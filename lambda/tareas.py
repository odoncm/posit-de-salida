# -*- coding: utf-8 -*-
"""Lógica pura de tareas (sin dependencias de Alexa) para poder testearla.

Compatible con Python 3.8 (runtime de Alexa-Hosted).
"""
import difflib
import re
import unicodedata
import uuid
from typing import Dict, List, Optional, Tuple

MAX_TAREAS = 40
MAX_LONGITUD = 120

DIAS_NOMBRE = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_PLURAL = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos"]
TODOS = [0, 1, 2, 3, 4, 5, 6]
LABORABLES = [0, 1, 2, 3, 4]
FINDE = [5, 6]

# --- Expresiones de recurrencia -------------------------------------------

_DIA = r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bados?|domingos?)"
_LISTA_DIAS = r"{d}(?:\s*(?:,|\by\b|\be\b)\s*{d})*".format(d=_DIA)
_ESPECIAL = (
    r"(?:d[ií]as\s+laborables|d[ií]as\s+de\s+diario|d[ií]as\s+de\s+trabajo"
    r"|fines?\s+de\s+semana|d[ií]as|d[ií]a)"
)
_RECURRENCIA = (
    r"(?:(?:cada|todos\s+los|todas\s+las|los)\s+(?:{lista}|{esp})"
    r"|a\s+diario|entre\s+semana|de\s+lunes\s+a\s+viernes)"
).format(lista=_LISTA_DIAS, esp=_ESPECIAL)

_RE_INICIO = re.compile(
    r"^\s*(?P<rec>{r})\s*,?\s*(?P<tarea>.+)$".format(r=_RECURRENCIA), re.IGNORECASE
)
_RE_FINAL = re.compile(
    r"^(?P<tarea>.+?)\s*,?\s*(?P<rec>{r})\s*$".format(r=_RECURRENCIA), re.IGNORECASE
)

# Muletillas que no forman parte de la tarea en sí.
_PREFIJOS = [
    r"que\s+",
    r"de\s+que\s+",
    r"tengo\s+que\s+",
    r"hay\s+que\s+",
    r"debo\s+",
    r"me\s+tengo\s+que\s+acordar\s+de\s+",
    r"cuando\s+salga\s+(?:de\s+casa\s+)?",
    r"al\s+salir\s+(?:de\s+casa\s+)?",
    r"antes\s+de\s+salir\s+",
]
_SUFIJOS = [
    r"\s+cuando\s+salga(?:\s+de\s+casa)?",
    r"\s+al\s+salir(?:\s+de\s+casa)?",
    r"\s+antes\s+de\s+salir(?:\s+de\s+casa)?",
    r"\s+por\s+favor",
]


