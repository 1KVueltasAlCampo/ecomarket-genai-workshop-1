# Herramientas del agente (simuladas). Cada una recibe argumentos tipados y devuelve un dict:
# los datos si todo salió bien, o {"error": CODIGO, "mensaje": ...} si no. Nunca lanzan excepciones
# hacia el agente ni devuelven trazas técnicas.
#
# Lo que ya existía en el Taller 2 se reutiliza: buscar_en_documentos consulta el mismo índice de
# Chroma, con el mismo modelo de embeddings y el mismo filtro de audiencia (ingesta.py).
import ast
import csv
import difflib
import hashlib
import hmac
import json
import operator
import os
import re
import time
import unicodedata
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from langchain_core.tools import tool

from pedidos import PEDIDOS

RAIZ = Path(__file__).parent
CATALOGO = RAIZ / "base_conocimiento" / "publico" / "catalogo_productos.csv"
REGISTRO = RAIZ / "registro_acciones.jsonl"

SECRETO = os.environ.get("SECRETO_ETIQUETAS", "ecomarket-proyecto-final").encode()
VIGENCIA_CODIGO_S = 30 * 60              # el código de verificación vale 30 minutos
DESCUENTO_ENVIO_RETORNO = 8000           # política: en un cambio de opinión el cliente paga el envío
PLAZO_CAMBIO_OPINION = 30                # días desde la entrega
PLAZO_DEFECTO = 5                        # días desde la entrega (2 para alimentos: 48 horas)
PLAZO_DEFECTO_ALIMENTOS = 2

TEMAS = {"devoluciones": "politica_devoluciones.pdf", "envios": "politica_envios.md",
         "garantias": "politica_garantias_sostenibilidad.docx", "faq": "faq.json",
         "catalogo": "catalogo_productos.csv"}


def hoy() -> date:
    """Fecha actual. En uso real es la del sistema; las pruebas la fijan con FECHA_SIMULADA."""
    simulada = os.environ.get("FECHA_SIMULADA")
    return date.fromisoformat(simulada) if simulada else date.today()


# --- Estado y registro ---------------------------------------------------------------------
_ETIQUETAS = set()                       # pedidos con etiqueta ya generada (en memoria)
_CONTEXTO = {"hilo": None}


def reiniciar_estado():
    _ETIQUETAS.clear()


def fijar_hilo(hilo):
    _CONTEXTO["hilo"] = hilo


def registrar(evento: dict):
    """Una línea JSON por evento: planes, llamadas a herramientas, aprobaciones y respuestas."""
    linea = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "hilo": _CONTEXTO["hilo"], **evento}
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False, default=str) + "\n")


def leer_registro(prefijo_hilo: str, ultimas: int = 3000) -> list:
    """Eventos de las conversaciones cuyo identificador empieza por el prefijo, en orden cronológico.
    Solo se leen las últimas líneas del archivo: el registro crece y la interfaz lo consulta en cada interacción."""
    if not REGISTRO.exists():
        return []
    eventos = []
    for linea in REGISTRO.read_text(encoding="utf-8").splitlines()[-ultimas:]:
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if str(evento.get("hilo") or "").startswith(prefijo_hilo):
            eventos.append(evento)
    return eventos


