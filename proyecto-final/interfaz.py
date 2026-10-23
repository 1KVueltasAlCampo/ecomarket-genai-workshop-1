# Presentación de la interfaz: tema, mascota, tarjetas y bitácora. No tiene lógica del agente (eso está en app.py):
# cada función recibe datos y devuelve HTML o texto.
import base64
import html
import json
from pathlib import Path

import streamlit as st

from agente import MESES

ASSETS = Path(__file__).parent / "assets"
ARDI = ASSETS / "ardi.svg"
ICONO = ASSETS / "ardi_icono.svg"

# Paleta tomada de la mascota: fondo oscuro, pelaje marrón, camiseta azul y rosa de la nariz.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700&display=swap');
:root {
  --noche: #171717; --carbon: #212121; --corteza: #2A231D; --borde: #3A2F26;
  --nuez: #B97B49; --miel: #D4A373; --crema: #F3E6D3; --cielo: #4F82D0; --cielo-claro: #7FA6E6;
  --rosa: #D98A7B; --ok: #7DBE8A; --alerta: #E5806F;
}
.stApp { font-family: 'Nunito', sans-serif;
  background: radial-gradient(900px 420px at 92% -8%, rgba(79,130,208,.16), transparent 62%),
              radial-gradient(700px 380px at -6% 105%, rgba(185,123,73,.14), transparent 60%), var(--noche); }