def normalizar(texto):
    # type: (str) -> str
    """Minúsculas y sin tildes, para comparar."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto).strip()


def parse_dias(texto):
    # type: (str) -> List[int]
    """Convierte 'los martes y jueves', 'entre semana', etc. en índices 0=lunes."""
    t = normalizar(texto)
    if re.search(r"laborables|entre semana|de lunes a viernes|dias de diario|dias de trabajo", t):
        return list(LABORABLES)
    if re.search(r"fines? de semana", t):
        return list(FINDE)
    if re.search(r"todos los dias|cada dia|a diario|\bdiario\b", t):
        return list(TODOS)
    claves = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    dias = [i for i, k in enumerate(claves) if re.search(r"\b" + k, t)]
    return dias


def limpiar_tarea(texto):
    # type: (str) -> str
    t = texto.strip().strip(".,;:¡!¿?").strip()
    cambiado = True
    while cambiado:
        cambiado = False
        for p in _PREFIJOS:
            nuevo = re.sub(r"^" + p, "", t, flags=re.IGNORECASE)
            if nuevo != t:
                t, cambiado = nuevo.strip(), True
        for s in _SUFIJOS:
            nuevo = re.sub(s + r"$", "", t, flags=re.IGNORECASE)
            if nuevo != t:
                t, cambiado = nuevo.strip(), True
    return t[:MAX_LONGITUD].strip()


def interpretar(texto):
    # type: (str) -> Tuple[str, List[int]]
    """Separa la tarea de su recurrencia.

    'los martes y jueves bajar la basura' -> ('bajar la basura', [1, 3])
    'poner la lavadora' -> ('poner la lavadora', [])
    """
    texto = limpiar_tarea(texto)
    for regex in (_RE_INICIO, _RE_FINAL):
        m = regex.match(texto)
        if m:
            dias = parse_dias(m.group("rec"))
            tarea = limpiar_tarea(m.group("tarea"))
            if dias and tarea:
                return tarea, dias
    return texto, []


def formatear_dias(dias):
    # type: (List[int]) -> str
    dias = sorted(set(dias))
    if dias == TODOS:
        return "todos los días"
    if dias == LABORABLES:
        return "de lunes a viernes"
    if dias == FINDE:
        return "los fines de semana"
    return "los " + unir([DIAS_PLURAL[d] for d in dias])


def unir(items):
    # type: (List[str]) -> str
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    ultimo = items[-1]
    conj = "e" if normalizar(ultimo).startswith(("i", "hi")) and not normalizar(ultimo).startswith(("hie", "ie")) else "y"
    return "{} {} {}".format(", ".join(items[:-1]), conj, ultimo)


# --- Modelo de datos -------------------------------------------------------
# datos = {"puntuales": [{"id", "texto"}], "recurrentes": [{"id", "texto", "dias"}]}


def datos_vacios():
    # type: () -> Dict
    return {"puntuales": [], "recurrentes": []}


def asegurar(datos):
    # type: (Optional[Dict]) -> Dict
    datos = datos or {}
    datos.setdefault("puntuales", [])
    datos.setdefault("recurrentes", [])
    return datos


def total(datos):
    # type: (Dict) -> int
    return len(datos["puntuales"]) + len(datos["recurrentes"])


def anadir(datos, texto, dias):
    # type: (Dict, str, List[int]) -> Tuple[str, Dict]
    """Devuelve (resultado, tarea). resultado: 'nueva', 'actualizada', 'duplicada', 'llena'."""
    clave = normalizar(texto)
    if dias:
        for r in datos["recurrentes"]:
            if normalizar(r["texto"]) == clave:
                nuevos = sorted(set(r["dias"]) | set(dias))
                if nuevos == sorted(r["dias"]):
                    return "duplicada", r
                r["dias"] = nuevos
                return "actualizada", r
    else:
        for p in datos["puntuales"]:
            if normalizar(p["texto"]) == clave:
                return "duplicada", p
    if total(datos) >= MAX_TAREAS:
        return "llena", {}
    tarea = {"id": uuid.uuid4().hex[:8], "texto": texto}
    if dias:
        tarea["dias"] = sorted(set(dias))
        datos["recurrentes"].append(tarea)
    else:
        datos["puntuales"].append(tarea)
    return "nueva", tarea


def tareas_de_hoy(datos, dia_semana):
    # type: (Dict, int) -> Tuple[List[Dict], List[Dict]]
    recurrentes = [r for r in datos["recurrentes"] if dia_semana in r.get("dias", [])]
    return list(datos["puntuales"]), recurrentes


def buscar(datos, texto):
    # type: (Dict, str) -> Optional[Tuple[str, Dict]]
    """Busca la tarea más parecida. Devuelve (tipo, tarea) o None."""
    objetivo = normalizar(limpiar_tarea(texto))
    if not objetivo:
        return None
    mejor, mejor_ratio = None, 0.0
    for tipo in ("puntuales", "recurrentes"):
        for t in datos[tipo]:
            cand = normalizar(t["texto"])
            if cand == objetivo:
                return tipo, t
            ratio = difflib.SequenceMatcher(None, objetivo, cand).ratio()
            if objetivo in cand or cand in objetivo:
                ratio = max(ratio, 0.8)
            if ratio > mejor_ratio:
                mejor, mejor_ratio = (tipo, t), ratio
    return mejor if mejor_ratio >= 0.6 else None


def borrar_por_ids(datos, tipo, ids):
    # type: (Dict, str, List[str]) -> int
    antes = len(datos[tipo])
    datos[tipo] = [t for t in datos[tipo] if t["id"] not in set(ids)]
    return antes - len(datos[tipo])


def es_todo(texto):
    # type: (str) -> bool
    t = normalizar(texto or "")
    return bool(re.fullmatch(r"(todo|todas?( las| mis)?( tareas)?|la lista|toda la lista)", t))
