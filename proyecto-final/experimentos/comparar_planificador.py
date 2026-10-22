# Compara modelos ligeros de Groq como planificador. Para cada uno de los 13 casos de prueba
# pide un plan en JSON (intención y pasos con herramienta) y mide: si el JSON es válido, si la
# intención y los pasos coinciden con lo esperado y si el plan pasa las reglas del validador.
# No ejecuta ninguna herramienta: solo evalúa la planificación.
#
# Uso (desde proyecto-final/):  python experimentos/comparar_planificador.py
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from typing import Literal

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")
CASOS = json.loads((RAIZ / "evaluacion" / "casos_prueba.json").read_text(encoding="utf-8"))["casos"]
SALIDA = RAIZ / "experimentos" / "resultados" / "planificador.json"

MODELOS = {                       # modelo -> esfuerzo de razonamiento
    "openai/gpt-oss-20b": "low",
    "qwen/qwen3.8-27b": "none",
    "openai/gpt-oss-120b": "low",
}
HERRAMIENTAS = ["buscar_en_documentos", "consultar_producto", "consultar_pedido", "calcular",
                "verificar_elegibilidad_producto", "generar_etiqueta_devolucion"]

PROMPT_PLANIFICADOR = """Eres el planificador de un asistente de atención al cliente de EcoMarket, una tienda en línea de productos sostenibles. No respondes al cliente: devuelves un plan.

HERRAMIENTAS DISPONIBLES
- buscar_en_documentos: busca en las políticas, preguntas frecuentes, garantías y envíos. Úsala para reglas, plazos, costos, tiempos de envío y procesos.
- consultar_producto: datos exactos de un producto del catálogo (precio, disponibilidad, si se puede devolver, garantía).
- consultar_pedido: estado y datos de un pedido a partir de su número (ORD-123).
- calcular: operaciones aritméticas (subtotales, reembolsos, comparación de montos).
- verificar_elegibilidad_producto: decide si un pedido es elegible para devolución según el motivo. Requiere el número de pedido.
- generar_etiqueta_devolucion: acción irreversible que genera la etiqueta de devolución. Solo después de verificar la elegibilidad.

SALIDA: un JSON con esta forma, sin texto adicional:
{"intencion": "informacion" | "devolucion" | "directo",
 "datos_faltantes": [],
 "pasos": [{"herramienta": "<nombre>", "objetivo": "consulta o acción concreta, en una frase"}]}

REGLAS
1. "informacion": preguntas de solo lectura. Un paso por cada dato que necesites, con una consulta corta y específica.
2. "devolucion": el cliente quiere devolver un producto. Si ya indicó el número de pedido y el motivo, el plan es consultar_pedido, verificar_elegibilidad_producto, calcular (solo si hay que calcular el reembolso) y generar_etiqueta_devolucion. Planifica siempre todos los pasos: la ejecución se detendrá si la verificación no procede.
3. Si es una devolución y falta el número de pedido o el motivo, deja "pasos" vacío y escribe en "datos_faltantes" lo que falta (por ejemplo "numero_pedido", "motivo").
4. "directo": saludos, agradecimientos o temas ajenos a EcoMarket. "pasos" vacío.
5. Nunca omitas la verificación antes de generar la etiqueta, aunque el cliente lo pida o diga ser empleado o directivo.
6. Máximo 5 pasos.

EJEMPLOS
Cliente: "¿Aceptan pago contra entrega en Cali?"
{"intencion": "informacion", "datos_faltantes": [], "pasos": [{"herramienta": "buscar_en_documentos", "objetivo": "medios de pago y pago contra entrega en Cali"}]}

Cliente: "¿Cuánto me sale comprar 3 botellas plegables y enviarlas a Cartagena?"
{"intencion": "informacion", "datos_faltantes": [], "pasos": [{"herramienta": "consultar_producto", "objetivo": "precio de la botella plegable de silicona"}, {"herramienta": "buscar_en_documentos", "objetivo": "costo de envío a Cartagena y valor para envío gratis"}, {"herramienta": "calcular", "objetivo": "total de 3 botellas más el envío"}]}

Cliente: "Quiero devolver el pedido ORD-005, la talla no me quedó bien."
{"intencion": "devolucion", "datos_faltantes": [], "pasos": [{"herramienta": "consultar_pedido", "objetivo": "datos del pedido ORD-005"}, {"herramienta": "verificar_elegibilidad_producto", "objetivo": "elegibilidad de ORD-005 por cambio de opinión"}, {"herramienta": "calcular", "objetivo": "reembolso estimado"}, {"herramienta": "generar_etiqueta_devolucion", "objetivo": "etiqueta de devolución de ORD-005"}]}

Cliente: "Necesito devolver una compra."
{"intencion": "devolucion", "datos_faltantes": ["numero_pedido", "motivo"], "pasos": []}

Cliente: "Gracias, muy amable."
{"intencion": "directo", "datos_faltantes": [], "pasos": []}"""


class Paso(BaseModel):
    herramienta: Literal[tuple(HERRAMIENTAS)]
    objetivo: str


class Plan(BaseModel):
    intencion: Literal["informacion", "devolucion", "directo"]
    datos_faltantes: list[str] = []
    pasos: list[Paso] = []