# --- Datos -----------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _catalogo():
    with open(CATALOGO, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        r["precio_cop"] = int(r["precio_cop"])
        r["garantia_meses"] = int(r["garantia_meses"])
        r["devolucion_permitida"] = r["devolucion_permitida"] == "Sí"
    return filas


def _norm(texto):
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def _pedido(numero):
    numero = (numero or "").strip().upper()
    return numero, PEDIDOS.get(numero)


# --- Herramientas ----------------------------------------------------------------------------
_indice = None


def preparar_indice():
    """Abre el índice vectorial del Taller 2. Si está vacío (primera ejecución en un clon limpio), lo construye
    con los documentos de base_conocimiento/, igual que `python ingesta.py`."""
    global _indice
    from ingesta import abrir_indice, construir_indice
    _indice = abrir_indice("bge-m3")
    if _indice._collection.count() == 0:
        from cargadores import cargar_base
        _indice = construir_indice("bge-m3", cargar_base(), _indice._embedding_function)
    return _indice


@tool
def buscar_en_documentos(consulta: str, tema: Optional[Literal["devoluciones", "envios", "garantias", "faq", "catalogo"]] = None) -> dict:
    """Busca en los documentos de EcoMarket (políticas de devoluciones, envíos y garantías, preguntas
    frecuentes y catálogo). Úsala para reglas, plazos, costos, tiempos y procesos. Formula una consulta
    corta y específica por cada dato que necesites. El parámetro tema es opcional y acota la búsqueda a un documento."""
    if _indice is None:
        preparar_indice()
    filtro = {"audiencia": "publico"}
    if tema:
        filtro = {"$and": [{"audiencia": "publico"}, {"fuente": TEMAS[tema]}]}
    res = _indice.similarity_search_with_score(consulta, k=5, filter=filtro)
    fragmentos = [{"documento": d.metadata["fuente"], "seccion": d.metadata["seccion"],
                   "similitud": round(1 - dist, 3), "texto": d.page_content} for d, dist in res]
    return {"fragmentos": fragmentos} if fragmentos else {"fragmentos": [], "aviso": "Sin resultados relevantes."}


@tool
def consultar_pedido(numero_pedido: str) -> dict:
    """Consulta un pedido por su número (formato ORD-123): producto, estado, fechas y enlace de rastreo."""
    numero, p = _pedido(numero_pedido)
    if p is None:
        return {"error": "PEDIDO_NO_ENCONTRADO", "mensaje": f"No existe el pedido {numero or numero_pedido}."}
    entrega = hoy() - timedelta(days=p["entregado_hace_dias"]) if "entregado_hace_dias" in p else None
    estimada = hoy() + timedelta(days=p["llega_en_dias"]) if "llega_en_dias" in p else None
    return {"numero_pedido": numero, "producto": p["producto"], "sku": p["sku"], "estado": p["estado"],
            "fecha_entrega": entrega.isoformat() if entrega else None,
            "fecha_estimada": estimada.isoformat() if estimada else None, "retrasado": p["retrasado"],
            "enlace_rastreo": f"https://ecomarket.com/track/{numero}"}


@tool
def consultar_producto(nombre_o_sku: str) -> dict:
    """Datos exactos de un producto del catálogo a partir de su nombre o sku: precio, disponibilidad,
    si admite devolución por cambio de opinión y garantía."""
    consulta = nombre_o_sku.strip()
    catalogo = _catalogo()
    por_sku = [r for r in catalogo if r["sku"].lower() == consulta.lower()]
    candidatos = por_sku
    if not candidatos:
        vacias = {"de", "del", "la", "el", "los", "las", "un", "una", "con", "para", "x"}
        palabras = [w for w in re.findall(r"[a-z0-9]+(?:,[0-9]+)?", _norm(consulta)) if w not in vacias]
        candidatos = [r for r in catalogo if palabras and all(w in _norm(r["nombre"]) for w in palabras)]
    if not candidatos:                                        # último recurso: parecido de texto
        cercanos = difflib.get_close_matches(_norm(consulta), [_norm(r["nombre"]) for r in catalogo], n=1, cutoff=0.6)
        candidatos = [r for r in catalogo if cercanos and _norm(r["nombre"]) == cercanos[0]]
    if not candidatos:
        return {"error": "PRODUCTO_NO_ENCONTRADO", "mensaje": f"No hay un producto que coincida con '{nombre_o_sku}'."}
    exactos = [r for r in candidatos if _norm(r["nombre"]) == _norm(consulta)]
    if len(candidatos) > 1 and len(exactos) != 1:
        return {"error": "PRODUCTO_AMBIGUO", "mensaje": "Hay varios productos que coinciden; hay que precisar cuál.",
                "candidatos": [{"sku": r["sku"], "nombre": r["nombre"]} for r in candidatos[:5]]}
    r = exactos[0] if len(candidatos) > 1 else candidatos[0]
    return {"sku": r["sku"], "nombre": r["nombre"], "categoria": r["categoria"], "precio_cop": r["precio_cop"],
            "disponibilidad": r["disponibilidad"], "devolucion_permitida": r["devolucion_permitida"],
            "motivo_restriccion": r["motivo_restriccion"] or None, "garantia_meses": r["garantia_meses"]}


_OPERADORES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
               ast.USub: operator.neg, ast.UAdd: operator.pos}


