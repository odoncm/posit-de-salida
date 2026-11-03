# -*- coding: utf-8 -*-
"""Skill de Alexa "Pósit de Salida".

Guarda recordatorios puntuales y recurrentes y los lee cuando el usuario sale de casa.
Pensada para Alexa-Hosted (Python 3.8) con DynamoDB como persistencia.
"""
import logging
import os
from datetime import datetime
from xml.sax.saxutils import escape

import boto3
import pytz
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
    AbstractRequestInterceptor,
)
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import get_slot_value, is_intent_name, is_request_type
from ask_sdk_dynamodb.adapter import DynamoDbAdapter

import tareas as T

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ZONA_POR_DEFECTO = "Europe/Madrid"

EJEMPLOS = (
    "Puedes decirme, por ejemplo: recuérdame poner la lavadora. "
    "O para algo que se repite: recuérdame los martes y jueves bajar la basura. "
    "Y cuando salgas de casa, dime: me voy."
)

# Estados de sesión para las preguntas de sí / no
CONFIRMAR_PUNTUALES = "CONFIRMAR_PUNTUALES"
CONFIRMAR_TODO = "CONFIRMAR_TODO"


# --- Utilidades ------------------------------------------------------------


def cargar(handler_input):
    return T.asegurar(handler_input.attributes_manager.persistent_attributes)


def guardar(handler_input, datos):
    handler_input.attributes_manager.persistent_attributes = datos
    handler_input.attributes_manager.save_persistent_attributes()


def sesion(handler_input):
    return handler_input.attributes_manager.session_attributes


def es_sesion_nueva(handler_input):
    s = handler_input.request_envelope.session
    return bool(s and s.new)


def dia_semana(handler_input):
    """Día de la semana (0=lunes) en la zona horaria del dispositivo del usuario."""
    zona = ZONA_POR_DEFECTO
    try:
        device_id = handler_input.request_envelope.context.system.device.device_id
        ups = handler_input.service_client_factory.get_ups_service()
        zona = ups.get_system_time_zone(device_id) or ZONA_POR_DEFECTO
    except Exception as e:  # pragma: no cover - depende del servicio de Alexa
        logger.warning("No se pudo obtener la zona horaria: %s", e)
    try:
        tz = pytz.timezone(zona)
    except Exception:
        tz = pytz.timezone(ZONA_POR_DEFECTO)
    return datetime.now(tz).weekday()


def ssml(texto):
    return escape(texto)


def responder(handler_input, texto, reprompt=None):
    """Si reprompt es None se cierra la sesión."""
    rb = handler_input.response_builder.speak(ssml(texto))
    if reprompt:
        rb.ask(ssml(reprompt))
    else:
        rb.set_should_end_session(True)
    return rb.response


def continuar_o_cerrar(handler_input, texto):
    """En una invocación de un solo paso se cierra; en conversación se pregunta si hay más."""
    if es_sesion_nueva(handler_input):
        return responder(handler_input, texto)
    return responder(handler_input, texto + " ¿Algo más?", "¿Quieres añadir otra cosa?")


def frase_salida(handler_input, datos):
    """Construye el aviso de salida y deja preparado el estado de confirmación."""
    puntuales, recurrentes = T.tareas_de_hoy(datos, dia_semana(handler_input))
    textos = [p["texto"] for p in puntuales] + [r["texto"] for r in recurrentes]
    if not textos:
        return None, None
    texto = "Antes de salir, recuerda: {}.".format(T.unir(textos))
    if puntuales:
        s = sesion(handler_input)
        s["estado"] = CONFIRMAR_PUNTUALES
        s["ids"] = [p["id"] for p in puntuales]
        if recurrentes:
            pregunta = "¿Borro las puntuales? Las que se repiten se quedan."
        elif len(puntuales) == 1:
            pregunta = "¿La borro ya?"
        else:
            pregunta = "¿Las borro ya?"
        return texto + " " + pregunta, pregunta
    return texto + " ¡Que vaya bien!", None


# --- Handlers --------------------------------------------------------------


class LaunchHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        datos = cargar(handler_input)
        texto, reprompt = frase_salida(handler_input, datos)
        if texto:
            if reprompt:
                return responder(handler_input, texto, reprompt)
            return responder(handler_input, texto)
        if T.total(datos) == 0:
            return responder(
                handler_input,
                "Hola, soy tu pósit de salida. " + EJEMPLOS + " ¿Qué quieres que te recuerde?",
                "¿Qué quieres que te recuerde cuando salgas?",
            )
        return responder(
            handler_input,
            "Hoy no tienes nada pendiente al salir. ¿Quieres añadir algo?",
            "Dime qué quieres que te recuerde, o di: salir.",
        )


class AnadirHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AnadirTareaIntent")(handler_input)

    def handle(self, handler_input):
        bruto = get_slot_value(handler_input, "tarea") or ""
        tarea, dias = T.interpretar(bruto)
        if not tarea:
            return responder(handler_input, "No te he entendido. " + EJEMPLOS, "¿Qué quieres que te recuerde?")

        datos = cargar(handler_input)
        resultado, item = T.anadir(datos, tarea, dias)
        if resultado == "llena":
            return responder(
                handler_input,
                "Ya tienes {} tareas, que es el máximo. Borra alguna antes de añadir más.".format(T.MAX_TAREAS),
            )
        if resultado == "duplicada":
            return continuar_o_cerrar(handler_input, "Eso ya lo tenía apuntado.")
        guardar(handler_input, datos)

        if dias:
            cuando = T.formatear_dias(item["dias"])
            if resultado == "actualizada":
                texto = "Hecho. Ahora te recordaré {} {}.".format(item["texto"], cuando)
            else:
                texto = "Apuntado. Te recordaré {} {}, cuando salgas.".format(item["texto"], cuando)
        else:
            texto = "Apuntado: {}. Te lo recordaré cuando salgas.".format(item["texto"])
        return continuar_o_cerrar(handler_input, texto)


class RecurrenteSinDatosHandler(AbstractRequestHandler):
    """'Añade una tarea recurrente' sin decir cuál: explicamos el formato."""

    def can_handle(self, handler_input):
        return is_intent_name("TareaRecurrenteIntent")(handler_input)

    def handle(self, handler_input):
        return responder(
            handler_input,
            "Dime la tarea con los días en una sola frase. Por ejemplo: recuérdame los lunes sacar el reciclaje, "
            "o recuérdame todos los días coger las llaves.",
            "Por ejemplo: recuérdame los martes y jueves bajar la basura.",
        )


class SalirHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SalirIntent")(handler_input)

    def handle(self, handler_input):
        datos = cargar(handler_input)
        texto, reprompt = frase_salida(handler_input, datos)
        if not texto:
            return responder(handler_input, "No tienes nada pendiente. ¡Que vaya bien!")
        return responder(handler_input, texto, reprompt)


class ListarHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("ListarTareasIntent")(handler_input)

    def handle(self, handler_input):
        datos = cargar(handler_input)
        if T.total(datos) == 0:
            return continuar_o_cerrar(handler_input, "No tienes ninguna tarea apuntada.")
        partes = []
        p = datos["puntuales"]
        if p:
            partes.append(
                "{} {}: {}.".format(
                    len(p),
                    "tarea puntual" if len(p) == 1 else "tareas puntuales",
                    T.unir([x["texto"] for x in p]),
                )
            )
        r = datos["recurrentes"]
        if r:
            partes.append(
                "{} que se {}: {}.".format(
                    len(r),
                    "repite" if len(r) == 1 else "repiten",
                    T.unir(["{} {}".format(x["texto"], T.formatear_dias(x["dias"])) for x in r]),
                )
            )
        return continuar_o_cerrar(handler_input, "Tienes " + " Y ".join(partes))


class BorrarHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("BorrarTareaIntent")(handler_input)

    def handle(self, handler_input):
        bruto = get_slot_value(handler_input, "tarea") or ""
        if T.es_todo(bruto):
            return pedir_borrar_todo(handler_input)
        datos = cargar(handler_input)
        encontrado = T.buscar(datos, bruto)
        if not encontrado:
            return continuar_o_cerrar(handler_input, "No encuentro ninguna tarea parecida a {}.".format(bruto))
        tipo, item = encontrado
        T.borrar_por_ids(datos, tipo, [item["id"]])
        guardar(handler_input, datos)
        return continuar_o_cerrar(handler_input, "Quitado: {}.".format(item["texto"]))


