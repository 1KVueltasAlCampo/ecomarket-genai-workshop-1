# Interfaz web de EcoMarket: conversa con el agente, le pide al cliente que apruebe la acción irreversible
# (la etiqueta de devolución) y muestra la bitácora de lo que hizo el agente. La presentación está en
# interfaz.py y el agente en agente.py; este archivo solo conecta ambos y guarda el estado de la conversación.
#
# Uso (desde proyecto-final/):  streamlit run app.py
import os
import uuid

import streamlit as st

import herramientas as h
import interfaz as ui
from agente import MODELO_EJECUTOR, MODELO_PLANIFICADOR, Agente

st.set_page_config(page_title="EcoMarket · Ardi", page_icon=str(ui.ICONO), layout="wide")
ui.aplicar_tema()

if not os.environ.get("GROQ_API_KEY"):
    st.error("Falta la llave de Groq. Copia `.env.example` como `.env` y escribe tu `GROQ_API_KEY`.")
    st.stop()


@st.cache_resource(show_spinner="Ardi está preparando los documentos de EcoMarket (la primera vez puede tardar unos minutos)...")
def cargar_agente() -> Agente:
    """El agente (con su memoria de la pausa de aprobación) y el índice se crean una sola vez por servidor."""
    h.preparar_indice()
    return Agente()


def iniciar_conversacion():
    st.session_state.update(sesion=uuid.uuid4().hex[:8], turno=0, mensajes=[], pendiente=None, entrada=None)


def historial() -> list:
    """La conversación hasta ahora, en el formato que espera el agente."""
    return [{"rol": "Cliente" if m["rol"] == "user" else "Asistente", "texto": m["texto"]} for m in st.session_state.mensajes]


def etiqueta_de(resultado: dict):
    return next((v for v in resultado.get("hechos", {}).values() if "etiqueta_id" in v), None)


def guardar(resultado: dict):
    pendiente = resultado["pendiente"]
    st.session_state.pendiente = {"hilo": resultado["hilo"], "datos": pendiente} if pendiente else None
    if resultado["respuesta"]:
        st.session_state.mensajes.append({"rol": "assistant", "texto": resultado["respuesta"], "etiqueta": etiqueta_de(resultado)})


def correr(llamada):
    """Hace una llamada al agente mostrando el avance de cada nodo; guarda el resultado y redibuja la pantalla."""
    with st.chat_message("assistant", avatar=str(ui.ICONO)):
        with st.status("Ardi está trabajando...", expanded=True) as estado:
            def avance(nodo, cambios):
                linea = ui.linea_de_progreso(nodo, cambios)
                if linea:
                    st.write(linea)

            resultado = llamada(avance)
            if resultado["pendiente"]:
                st.write("Esperando tu confirmación")
            estado.update(label="Listo", state="complete", expanded=False)
    guardar(resultado)
    st.rerun()


def pintar(mensaje: dict):
    with st.chat_message(mensaje["rol"], avatar=str(ui.ICONO) if mensaje["rol"] == "assistant" else None):
        st.markdown(ui.escapar(mensaje["texto"]))
        if mensaje.get("etiqueta"):
            st.markdown(ui.tarjeta_etiqueta(mensaje["etiqueta"]), unsafe_allow_html=True)


agente = cargar_agente()
if "mensajes" not in st.session_state:
    iniciar_conversacion()
sesion = st.session_state
pendiente = sesion.pendiente

# --- Barra lateral ----------------------------------------------------------------------------------
with st.sidebar:
    st.markdown(ui.marca_lateral(), unsafe_allow_html=True)
    if st.button("Nueva conversación", type="primary", use_container_width=True):
        iniciar_conversacion()
        st.rerun()
    with st.expander("Pedidos de prueba"):
        st.markdown("| Pedido | Situación | Para probar |\n|---|---|---|\n" +
                    "\n".join(f"| {p} | {s} | {t} |" for p, s, t in ui.PEDIDOS_DE_PRUEBA))
    if st.button("Restablecer etiquetas", use_container_width=True,
                 help="Los pedidos de prueba admiten una sola etiqueta; este botón permite repetir la demostración."):
        h.reiniciar_estado()
        st.toast("Los pedidos de prueba quedaron como al inicio.")
    st.caption(f"Planificador: {MODELO_PLANIFICADOR}  \nEjecutor: {MODELO_EJECUTOR}  \nPedidos, etiquetas y reembolsos son simulados.")

# --- Pantalla principal ------------------------------------------------------------------------------
st.markdown(ui.cabecera(h.hoy().isoformat()), unsafe_allow_html=True)
col_chat, col_panel = st.columns([5, 3], gap="large")

with col_chat:
    if not sesion.mensajes:
        st.markdown(ui.bienvenida(), unsafe_allow_html=True)
        for izquierda, derecha in zip(ui.SUGERENCIAS[::2], ui.SUGERENCIAS[1::2]):
            for columna, (titulo, texto) in zip(st.columns(2), (izquierda, derecha)):
                if columna.button(titulo, key=f"sugerencia-{titulo}", use_container_width=True, help=texto):
                    sesion.entrada = texto
    for m in sesion.mensajes:
        pintar(m)

    if pendiente:
        st.markdown(ui.tarjeta_aprobacion(pendiente["datos"]), unsafe_allow_html=True)
        confirmar, cancelar = st.columns(2)
        acepta = confirmar.button("Confirmar y generar la etiqueta", key="confirmar", type="primary", use_container_width=True)
        rechaza = cancelar.button("Cancelar", key="cancelar", use_container_width=True)
        if acepta or rechaza:
            sesion.mensajes.append({"rol": "user", "texto": "Confirmo la devolución." if acepta else "Prefiero cancelar."})
            pintar(sesion.mensajes[-1])
            correr(lambda avance: agente.reanudar(pendiente["hilo"], acepta, avance))

with col_panel:
    st.markdown(ui.bitacora(h.leer_registro(sesion.sesion)), unsafe_allow_html=True)

# El campo de texto queda fijo al pie de la página; mientras haya una aprobación pendiente se desactiva.
mensaje = st.chat_input("Escribe tu mensaje para Ardi...", disabled=pendiente is not None) or sesion.pop("entrada", None)
if mensaje:
    previo = historial()
    sesion.turno += 1
    sesion.mensajes.append({"rol": "user", "texto": mensaje})
    with col_chat:
        pintar(sesion.mensajes[-1])
        correr(lambda avance: agente.conversar(mensaje, previo, f"{sesion.sesion}-{sesion.turno}", avance))