def _evaluar(nodo):
    if isinstance(nodo, ast.Expression):
        return _evaluar(nodo.body)
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)) and not isinstance(nodo.value, bool):
        return nodo.value
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.left), _evaluar(nodo.right))
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.operand))
    raise ValueError("operación no permitida")


@tool
def calcular(expresion: str) -> dict:
    """Calculadora segura: solo números y las operaciones + - * / con paréntesis. Escribe los números sin
    separador de miles (por ejemplo 2*69900 y no 2*69.900). Úsala para subtotales, reembolsos y comparaciones."""
    limpia = expresion.replace("×", "*").replace("÷", "/").replace("$", "").replace(" ", "")
    if not limpia or len(limpia) > 100:
        return {"error": "EXPRESION_INVALIDA", "mensaje": "La expresión está vacía o es demasiado larga."}
    try:
        valor = _evaluar(ast.parse(limpia, mode="eval"))
    except (ValueError, SyntaxError, ZeroDivisionError):
        return {"error": "EXPRESION_INVALIDA", "mensaje": "Solo se admiten números y las operaciones + - * / con paréntesis."}
    valor = int(valor) if float(valor).is_integer() else round(valor, 2)
    return {"expresion": limpia, "resultado": valor}


def _codigo(numero, motivo):
    vence = int(time.time()) + VIGENCIA_CODIGO_S
    return f"{motivo}.{vence}.{_firma(numero, motivo, vence)}"


def _firma(numero, motivo, vence):
    return hmac.new(SECRETO, f"{numero}|{motivo}|{vence}".encode(), hashlib.sha256).hexdigest()[:16]


@tool
def verificar_elegibilidad_producto(numero_pedido: str, motivo: Literal["cambio_de_opinion", "defecto_o_dano"]) -> dict:
    """Decide si un pedido es elegible para devolución según el motivo: cambio_de_opinion (al cliente no le
    gustó o ya no lo quiere) o defecto_o_dano (llegó roto, defectuoso o equivocado). Si es elegible devuelve un
    código de verificación, necesario para generar la etiqueta."""
    numero, p = _pedido(numero_pedido)
    if p is None:
        return {"error": "PEDIDO_NO_ENCONTRADO", "mensaje": f"No existe el pedido {numero or numero_pedido}."}
    producto = next(r for r in _catalogo() if r["sku"] == p["sku"])
    base = {"numero_pedido": numero, "motivo": motivo, "producto": producto["nombre"], "precio_cop": producto["precio_cop"]}
    if numero in _ETIQUETAS:
        return {**base, "elegible": False, "razon": "YA_TIENE_ETIQUETA", "detalle": "Este pedido ya tiene una etiqueta de devolución generada."}
    if p["estado"] != "Entregado":
        return {**base, "elegible": False, "razon": "NO_ENTREGADO", "detalle": f"El pedido está '{p['estado']}': solo se pueden devolver pedidos entregados."}
    dias = p["entregado_hace_dias"]
    plazo_defecto = PLAZO_DEFECTO_ALIMENTOS if producto["categoria"] == "Alimentos y Bebidas" else PLAZO_DEFECTO
    # Un defecto se atiende dentro de su propio plazo, aunque el cambio de opinión no proceda: así el agente
    # sabe si esa salida sigue abierta y no la ofrece cuando ya venció.
    alternativa_defecto = {"vigente": dias <= plazo_defecto, "plazo_dias": plazo_defecto, "dias_restantes": max(plazo_defecto - dias, 0)}
    if motivo == "cambio_de_opinion":
        plazo, a_cargo, descuento = PLAZO_CAMBIO_OPINION, "cliente", DESCUENTO_ENVIO_RETORNO
        if not producto["devolucion_permitida"]:
            return {**base, "elegible": False, "razon": "CATEGORIA_NO_RETORNABLE", "dias_desde_entrega": dias,
                    "detalle": f"{producto['categoria']}: {producto['motivo_restriccion']} No admite devolución por cambio de opinión.",
                    "alternativa_defecto": alternativa_defecto}
    else:
        plazo, a_cargo, descuento = plazo_defecto, "ecomarket", 0
    if dias > plazo:
        fuera = {**base, "elegible": False, "razon": "FUERA_DE_PLAZO", "dias_desde_entrega": dias, "plazo_dias": plazo,
                 "detalle": f"Pasaron {dias} días desde la entrega y el plazo para este motivo es de {plazo}."}
        return {**fuera, "alternativa_defecto": alternativa_defecto} if motivo == "cambio_de_opinion" else fuera
    return {**base, "elegible": True, "razon": "ELEGIBLE", "dias_desde_entrega": dias, "plazo_dias": plazo,
            "dias_restantes": plazo - dias, "envio_retorno_a_cargo": a_cargo, "se_resta_del_reembolso_cop": descuento,
            "codigo_verificacion": _codigo(numero, motivo)}


