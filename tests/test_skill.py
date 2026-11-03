"""Simula conversaciones completas contra el handler de la skill (persistencia en memoria)."""
import os, sys, json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))
os.environ.setdefault("DYNAMODB_PERSISTENCE_TABLE_NAME", "test")
os.environ.setdefault("DYNAMODB_PERSISTENCE_REGION", "eu-west-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-1")
pytest.importorskip("ask_sdk_core")
import lambda_function as L

STORE = {}

class FakeAdapter:
    def get_attributes(self, request_envelope):
        return json.loads(json.dumps(STORE.get(request_envelope.context.system.user.user_id, {})))
    def save_attributes(self, request_envelope, attributes):
        STORE[request_envelope.context.system.user.user_id] = json.loads(json.dumps(attributes))
    def delete_attributes(self, request_envelope):
        STORE.pop(request_envelope.context.system.user.user_id, None)

L.sb.persistence_adapter = FakeAdapter()
DIA = {"v": 1}
L.dia_semana = lambda hi: DIA["v"]

def evento(req, new=True, attrs=None):
    return {
        "version": "1.0",
        "session": {"new": new, "sessionId": "s", "application": {"applicationId": "a"},
                    "user": {"userId": "u1"}, "attributes": attrs or {}},
        "context": {"System": {"application": {"applicationId": "a"}, "user": {"userId": "u1"},
                               "device": {"deviceId": "d"}, "apiEndpoint": "https://api.eu.amazonalexa.com"}},
        "request": dict(req, requestId="r", timestamp="2026-11-03T10:00:00Z", locale="es-ES"),
    }

def intent(name, tarea=None, new=True, attrs=None):
    slots = {"tarea": {"name": "tarea", "value": tarea}} if tarea is not None else {}
    return evento({"type": "IntentRequest", "intent": {"name": name, "slots": slots}}, new, attrs)

def run(ev):
    out = L.lambda_handler(ev, None)
    return out["response"]["outputSpeech"]["ssml"], out["response"].get("shouldEndSession"), out.get("sessionAttributes", {})

def test_conversacion():
    STORE.clear()
    txt, end, _ = run(evento({"type": "LaunchRequest"}))
    assert "Hola" in txt and end is not True
    txt, end, _ = run(intent("AnadirTareaIntent", "poner la lavadora"))
    assert "poner la lavadora" in txt and end is True
    txt, *_ = run(intent("AnadirTareaIntent", "los martes y jueves bajar la basura"))
    assert "los martes y jueves" in txt
    DIA["v"] = 1
    txt, end, attrs = run(intent("SalirIntent"))
    assert "poner la lavadora y bajar la basura" in txt and end is not True
    txt, end, _ = run(intent("AMAZON.YesIntent", new=False, attrs=attrs))
    assert "borrada" in txt and end is True
    txt, *_ = run(intent("ListarTareasIntent"))
    assert "bajar la basura los martes y jueves" in txt and "puntual" not in txt
    DIA["v"] = 0
    txt, end, _ = run(intent("SalirIntent"))
    assert "nada pendiente" in txt and end is True
    txt, *_ = run(intent("BorrarTareaIntent", "la basura"))
    assert "Quitado" in txt
    txt, end, attrs = run(intent("BorrarTodoIntent"))
    assert "No tienes" in txt
    print(STORE)

def test_abrir_con_solo_recurrentes_no_cierra():
    STORE.clear()
    run(intent("AnadirTareaIntent", "los martes bajar la basura"))
    DIA["v"] = 1
    txt, end, _ = run(evento({"type": "LaunchRequest"}))
    assert "bajar la basura" in txt and "apuntar algo más" in txt and end is not True
    txt, end, _ = run(intent("AMAZON.NoIntent", new=False))
    assert end is True
