import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))
import tareas as T

def test_puntual():
    assert T.interpretar("poner la lavadora") == ("poner la lavadora", [])
    assert T.interpretar("que tengo que bajar la basura cuando salga") == ("bajar la basura", [])

def test_recurrente_inicio():
    assert T.interpretar("los martes y jueves bajar la basura") == ("bajar la basura", [1, 3])
    assert T.interpretar("todos los días coger las llaves") == ("coger las llaves", T.TODOS)
    assert T.interpretar("cada lunes sacar el reciclaje") == ("sacar el reciclaje", [0])
    assert T.interpretar("los sábados regar las plantas") == ("regar las plantas", [5])
    assert T.interpretar("entre semana coger la fiambrera") == ("coger la fiambrera", T.LABORABLES)

def test_recurrente_final():
    assert T.interpretar("bajar la basura los lunes, miércoles y viernes") == ("bajar la basura", [0, 2, 4])
    assert T.interpretar("sacar al perro los fines de semana") == ("sacar al perro", T.FINDE)
    assert T.interpretar("que tengo que tirar el vidrio cada miercoles") == ("tirar el vidrio", [2])

def test_formatear():
    assert T.formatear_dias([1, 3]) == "los martes y jueves"
    assert T.formatear_dias([5]) == "los sábados"
    assert T.formatear_dias(T.TODOS) == "todos los días"
    assert T.unir(["a", "b", "c"]) == "a, b y c"
    assert T.unir(["a", "ir al banco"]) == "a e ir al banco"

def test_ciclo():
    d = T.datos_vacios()
    assert T.anadir(d, "poner la lavadora", [])[0] == "nueva"
    assert T.anadir(d, "Poner la lavadora", [])[0] == "duplicada"
    assert T.anadir(d, "bajar la basura", [1])[0] == "nueva"
    r, item = T.anadir(d, "bajar la basura", [3])
    assert r == "actualizada" and item["dias"] == [1, 3]
    p, rec = T.tareas_de_hoy(d, 3)
    assert len(p) == 1 and len(rec) == 1
    assert T.tareas_de_hoy(d, 0)[1] == []
    tipo, t = T.buscar(d, "la lavadora")
    assert tipo == "puntuales"
    assert T.borrar_por_ids(d, tipo, [t["id"]]) == 1
    assert T.buscar(d, "comprar pan") is None

def test_es_todo():
    assert T.es_todo("todas las tareas") and T.es_todo("todo") and not T.es_todo("la basura")