@tool
def generar_etiqueta_devolucion(numero_pedido: str, codigo_verificacion: str) -> dict:
    """Acción irreversible: genera la etiqueta de devolución de un pedido. Exige el código de verificación
    entregado por verificar_elegibilidad_producto y la aprobación previa del cliente."""
    numero, p = _pedido(numero_pedido)
    if p is None:
        return {"error": "PEDIDO_NO_ENCONTRADO", "mensaje": f"No existe el pedido {numero or numero_pedido}."}
    try:
        motivo, vence, firma = codigo_verificacion.split(".")
        valido = hmac.compare_digest(firma, _firma(numero, motivo, int(vence)))
    except (ValueError, AttributeError):
        valido = False
    if not valido:
        return {"error": "CODIGO_INVALIDO", "mensaje": "El código de verificación no es válido para este pedido."}
    if int(vence) < time.time():
        return {"error": "CODIGO_VENCIDO", "mensaje": "El código de verificación venció; hay que verificar de nuevo."}
    if numero in _ETIQUETAS:
        return {"error": "YA_GENERADA", "mensaje": "Este pedido ya tiene una etiqueta generada."}
    if numero == "ORD-014":                                   # falla simulada del servicio de etiquetas
        return {"error": "SERVICIO_NO_DISPONIBLE", "mensaje": "El servicio de etiquetas no está disponible en este momento."}
    _ETIQUETAS.add(numero)
    return {"etiqueta_id": "ETQ-" + hashlib.sha1(numero.encode()).hexdigest()[:6].upper(), "numero_pedido": numero,
            "transportadora": "EcoLogística", "vigencia_hasta": (hoy() + timedelta(days=7)).isoformat(),
            "instrucciones": ["Imprime la etiqueta y pégala en el paquete, con el producto en su empaque original.",
                              "Entrega el paquete en un punto de recolección de la transportadora antes de que venza.",
                              "El reembolso se procesa en 5 a 7 días hábiles después de que se reciba e inspeccione el producto."]}


HERRAMIENTAS = {t.name: t for t in (buscar_en_documentos, consultar_pedido, consultar_producto, calcular,
                                    verificar_elegibilidad_producto, generar_etiqueta_devolucion)}


def _resumen(resultado):
    """Versión corta del resultado para el registro (los fragmentos se reducen a documento y sección)."""
    if "fragmentos" in resultado:
        return {"fragmentos": [f"{f['documento']} | {f['seccion']}" for f in resultado["fragmentos"]]}
    return {k: v for k, v in resultado.items() if k != "codigo_verificacion"}


def ejecutar(nombre: str, argumentos: dict) -> dict:
    """Ejecuta una herramienta, valida sus argumentos y deja constancia en el registro."""
    inicio = time.time()
    try:
        resultado = HERRAMIENTAS[nombre].invoke(argumentos)
    except Exception as e:                                    # argumentos mal formados u error interno
        resultado = {"error": "ERROR_EN_HERRAMIENTA", "mensaje": "No se pudo completar la consulta."}
        registrar({"evento": "fallo_interno", "herramienta": nombre, "args": argumentos, "detalle": repr(e)[:200]})
    registrar({"evento": "herramienta", "herramienta": nombre, "args": argumentos, "resultado": _resumen(resultado),
               "error": resultado.get("error"), "segundos": round(time.time() - inicio, 2)})
    return resultado
