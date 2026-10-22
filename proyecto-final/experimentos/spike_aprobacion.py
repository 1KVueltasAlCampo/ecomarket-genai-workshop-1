# Prueba de viabilidad: pausar el proceso antes de una acción irreversible hasta que el CLIENTE
# la apruebe. Se usa un nodo de LangGraph con interrupt() y un checkpointer; el LLM no interviene.
# La acción solo se ejecuta si la decisión es "aprobado" (y la ejecuta el código, no el modelo).
#
# Uso (desde proyecto-final/):  python experimentos/spike_aprobacion.py
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class Estado(TypedDict, total=False):
    pedido: str
    resumen: str
    aprobado: bool
    resultado: str


def preparar(e: Estado):
    return {"resumen": f"Generar etiqueta de devolución para {e['pedido']}"}


def aprobar(e: Estado):
    # El grafo se detiene aquí y devuelve el payload; continúa cuando alguien lo reanuda.
    decision = interrupt({"accion": e["resumen"], "pregunta": "¿Confirmas?"})
    return {"aprobado": bool(decision["aprobado"])}


def generar(e: Estado):
    if not e["aprobado"]:
        return {"resultado": "El cliente canceló: no se generó ninguna etiqueta."}
    return {"resultado": f"Etiqueta ETQ-0001 generada para {e['pedido']}"}


g = StateGraph(Estado)
g.add_node("preparar", preparar)
g.add_node("aprobar", aprobar)
g.add_node("generar", generar)
g.add_edge(START, "preparar")
g.add_edge("preparar", "aprobar")
g.add_edge("aprobar", "generar")
g.add_edge("generar", END)
app = g.compile(checkpointer=InMemorySaver())


def correr(hilo, decision):
    cfg = {"configurable": {"thread_id": hilo}}
    r1 = app.invoke({"pedido": "ORD-003"}, cfg)
    print(f"[{hilo}] 1) tras invocar: pausado={('__interrupt__' in r1)} | resultado={r1.get('resultado')!r}")
    if "__interrupt__" in r1:
        print(f"[{hilo}]    lo que ve el cliente: {r1['__interrupt__'][0].value}")
    r2 = app.invoke(Command(resume={"aprobado": decision}), cfg)
    print(f"[{hilo}] 2) tras la decisión ({'aprobar' if decision else 'cancelar'}): {r2['resultado']}")
    return r2


if __name__ == "__main__":
    correr("conversacion-A", True)
    correr("conversacion-B", False)
    # Una tercera conversación que NUNCA se reanuda: la acción no debe ejecutarse
    cfg = {"configurable": {"thread_id": "conversacion-C"}}
    r = app.invoke({"pedido": "ORD-003"}, cfg)
    print(f"[conversacion-C] sin decisión: resultado={r.get('resultado')!r} (None = la acción no se ejecutó)")