h1, h2, h3, .ardi-titulo { font-family: 'Fredoka', sans-serif !important; letter-spacing: .2px; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stCaptionContainer"],
[data-testid="stChatInput"] textarea, [data-testid="stExpander"] summary p, .stButton button p, .ardi-evento, .ardi-etiqueta { font-family: 'Nunito', sans-serif; }
[data-testid="stAppDeployButton"], #MainMenu, footer { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }

/* barra lateral */
[data-testid="stSidebar"] { background: #1B1815; border-right: 1px solid var(--borde); }
.ardi-marca { display: flex; align-items: center; gap: .75rem; margin-bottom: .4rem; }
.ardi-marca img { width: 58px; height: 58px; }
.ardi-marca b { font-family: 'Fredoka', sans-serif; font-size: 1.45rem; color: var(--crema); display: block; line-height: 1.05; }
.ardi-marca span { color: var(--miel); font-size: .82rem; }

/* cabecera */
.ardi-cabecera { display: flex; align-items: center; gap: 1rem; padding: .2rem 0 1rem; }
.ardi-cabecera img { width: 64px; height: 64px; }
.ardi-cabecera h1 { margin: 0; font-size: 2rem; color: var(--crema); line-height: 1.1; }
.ardi-cabecera h1 em { font-style: normal; color: var(--cielo-claro); }
.ardi-cabecera p { margin: .1rem 0 0; color: var(--miel); font-size: .95rem; }
.ardi-chip { margin-left: auto; font-size: .78rem; color: var(--crema); background: var(--corteza); border: 1px solid var(--borde);
  border-radius: 999px; padding: .3rem .8rem; white-space: nowrap; }

/* bienvenida */
.ardi-bienvenida { display: flex; align-items: center; gap: 1.6rem; background: linear-gradient(135deg, #2A231D, #1F2A3F);
  border: 1px solid var(--borde); border-radius: 24px; padding: 1.4rem 1.8rem; margin-bottom: 1rem; }
.ardi-bienvenida img { width: 150px; flex-shrink: 0; }
.ardi-bienvenida h2 { margin: 0 0 .35rem; color: var(--crema); font-size: 1.55rem; }
.ardi-bienvenida p { margin: 0; color: #d9c9b3; line-height: 1.5; }

/* mensajes */
[data-testid="stChatMessage"] { border-radius: 20px; padding: .9rem 1.1rem; background: var(--corteza); border: 1px solid var(--borde); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: #1E2C46; border-color: #2E4672; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { line-height: 1.55; }
[data-testid="stChatMessageAvatarAssistant"] { background: transparent; }
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background: transparent !important; }
[data-testid="stChatInput"] { border-radius: 999px; border: 1px solid var(--borde); background: var(--corteza); }
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea { background: transparent !important; }

/* botones */
.stButton > button { border-radius: 999px; font-family: 'Nunito', sans-serif; font-weight: 700; border: 1px solid var(--nuez); color: var(--crema);
  background: transparent; transition: all .15s ease; }
.stButton > button:hover { background: var(--corteza); border-color: var(--miel); color: #fff; transform: translateY(-1px); }
.stButton > button[kind="primary"] { background: var(--cielo); border-color: var(--cielo); color: #fff; }
.stButton > button[kind="primary"]:hover { background: var(--cielo-claro); border-color: var(--cielo-claro); }

/* tarjeta de aprobación */
.ardi-aprobacion { border: 2px dashed var(--miel); border-radius: 22px; padding: 1.1rem 1.3rem; background: rgba(212,163,115,.07); margin: .6rem 0 .8rem; }
.ardi-aprobacion h3 { margin: 0 0 .15rem; color: var(--miel); font-size: 1.15rem; }
.ardi-aprobacion .sub { color: #cdbba3; font-size: .9rem; margin-bottom: .7rem; }
.ardi-filas { display: grid; grid-template-columns: auto 1fr; gap: .3rem 1rem; font-size: .95rem; }
.ardi-filas dt { color: #b9a68e; } .ardi-filas dd { margin: 0; color: var(--crema); font-weight: 600; }
.ardi-filas .total { color: var(--cielo-claro); font-size: 1.1rem; }

/* etiqueta de devolución */
.ardi-etiqueta { max-width: 430px; margin: .7rem 0 .2rem; background: var(--crema); color: #2A2118; border-radius: 16px;
  overflow: hidden; box-shadow: 0 6px 22px rgba(0,0,0,.4); }
.ardi-etiqueta header { background: var(--cielo); color: #fff; display: flex; justify-content: space-between; padding: .55rem 1rem;
  font-family: 'Fredoka', sans-serif; font-size: .92rem; letter-spacing: .4px; }
.ardi-etiqueta .cuerpo { padding: .8rem 1rem .5rem; display: grid; grid-template-columns: 1fr 1fr; gap: .4rem 1rem; font-size: .85rem; }
.ardi-etiqueta .cuerpo small { display: block; color: #7b6a58; font-size: .7rem; text-transform: uppercase; letter-spacing: .6px; }
.ardi-etiqueta .cuerpo strong { font-size: .98rem; }
.ardi-etiqueta .codigo { grid-column: 1 / -1; font-family: 'Fredoka', monospace; font-size: 1.5rem; color: #2F5EA8; letter-spacing: 1.5px; }
.ardi-barras { height: 44px; margin: .4rem 1rem 1rem; border-radius: 3px;
  background: repeating-linear-gradient(90deg, #2A2118 0 2px, transparent 2px 4px, #2A2118 4px 5px, transparent 5px 9px, #2A2118 9px 12px, transparent 12px 14px); }

/* bitácora */
.ardi-panel h3 { color: var(--crema); font-size: 1.15rem; margin-bottom: .1rem; }
.ardi-panel .sub { color: #b9a68e; font-size: .82rem; margin-bottom: .8rem; }
.ardi-turno { color: var(--miel); font-family: 'Fredoka', sans-serif; font-size: .9rem; margin: .9rem 0 .35rem; }
.ardi-evento { display: flex; flex-direction: column; gap: .05rem; font-size: .84rem; padding: .4rem .75rem; margin-bottom: .3rem; background: #1D1A17;
  border-left: 3px solid var(--nuez); border-radius: 0 10px 10px 0; color: #e6d8c3; }
.ardi-evento.herramienta { border-color: var(--cielo); } .ardi-evento.aprobacion { border-color: var(--ok); }
.ardi-evento.error { border-color: var(--alerta); }
.ardi-evento b { color: var(--crema); white-space: nowrap; } .ardi-evento span { color: #b9a68e; word-break: break-word; }
@media (max-width: 640px) {
  .ardi-bienvenida { flex-direction: column; text-align: center; padding: 1.1rem; }
  .ardi-bienvenida img { width: 120px; }
  .ardi-cabecera { flex-wrap: wrap; } .ardi-cabecera h1 { font-size: 1.5rem; } .ardi-chip { margin-left: 0; }
}
.ardi-vacio { color: #8f7f6c; font-size: .88rem; border: 1px dashed var(--borde); border-radius: 14px; padding: 1rem; }
</style>
"""


def aplicar_tema():
    st.markdown(CSS, unsafe_allow_html=True)


def _imagen(ruta: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(ruta.read_bytes()).decode()


def escapar(texto: str) -> str:
    """Streamlit interpreta $...$ como fórmula matemática: los montos en pesos deben mostrarse tal cual."""
    return texto.replace("$", r"\$")


def pesos(valor) -> str:
    return "$" + f"{int(valor):,}".replace(",", ".")


def fecha_larga(iso: str) -> str:
    anio, mes, dia = iso.split("-")
    return f"{int(dia)} de {MESES[int(mes) - 1]} de {anio}"


# --- Piezas de la pantalla ---------------------------------------------------------------------------
def marca_lateral() -> str:
    return (f'<div class="ardi-marca"><img src="{_imagen(ARDI)}" alt="Ardi"><div><b>EcoMarket</b>'
            '<span>Atención con Ardi</span></div></div>')


def cabecera(fecha_iso: str) -> str:
    return (f'<div class="ardi-cabecera"><img src="{_imagen(ICONO)}" alt="Ardi"><div>'
            '<h1>Hola, soy <em>Ardi</em></h1><p>El asistente de EcoMarket: pedidos, devoluciones y dudas de la tienda</p></div>'
            f'<div class="ardi-chip">Hoy: {fecha_larga(fecha_iso)}</div></div>')


def bienvenida() -> str:
    return (f'<div class="ardi-bienvenida"><img src="{_imagen(ARDI)}" alt="Ardi"><div>'
            '<h2>Cuéntame qué necesitas</h2><p>Puedo consultar el estado de tu pedido, resolver dudas sobre envíos, garantías y productos, '
            'y gestionar tu devolución. Antes de hacer algo que no se pueda deshacer, como generar una etiqueta, siempre te pido '
            'confirmación.</p></div></div>')


def tarjeta_aprobacion(p: dict) -> str:
    motivo = {"cambio_de_opinion": "Cambio de opinión", "defecto_o_dano": "Defecto o daño"}.get(p["motivo"], p["motivo"])
    envio = (f"A tu cargo: se resta {pesos(p['se_resta_del_reembolso_cop'])} del reembolso"
             if p["envio_retorno_a_cargo"] == "cliente" else "A cargo de EcoMarket")
    reembolso = pesos(p["reembolso_estimado_cop"]) if p.get("reembolso_estimado_cop") is not None else "Se calcula al recibir el producto"
    return ('<div class="ardi-aprobacion"><h3>Necesito tu confirmación</h3>'
            f'<div class="sub">{html.escape(p["accion"])}. Esta acción no se puede deshacer.</div><dl class="ardi-filas">'
            f'<dt>Pedido</dt><dd>{html.escape(p["pedido"])}</dd><dt>Producto</dt><dd>{html.escape(p["producto"])}</dd>'
            f'<dt>Motivo</dt><dd>{motivo}</dd><dt>Envío de retorno</dt><dd>{envio}</dd>'
            f'<dt>Reembolso estimado</dt><dd class="total">{reembolso}</dd></dl></div>')


def tarjeta_etiqueta(e: dict) -> str:
    return ('<div class="ardi-etiqueta"><header><span>ETIQUETA DE DEVOLUCIÓN</span>'
            f'<span>{html.escape(e["transportadora"])}</span></header><div class="cuerpo">'
            f'<div class="codigo">{html.escape(e["etiqueta_id"])}</div>'
            f'<div><small>Pedido</small><strong>{html.escape(e["numero_pedido"])}</strong></div>'
            f'<div><small>Vigente hasta</small><strong>{fecha_larga(e["vigencia_hasta"])}</strong></div></div>'
            '<div class="ardi-barras"></div></div>')


# --- Progreso y bitácora -----------------------------------------------------------------------------
HECHO = {"buscar_en_documentos": "Documentos consultados", "consultar_pedido": "Pedido consultado",
         "consultar_producto": "Producto consultado", "calcular": "Cálculo realizado",
         "verificar_elegibilidad_producto": "Elegibilidad verificada", "generar_etiqueta_devolucion": "Etiqueta generada"}
PLAN = {"buscar_en_documentos": "documentos", "consultar_pedido": "pedido", "consultar_producto": "producto",
        "calcular": "cálculo", "verificar_elegibilidad_producto": "elegibilidad", "generar_etiqueta_devolucion": "etiqueta"}


def linea_de_progreso(nodo: str, cambios: dict):
    """Texto breve de lo que acaba de terminar un nodo del grafo (None si no aporta nada)."""
    if nodo == "planificar":
        if cambios.get("estado") == "plan_invalido":
            return "No fue posible interpretar la solicitud"
        pasos = [p["herramienta"] for p in cambios.get("plan", {}).get("pasos", [])]
        return "Plan: " + " → ".join(PLAN[p] for p in pasos) if pasos else "Solicitud entendida: no necesita consultas"
    if nodo == "ejecutar":
        return HECHO[cambios["pasos_ejecutados"][-1]]
    if nodo == "aprobar":
        return "Aprobación del cliente: " + ("confirmada" if cambios.get("aprobado") else "cancelada")
    if nodo == "generar":
        return "Etiqueta generada" if cambios.get("estado") == "ok" else "No fue posible generar la etiqueta"
    if nodo == "responder":
        return "Respuesta redactada"
    return None


def _resumen_resultado(ev: dict) -> str:
    """Una frase con lo esencial del resultado de una herramienta, en lugar del JSON completo."""
    r, herramienta = ev.get("resultado") or {}, ev["herramienta"]
    if ev.get("error"):
        return r.get("mensaje") or ev["error"]
    if "fragmentos" in r:
        return f"{len(r['fragmentos'])} fragmentos de " + ", ".join(sorted({f.split(' | ')[0] for f in r['fragmentos']}))
    if herramienta == "consultar_pedido":
        return f"{r['numero_pedido']}: {r['estado']}"
    if herramienta == "consultar_producto":
        return f"{r['nombre']}, {pesos(r['precio_cop'])}, {r['disponibilidad']}"
    if herramienta == "calcular":
        return f"{r['expresion']} = {r['resultado']}"
    if herramienta == "verificar_elegibilidad_producto":
        return f"elegible, quedan {r['dias_restantes']} días" if r["elegible"] else r["detalle"]
    if herramienta == "generar_etiqueta_devolucion":
        return f"{r['etiqueta_id']}, vigente hasta {fecha_larga(r['vigencia_hasta'])}"
    return json.dumps(r, ensure_ascii=False)[:140]


def _evento(ev: dict):
    """(clase CSS, título, detalle) de un evento del registro, o None si no se muestra."""
    tipo = ev["evento"]
    if tipo == "mensaje":
        return "", "Mensaje", ev["texto"][:90]
    if tipo == "plan":
        return "", "Plan", " → ".join(PLAN[p] for p in ev["pasos"]) or f"sin consultas ({ev.get('intencion')})"
    if tipo == "plan_rechazado":
        return "error", "Plan rechazado", "; ".join(ev["errores"])
    if tipo == "herramienta":
        tiempo = f" ({ev['segundos']} s)" if ev["segundos"] >= 0.5 else ""      # las consultas locales tardan milésimas
        return ("error" if ev.get("error") else "herramienta"), ev["herramienta"], _resumen_resultado(ev) + tiempo
    if tipo == "aprobacion":
        return "aprobacion", "Aprobación", ("confirmada" if ev["aprobado"] else "cancelada") + f" para {ev['pedido']}"
    if tipo == "respuesta":
        return "", "Respuesta", f"estado {ev['estado']}"
    if tipo == "fallo_interno":
        return "error", "Fallo interno", f"{ev.get('etapa') or ev.get('herramienta')}: {ev['detalle'][:90]}"
    return None


def bitacora(eventos: list) -> str:
    """Línea de tiempo de lo que hizo el agente en la conversación, agrupada por turno."""
    encabezado = ('<div class="ardi-panel"><h3>Bitácora del agente</h3><div class="sub">Cada plan, consulta y aprobación '
                  'queda registrada. Esto es lo que ocurrió en esta conversación.</div>')
    if not eventos:
        return encabezado + '<div class="ardi-vacio">Aún no hay acciones. Escribe un mensaje para empezar.</div></div>'
    partes, turno_actual = [encabezado], None
    for ev in eventos:
        fila = _evento(ev)
        if fila is None:
            continue
        turno = str(ev["hilo"]).rsplit("-", 1)[-1]
        if turno != turno_actual:
            partes.append(f'<div class="ardi-turno">Turno {turno}</div>')
            turno_actual = turno
        clase, titulo, detalle = fila
        partes.append(f'<div class="ardi-evento {clase}"><b>{html.escape(titulo)}</b><span>{html.escape(detalle)}</span></div>')
    return "".join(partes) + "</div>"


# --- Datos de prueba -----------------------------------------------------------------------------------
SUGERENCIAS = [
    ("Estado de un pedido", "¿Dónde está mi pedido ORD-006?"),
    ("Devolver un producto", "Quiero devolver mi pedido ORD-003, no me gustó."),
    ("Llegó dañado", "El cepillo de dientes de mi pedido ORD-012 llegó con el mango roto."),
    ("Envío de una compra", "Si compro dos termos de 500 ml y vivo en Medellín, ¿pago envío?"),
]

PEDIDOS_DE_PRUEBA = [
    ("ORD-003", "Entregado hace 18 días", "Devolución por cambio de opinión (se resta el envío)"),
    ("ORD-012", "Entregado hace 3 días", "Producto dañado (el envío lo paga EcoMarket)"),
    ("ORD-011", "Entregado hace 46 días", "Fuera de plazo"),
    ("ORD-008", "Entregado hace 20 días", "Categoría sin devolución por cambio de opinión"),
    ("ORD-013", "Entregado hace 1 día", "Alimento: plazo de defecto de 2 días"),
    ("ORD-014", "Entregado hace 5 días", "El servicio de etiquetas falla"),
    ("ORD-006", "En tránsito", "Consulta de estado"),
    ("ORD-007", "Extraviado", "Pedido extraviado"),
]