def pedir_borrar_todo(handler_input):
    datos = cargar(handler_input)
    if T.total(datos) == 0:
        return continuar_o_cerrar(handler_input, "No tienes ninguna tarea apuntada.")
    sesion(handler_input)["estado"] = CONFIRMAR_TODO
    return responder(
        handler_input,
        "¿Seguro que quieres borrar todas tus tareas, también las que se repiten?",
        "¿Las borro todas? Di sí o no.",
    )


class BorrarTodoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("BorrarTodoIntent")(handler_input)

    def handle(self, handler_input):
        return pedir_borrar_todo(handler_input)


class SiHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.YesIntent")(handler_input)

    def handle(self, handler_input):
        s = sesion(handler_input)
        estado = s.pop("estado", None)
        if estado == CONFIRMAR_PUNTUALES:
            datos = cargar(handler_input)
            n = T.borrar_por_ids(datos, "puntuales", s.pop("ids", []))
            guardar(handler_input, datos)
            return responder(handler_input, "Hecho, borradas. ¡Que vaya bien!" if n != 1 else "Hecho, borrada. ¡Que vaya bien!")
        if estado == CONFIRMAR_TODO:
            guardar(handler_input, T.datos_vacios())
            return responder(handler_input, "Listo, he borrado todas tus tareas.")
        return responder(handler_input, "Dime qué quieres que te recuerde. " + EJEMPLOS, "¿Qué quieres que te recuerde?")


class NoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.NoIntent")(handler_input)

    def handle(self, handler_input):
        s = sesion(handler_input)
        estado = s.pop("estado", None)
        s.pop("ids", None)
        if estado == CONFIRMAR_PUNTUALES:
            return responder(handler_input, "Vale, las guardo para la próxima vez. ¡Hasta luego!")
        if estado == CONFIRMAR_TODO:
            return responder(handler_input, "Vale, no borro nada.")
        return responder(handler_input, "Vale, hasta luego.")


class AyudaHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        sesion(handler_input).pop("estado", None)
        return responder(
            handler_input,
            "Soy como un pósit en la puerta de casa. " + EJEMPLOS
            + " También puedes decir: qué tareas tengo, o, borra poner la lavadora. ¿Qué quieres hacer?",
            "¿Qué quieres que te recuerde?",
        )


class CancelarHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input)
            or is_intent_name("AMAZON.StopIntent")(handler_input)
            or is_intent_name("AMAZON.NavigateHomeIntent")(handler_input)
        )

    def handle(self, handler_input):
        return responder(handler_input, "¡Hasta luego!")


class FallbackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        return responder(handler_input, "Perdona, no te he entendido. " + EJEMPLOS, "¿Qué quieres que te recuerde?")


class SesionTerminadaHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        logger.info("Sesión terminada: %s", handler_input.request_envelope.request.reason)
        return handler_input.response_builder.response


class LimpiarEstadoInterceptor(AbstractRequestInterceptor):
    """Una pregunta de sí/no solo vale para la respuesta inmediatamente siguiente."""

    def process(self, handler_input):
        if not (is_intent_name("AMAZON.YesIntent")(handler_input) or is_intent_name("AMAZON.NoIntent")(handler_input)):
            s = sesion(handler_input)
            s.pop("estado", None)
            s.pop("ids", None)


class ErrorHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return responder(handler_input, "Vaya, algo ha fallado. Inténtalo de nuevo en un momento.")


# --- Construcción de la skill ---------------------------------------------

adaptador = DynamoDbAdapter(
    table_name=os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME"),
    create_table=False,
    dynamodb_resource=boto3.resource(
        "dynamodb", region_name=os.environ.get("DYNAMODB_PERSISTENCE_REGION")
    ),
)

sb = CustomSkillBuilder(persistence_adapter=adaptador, api_client=DefaultApiClient())
for h in (
    LaunchHandler(),
    AnadirHandler(),
    RecurrenteSinDatosHandler(),
    SalirHandler(),
    ListarHandler(),
    BorrarHandler(),
    BorrarTodoHandler(),
    SiHandler(),
    NoHandler(),
    AyudaHandler(),
    CancelarHandler(),
    FallbackHandler(),
    SesionTerminadaHandler(),
):
    sb.add_request_handler(h)
sb.add_global_request_interceptor(LimpiarEstadoInterceptor())
sb.add_exception_handler(ErrorHandler())

lambda_handler = sb.lambda_handler()
