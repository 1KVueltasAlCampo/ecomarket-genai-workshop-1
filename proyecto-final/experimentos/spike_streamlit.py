# Prueba de viabilidad: la pausa de aprobación dentro de Streamlit. Cada clic reejecuta el script,
# así que el grafo (con su checkpointer) y el identificador de conversación deben sobrevivir.
#
# Uso (desde proyecto-final/):  streamlit run experimentos/spike_streamlit.py
import uuid

import streamlit as st
from langgraph.types import Command

from spike_aprobacion import app            # el grafo con pausa; el módulo se importa una sola vez

st.title("Prueba: aprobación del cliente")

if "hilo" not in st.session_state:
    st.session_state.hilo = str(uuid.uuid4())
    st.session_state.fase = "inicio"
cfg = {"configurable": {"thread_id": st.session_state.hilo}}

if st.session_state.fase == "inicio":
    st.write("El agente va a generar una etiqueta de devolución.")
    if st.button("Solicitar etiqueta para ORD-003"):
        r = app.invoke({"pedido": "ORD-003"}, cfg)
        if "__interrupt__" in r:
            st.session_state.pendiente = r["__interrupt__"][0].value
            st.session_state.fase = "pausado"
        st.rerun()

elif st.session_state.fase == "pausado":
    st.warning(f"El agente quiere: {st.session_state.pendiente['accion']}. {st.session_state.pendiente['pregunta']}")
    col1, col2 = st.columns(2)
    decision = None
    if col1.button("Confirmar"):
        decision = True
    if col2.button("Cancelar"):
        decision = False
    if decision is not None:
        r = app.invoke(Command(resume={"aprobado": decision}), cfg)
        st.session_state.resultado = r["resultado"]
        st.session_state.fase = "fin"
        st.rerun()

else:
    st.success(st.session_state.resultado)
    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()