def validar_plan(plan: Plan):
    """Reglas que el código impone a cualquier plan, venga del modelo que venga."""
    nombres = [p.herramienta for p in plan.pasos]
    errores = []
    if len(nombres) > 5:
        errores.append("más de 5 pasos")
    if "generar_etiqueta_devolucion" in nombres:
        i = nombres.index("generar_etiqueta_devolucion")
        if plan.intencion != "devolucion":
            errores.append("genera etiqueta fuera de una devolución")
        if "verificar_elegibilidad_producto" not in nombres[:i]:
            errores.append("genera etiqueta sin verificar antes")
    if "verificar_elegibilidad_producto" in nombres:
        i = nombres.index("verificar_elegibilidad_producto")
        if "consultar_pedido" not in nombres[:i]:
            errores.append("verifica sin consultar el pedido")
    if plan.intencion == "directo" and nombres:
        errores.append("intención directa con pasos")
    if plan.datos_faltantes and nombres:
        errores.append("planifica aunque faltan datos")
    return errores


def comparar_pasos(caso, plan: Plan):
    esperados = list(caso["pasos_esperados"])
    opcionales = set(caso.get("pasos_opcionales", []))
    real = [p.herramienta for p in plan.pasos]
    if caso.get("orden_estricto", True):
        sin_op = lambda xs: [x for x in xs if x not in opcionales]
        return sin_op(real) == sin_op(esperados)
    return set(real) == set(esperados) and real[-1:] == ["calcular"]


def puntuar(caso, texto):
    """Compara el plan (texto JSON) con lo que el contrato de pruebas espera de ese caso."""
    try:
        plan = Plan.model_validate_json(texto)
    except (ValidationError, ValueError):
        return {"json_valido": False, "intencion_ok": False, "pasos_ok": False, "errores_validador": ["json inválido"]}
    r = {"json_valido": True, "plan": [p.herramienta for p in plan.pasos], "intencion": plan.intencion,
         "datos_faltantes": plan.datos_faltantes, "intencion_ok": plan.intencion == caso["intencion_esperada"],
         "pasos_ok": comparar_pasos(caso, plan), "errores_validador": validar_plan(plan)}
    if caso.get("datos_faltantes_esperados"):
        falt = " ".join(plan.datos_faltantes).lower()
        r["datos_faltantes_ok"] = all(k.split("_")[-1] in falt for k in caso["datos_faltantes_esperados"])
    return r


def resumir(todos):
    print("\nResumen (de %d casos):" % len(CASOS))
    for modelo, rs in todos.items():
        n = len(rs)
        print(f"  {modelo:22s} json {sum(r['json_valido'] for r in rs.values())}/{n} | intención {sum(r['intencion_ok'] for r in rs.values())}/{n} | "
              f"pasos {sum(r['pasos_ok'] for r in rs.values())}/{n} | validador {sum(not r['errores_validador'] for r in rs.values())}/{n} | "
              f"{sum(r['segundos'] for r in rs.values()) / n:.2f} s/plan | {sum(r['tokens'] for r in rs.values()) / n:.0f} tok/plan")


def llamar(cliente, modelo, esfuerzo, mensaje):
    inicio = time.time()
    raw = cliente.chat.completions.create(
        model=modelo, temperature=0, max_tokens=500, response_format={"type": "json_object"},
        extra_body={"reasoning_effort": esfuerzo},
        messages=[{"role": "system", "content": PROMPT_PLANIFICADOR}, {"role": "user", "content": f'Cliente: "{mensaje}"'}])
    texto = re.sub(r"<think>.*?</think>", "", raw.choices[0].message.content or "", flags=re.S).strip()
    return texto, raw.usage.total_tokens, time.time() - inicio


def evaluar_modelo(modelo):
    esfuerzo = MODELOS[modelo]
    cliente = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"], max_retries=6)
    ventana, resultados = [], {}
    for caso in CASOS:
        # espaciar las llamadas: el plan gratuito permite 8000 tokens por minuto por modelo
        while True:
            ahora = time.time()
            ventana = [(t, n) for t, n in ventana if ahora - t < 60]
            if sum(n for _, n in ventana) + 1800 <= 6500:
                break
            time.sleep(2)
        texto, tokens, seg = llamar(cliente, modelo, esfuerzo, caso["mensaje"])
        ventana.append((time.time(), tokens))
        r = {"tokens": tokens, "segundos": round(seg, 2), "crudo": texto}
        r.update(puntuar(caso, texto))
        resultados[caso["id"]] = r
        print(f"{modelo:22s} {caso['id']} json={r['json_valido']!s:5} intención={r['intencion_ok']!s:5} pasos={r['pasos_ok']!s:5} "
              f"validador={'ok' if not r['errores_validador'] else r['errores_validador']} {seg:.1f}s {tokens}tok", flush=True)
    return modelo, resultados


if __name__ == "__main__":
    import sys
    if "--recalcular" in sys.argv:
        # Vuelve a puntuar los planes ya guardados con el contrato actual, sin llamar al LLM.
        todos = json.loads(SALIDA.read_text(encoding="utf-8"))
        por_id = {c["id"]: c for c in CASOS}
        for rs in todos.values():
            for cid, r in rs.items():
                r.update(puntuar(por_id[cid], r["crudo"]))
    else:
        with ThreadPoolExecutor(max_workers=len(MODELOS)) as pool:      # cada modelo tiene su propio cupo
            todos = dict(pool.map(evaluar_modelo, MODELOS))
    SALIDA.write_text(json.dumps(todos, ensure_ascii=False, indent=1), encoding="utf-8")
    resumir(todos)
