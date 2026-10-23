# Pruebas del proyecto final.
#   python pruebas.py herramientas   -> pruebas de las herramientas, sin LLM (rápidas y deterministas)
#   python pruebas.py interfaz       -> la app de Streamlit completa con modelos simulados (sin LLM)
#   python pruebas.py agente         -> el contrato de casos_prueba.json contra el agente (usa el LLM)
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("FECHA_SIMULADA", "2026-10-21")        # las pruebas fijan la fecha

RAIZ = Path(__file__).parent
import herramientas as h                                       # noqa: E402

resultados = []


def verificar(nombre, condicion, detalle=""):
    resultados.append(bool(condicion))
    print(f"  {'ok   ' if condicion else 'FALLA'} {nombre}" + ("" if condicion or not detalle else f"  -> {detalle}"))


def modelos_simulados(redactor):
    """Reemplaza las tres llamadas a modelos del agente por versiones deterministas: el planificador siempre propone
    la devolución completa de ORD-003, el ejecutor entrega los argumentos correctos y 'redactor' hace de modelo de
    respuesta. Sirve para probar el grafo y la interfaz sin gastar cupo del proveedor."""
    from contextlib import ExitStack
    from unittest.mock import patch

    import agente as a
    plan = a.Plan(intencion="devolucion", pasos=[a.Paso(herramienta=n, objetivo="x") for n in (
        "consultar_pedido", "verificar_elegibilidad_producto", "calcular", "generar_etiqueta_devolucion")])
    argumentos = {"consultar_pedido": {"numero_pedido": "ORD-003"},
                  "verificar_elegibilidad_producto": {"numero_pedido": "ORD-003", "motivo": "cambio_de_opinion"},
                  "calcular": {"expresion": "19900 - 8000"}}
    pila = ExitStack()
    pila.enter_context(patch.object(a, "planificar_con_modelo", lambda m, hist: plan))
    pila.enter_context(patch.object(a, "argumentos_del_paso", lambda paso, m, hist, hechos: argumentos[paso["herramienta"]]))
    pila.enter_context(patch.object(a, "redactar_respuesta", redactor))
    return pila


def probar_herramientas():
    h.reiniciar_estado()
    ej = h.ejecutar

    print("calcular")
    verificar("reembolso 19900 - 8000", ej("calcular", {"expresion": "19900 - 8000"}).get("resultado") == 11900)
    verificar("dos termos 2*69900", ej("calcular", {"expresion": "2*69900"}).get("resultado") == 139800)
    verificar("acepta $ y ×", ej("calcular", {"expresion": "$2 × 100"}).get("resultado") == 200)
    verificar("rechaza código arbitrario", ej("calcular", {"expresion": "__import__('os').system('echo hola')"}).get("error") == "EXPRESION_INVALIDA")
    verificar("rechaza división por cero", ej("calcular", {"expresion": "10/0"}).get("error") == "EXPRESION_INVALIDA")

    print("consultar_pedido")
    p = ej("consultar_pedido", {"numero_pedido": "ord-006"})
    verificar("estado y rastreo de ORD-006", p.get("estado") == "En tránsito" and p["enlace_rastreo"].endswith("ORD-006"))
    verificar("fecha de entrega relativa a hoy (ORD-003, 18 días)", ej("consultar_pedido", {"numero_pedido": "ORD-003"}).get("fecha_entrega") == "2026-10-03")
    verificar("pedido inexistente", ej("consultar_pedido", {"numero_pedido": "ORD-999"}).get("error") == "PEDIDO_NO_ENCONTRADO")

    print("consultar_producto")
    verificar("por nombre parcial: termo familiar", ej("consultar_producto", {"nombre_o_sku": "termo familiar"}).get("sku") == "PROD-030")
    verificar("por nombre: termo de 500 ml", ej("consultar_producto", {"nombre_o_sku": "termo de 500 ml"}).get("sku") == "PROD-002")
    verificar("por sku", ej("consultar_producto", {"nombre_o_sku": "prod-008"}).get("nombre", "").startswith("Champú"))
    verificar("ambiguo: 'termo'", ej("consultar_producto", {"nombre_o_sku": "termo"}).get("error") == "PRODUCTO_AMBIGUO")
    verificar("inexistente", ej("consultar_producto", {"nombre_o_sku": "bicicleta eléctrica"}).get("error") == "PRODUCTO_NO_ENCONTRADO")
    verificar("precio y devolución del champú", (lambda r: r.get("precio_cop") == 22900 and r["devolucion_permitida"] is False)(ej("consultar_producto", {"nombre_o_sku": "champú sólido"})))

    print("verificar_elegibilidad_producto")
    casos = [
        ("ORD-003", "cambio_de_opinion", True, "ELEGIBLE"),
        ("ORD-008", "cambio_de_opinion", False, "CATEGORIA_NO_RETORNABLE"),     # C06
        ("ORD-008", "defecto_o_dano", False, "FUERA_DE_PLAZO"),                 # 20 días > 5
        ("ORD-011", "cambio_de_opinion", False, "FUERA_DE_PLAZO"),              # C07, 46 días
        ("ORD-012", "defecto_o_dano", True, "ELEGIBLE"),                        # C08, higiene con defecto a 3 días
        ("ORD-012", "cambio_de_opinion", False, "CATEGORIA_NO_RETORNABLE"),
        ("ORD-013", "defecto_o_dano", True, "ELEGIBLE"),                        # alimento a 1 día (límite 2)
        ("ORD-001", "cambio_de_opinion", False, "NO_ENTREGADO"),
        ("ORD-014", "cambio_de_opinion", True, "ELEGIBLE"),                     # C13
    ]
    for pedido, motivo, elegible, razon in casos:
        r = ej("verificar_elegibilidad_producto", {"numero_pedido": pedido, "motivo": motivo})
        verificar(f"{pedido} {motivo}: {razon}", r.get("elegible") is elegible and r.get("razon") == razon, str(r)[:120])
    alt = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-012", "motivo": "cambio_de_opinion"}).get("alternativa_defecto", {})
    verificar("no retornable a 3 días: la vía de defecto sigue vigente (2 días restantes)", alt.get("vigente") is True and alt.get("dias_restantes") == 2, str(alt))
    alt = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-008", "motivo": "cambio_de_opinion"}).get("alternativa_defecto", {})
    verificar("no retornable a 20 días: la vía de defecto ya venció", alt.get("vigente") is False, str(alt))
    r = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-003", "motivo": "cambio_de_opinion"})
    verificar("cambio de opinión: envío a cargo del cliente, descuento $8.000", r["envio_retorno_a_cargo"] == "cliente" and r["se_resta_del_reembolso_cop"] == 8000)
    r = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-012", "motivo": "defecto_o_dano"})
    verificar("defecto: envío a cargo de EcoMarket, sin descuento", r["envio_retorno_a_cargo"] == "ecomarket" and r["se_resta_del_reembolso_cop"] == 0)
    fuera = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-011", "motivo": "cambio_de_opinion"})
    verificar("fuera de plazo (46 días): también informa que el plazo de defecto venció", fuera.get("razon") == "FUERA_DE_PLAZO" and fuera.get("alternativa_defecto", {}).get("vigente") is False, str(fuera.get("alternativa_defecto")))
    verificar("no elegible no entrega código","codigo_verificacion" not in ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-008", "motivo": "cambio_de_opinion"}))
    verificar("pedido inexistente", ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-999", "motivo": "cambio_de_opinion"}).get("error") == "PEDIDO_NO_ENCONTRADO")
    verificar("motivo fuera de lo permitido se rechaza", ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-003", "motivo": "porque si"}).get("error") == "ERROR_EN_HERRAMIENTA")

    print("verificar_elegibilidad_producto: los días límite")
    original = dict(h.PEDIDOS["ORD-003"]), dict(h.PEDIDOS["ORD-014"]), dict(h.PEDIDOS["ORD-013"])

    def razon(pedido, dias, motivo):
        h.PEDIDOS[pedido]["entregado_hace_dias"] = dias
        return ej("verificar_elegibilidad_producto", {"numero_pedido": pedido, "motivo": motivo})["razon"]

    verificar("cambio de opinión: día 30 sí, día 31 no", (razon("ORD-003", 30, "cambio_de_opinion"), razon("ORD-003", 31, "cambio_de_opinion")) == ("ELEGIBLE", "FUERA_DE_PLAZO"))
    verificar("defecto: día 5 sí, día 6 no", (razon("ORD-014", 5, "defecto_o_dano"), razon("ORD-014", 6, "defecto_o_dano")) == ("ELEGIBLE", "FUERA_DE_PLAZO"))
    verificar("defecto en alimentos: día 2 sí, día 3 no", (razon("ORD-013", 2, "defecto_o_dano"), razon("ORD-013", 3, "defecto_o_dano")) == ("ELEGIBLE", "FUERA_DE_PLAZO"))
    for pedido, datos in zip(("ORD-003", "ORD-014", "ORD-013"), original):
        h.PEDIDOS[pedido].update(datos)

    print("generar_etiqueta_devolucion (los candados)")
    codigo = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-003", "motivo": "cambio_de_opinion"})["codigo_verificacion"]
    verificar("sin código válido: CODIGO_INVALIDO", ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-003", "codigo_verificacion": "inventado"}).get("error") == "CODIGO_INVALIDO")
    verificar("código de otro pedido: CODIGO_INVALIDO", ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-012", "codigo_verificacion": codigo}).get("error") == "CODIGO_INVALIDO")
    verificar("código alterado: CODIGO_INVALIDO", ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-003", "codigo_verificacion": codigo[:-1] + ("0" if codigo[-1] != "0" else "1")}).get("error") == "CODIGO_INVALIDO")
    vencido = f"cambio_de_opinion.{int(time.time()) - 10}.{h._firma('ORD-003', 'cambio_de_opinion', int(time.time()) - 10)}"
    verificar("código vencido: CODIGO_VENCIDO", ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-003", "codigo_verificacion": vencido}).get("error") == "CODIGO_VENCIDO")
    verificar("nada se generó con códigos malos", "ORD-003" not in h._ETIQUETAS)
    e = ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-003", "codigo_verificacion": codigo})
    verificar("con código válido se genera", e.get("etiqueta_id", "").startswith("ETQ-") and e["transportadora"] == "EcoLogística", str(e)[:100])
    verificar("repetir: YA_GENERADA", ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-003", "codigo_verificacion": codigo}).get("error") == "YA_GENERADA")
    verificar("verificar de nuevo: YA_TIENE_ETIQUETA", ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-003", "motivo": "cambio_de_opinion"}).get("razon") == "YA_TIENE_ETIQUETA")
    c14 = ej("verificar_elegibilidad_producto", {"numero_pedido": "ORD-014", "motivo": "cambio_de_opinion"})["codigo_verificacion"]
    verificar("servicio caído (ORD-014): SERVICIO_NO_DISPONIBLE", ej("generar_etiqueta_devolucion", {"numero_pedido": "ORD-014", "codigo_verificacion": c14}).get("error") == "SERVICIO_NO_DISPONIBLE")
    verificar("y no queda registrada como generada", "ORD-014" not in h._ETIQUETAS)

    print("buscar_en_documentos")
    r = ej("buscar_en_documentos", {"consulta": "umbral de envío gratis en la Zona 1", "tema": "envios"})
    verificar("el tema acota a un documento", r["fragmentos"] and {f["documento"] for f in r["fragmentos"]} == {"politica_envios.md"})
    r = ej("buscar_en_documentos", {"consulta": "hasta qué monto puede aprobar un agente una compensación"})
    verificar("nunca devuelve el documento interno", all(f["documento"] != "guia_atencion_interna.txt" for f in r["fragmentos"]))
    verificar("sin tema: hasta 5 fragmentos", len(r["fragmentos"]) == 5)

    print("respuesta al cliente: salvaguardas en código (agente.py)")
    import agente as a
    hechos = {"1_verificar": {"elegible": False, "razon": "FUERA_DE_PLAZO", "detalle": "Pasaron 46 días", "codigo_verificacion": "abc"},
              "2_pedido": {"error": "PEDIDO_NO_ENCONTRADO", "mensaje": "No existe el pedido"}}
    visto = a._compactar(hechos)
    verificar("el modelo no ve códigos internos (razon, error, código de verificación)",
              not any(c in visto for c in ("FUERA_DE_PLAZO", "PEDIDO_NO_ENCONTRADO", "abc")))
    verificar("pero sí el texto que explica el resultado", "Pasaron 46 días" in visto and "No existe el pedido" in visto)
    frag = {"fragmentos": [{"documento": "politica_envios.md", "texto": "x"}, {"documento": "faq.json", "texto": "y"}]}
    verificar("fuentes: solo nombres de documentos recuperados", a._fuentes({"1_buscar": frag, "2_calcular": {"resultado": 1}}) == "faq.json, politica_envios.md")
    verificar("fuentes: 'ninguna' si no se consultaron documentos", a._fuentes({"1_pedido": {"estado": "Entregado"}}) == "ninguna")
    verificar("guiones y espacios no separables pasan a normales", a._limpiar("ETQ‑123 y ORD‐011: 8 900 COP") == "ETQ-123 y ORD-011: 8 900 COP")

    from unittest.mock import patch

    class ModeloEspia:
        """Reemplaza al modelo de respuesta y guarda lo que el agente le envía."""
        enviado = None

        def __init__(self, **_):
            pass

        def invoke(self, mensajes):
            ModeloEspia.enviado = "\n".join(m.content for m in mensajes)
            return type("R", (), {"content": "ok", "usage_metadata": None})()

    os.environ.setdefault("GROQ_API_KEY", "llave-de-prueba")
    with patch.object(a, "ChatOpenAI", ModeloEspia):
        a.redactar_respuesta({"mensaje": "¿y el de 500 ml?", "estado": "ok", "hechos": {}, "historial": [
            {"rol": "Cliente", "texto": "¿Cuánto cuesta el termo familiar?"}, {"rol": "Asistente", "texto": "Cuesta 99.900 pesos."}]})
    verificar("la respuesta final recibe el historial de la conversación", "termo familiar" in (ModeloEspia.enviado or "") and "99.900" in ModeloEspia.enviado)

    print("fallos del modelo: el grafo completo con modelos simulados (sin LLM)")
    from unittest.mock import patch

    def se_cae(*_, **__):
        raise RuntimeError("429 límite de uso")

    h.reiniciar_estado()
    with modelos_simulados(se_cae):
        ag = a.Agente()
        r = ag.conversar("Quiero devolver el pedido ORD-003, no me gustó")
        verificar("antes de generar la etiqueta se pide la aprobación", r["pendiente"] is not None and r["pendiente"]["reembolso_estimado_cop"] == 11900)
        r = ag.reanudar(r["hilo"], True)
        verificar("si falla la redacción, la etiqueta generada igual se informa", r["etiqueta_generada"] and "ETQ-" in r["respuesta"] and "28 de octubre de 2026" in r["respuesta"], r["respuesta"][:80])
        r = a.Agente().conversar("Quiero devolver de nuevo el pedido ORD-003")      # ya tiene etiqueta: no elegible
    verificar("si falla la redacción y no se generó etiqueta: mensaje claro", r["respuesta"] == a.MENSAJE_SISTEMA and not r["etiqueta_generada"])
    h.reiniciar_estado()
    with patch.object(a, "planificar_con_modelo", se_cae):
        r = a.Agente().conversar("¿Dónde está mi pedido ORD-006?")
    verificar("si falla el planificador: mensaje claro y sin excepción", r["estado"] == "error_sistema" and r["respuesta"] == a.MENSAJE_SISTEMA and "429" not in r["respuesta"])

    h.reiniciar_estado()
    with modelos_simulados(se_cae):
        try:
            correr(a.Agente(), "Quiero devolver mi pedido ORD-003, no me gustó.")
            detuvo = False
        except RuntimeError:
            detuvo = True
    verificar("la evaluación se detiene si el modelo falla, en vez de guardar la respuesta de emergencia", detuvo)

    print("avance en vivo y bitácora (sin LLM)")
    h.reiniciar_estado()
    nodos = []
    with modelos_simulados(lambda e: "Listo"):
        ag = a.Agente()
        sin_avance = ag.conversar("Quiero devolver el pedido ORD-003")
        h.reiniciar_estado()
        r = ag.conversar("Quiero devolver el pedido ORD-003", avance=lambda nodo, cambios: nodos.append(nodo))
        verificar("el avance informa cada nodo hasta la pausa de aprobación", nodos == ["planificar", "ejecutar", "ejecutar", "ejecutar"] and r["pendiente"] is not None, str(nodos))
        verificar("con y sin avance se pide lo mismo al cliente", r["pendiente"] == sin_avance["pendiente"] and r.keys() == sin_avance.keys())
        nodos.clear()
        r2 = ag.reanudar(r["hilo"], True, avance=lambda nodo, cambios: nodos.append(nodo))
        h.reiniciar_estado()
        sin_avance2 = ag.reanudar(sin_avance["hilo"], True)
        verificar("al terminar, con y sin avance el resultado es el mismo",
                  {k: v for k, v in r2.items() if k != "hilo"} == {k: v for k, v in sin_avance2.items() if k != "hilo"})
        verificar("al confirmar: aprobar, generar y responder", nodos == ["aprobar", "generar", "responder"] and r2["etiqueta_generada"] and r2["respuesta"] == "Listo", str(nodos))
    eventos = h.leer_registro(r["hilo"])
    verificar("la bitácora trae los eventos de esa conversación y solo esos",
              {"mensaje", "herramienta", "aprobacion", "respuesta"} <= {e["evento"] for e in eventos} and all(e["hilo"] == r["hilo"] for e in eventos))
    verificar("un prefijo desconocido no devuelve nada", h.leer_registro("no-existe") == [])
    h.reiniciar_estado()

    print("buscar_en_documentos: sin regresión frente al Taller 2 (23 preguntas con evidencia, k=5)")
    ev = json.loads((RAIZ.parent / "taller-2" / "evaluacion" / "preguntas_evaluacion.json").read_text(encoding="utf-8"))["preguntas"]
    ref = json.loads((RAIZ.parent / "taller-2" / "evaluacion" / "resultados" / "embeddings.json").read_text(encoding="utf-8"))["bge-m3"]
    completas, fracciones = 0, []
    for q in (x for x in ev if x.get("evidencia")):
        texto = "\n".join(f["texto"] for f in h.buscar_en_documentos.invoke({"consulta": q["pregunta"]})["fragmentos"]).lower()
        hallada = sum(e.lower() in texto for e in q["evidencia"]) / len(q["evidencia"])
        fracciones.append(hallada)
        completas += hallada == 1
    media = sum(fracciones) / len(fracciones)
    verificar(f"preguntas con la evidencia completa: {completas} (Taller 2: {ref['preguntas_completas@5']})", completas == ref["preguntas_completas@5"])
    verificar(f"evidencia@5: {media:.3f} (Taller 2: {ref['evidencia@5']})", abs(media - ref["evidencia@5"]) < 0.001)

    print(f"\n{sum(resultados)} de {len(resultados)} pruebas superadas")
    return all(resultados)


SALIDA_AGENTE = RAIZ / "evaluacion" / "resultados" / "agente.json"
TRAZAS = re.compile(r"PEDIDO_NO_ENCONTRADO|CODIGO_|SERVICIO_NO_DISPONIBLE|CATEGORIA_NO_RETORNABLE|FUERA_DE_PLAZO|Traceback|ERROR_EN_HERRAMIENTA|YA_GENERADA")
# Comprobaciones simples sobre el texto de la respuesta (datos que salen de las herramientas)
CONTENIDO = {
    "C01": lambda t, d: re.search(r"5\s*(a|-|–|y)\s*7", t) is not None and re.search(r"8\s*(a|-|–|y)\s*10", t) is None,
    "C02": lambda t, d: "99900" in d,
    "C03": lambda t, d: "tránsito" in t.lower() and "ORD-006" in t,
    "C04": lambda t, d: "139800" in d and re.search(r"gratis|gratuit|sin costo|no pagas|no pagar", t.lower()) is not None,
    "C05": lambda t, d: "11900" in d and "ETQ-" in t,
    "C07": lambda t, d: "46" in t and (re.search(r"dañad|defect", t.lower()) is None or re.search(r"venci|expir|no est[aá] vigente|ya no (est[aá] vigente|aplica)", t.lower()) is not None),
    "C08": lambda t, d: "ETQ-" in t,
    "C09": lambda t, d: "ORD-999" in t or "verific" in t.lower(),
    "C10": lambda t, d: "pedido" in t.lower(),
    "C13": lambda t, d: "agente" in t.lower() and "ETQ-" not in t,
}


def sin_fallos_del_modelo(*resultados):
    """Si un modelo falla (por ejemplo, cupo agotado), el agente responde con un mensaje de emergencia: esa corrida
    no mide al agente y no debe guardarse como resultado. Se detiene la evaluación y se reanuda después."""
    for r in resultados:
        fallos = [e for e in h.leer_registro(r["hilo"]) if e["evento"] == "fallo_interno" and e.get("etapa") in ("respuesta", "agente")]
        if fallos:
            raise RuntimeError("falló el modelo: " + fallos[0]["detalle"])


def correr(agente, mensaje, historial=None, aprobar=True):
    """Un mensaje completo: si el agente pide aprobación, se responde con 'aprobar'."""
    inicio = time.time()
    h.reiniciar_estado()
    r = agente.conversar(mensaje, historial)
    pidio_aprobacion = r["pendiente"] is not None
    if pidio_aprobacion:
        r = agente.reanudar(r["hilo"], aprobar)
    sin_fallos_del_modelo(r)
    return {"mensaje": mensaje, "respuesta": r["respuesta"], "estado": r["estado"], "plan": r["plan"],
            "ejecutadas": r["pasos_ejecutados"], "pidio_aprobacion": pidio_aprobacion,
            "etiqueta_generada": r["etiqueta_generada"], "segundos": round(time.time() - inicio, 1)}


def evaluar_corrida(caso, r):
    esperadas = set(caso["herramientas_ejecutadas_esperadas"])
    opcionales = set(caso.get("pasos_opcionales", []))
    texto = r["respuesta"] or ""
    digitos = re.sub(r"[\s.,  ]", "", texto)
    prueba_texto = CONTENIDO.get(caso["id"])
    return {"herramientas_ok": set(r["ejecutadas"]) - opcionales == esperadas - opcionales,
            "etiqueta_ok": r["etiqueta_generada"] == caso["etiqueta_generada"],
            "sin_trazas": TRAZAS.search(texto) is None,
            "contenido_ok": prueba_texto(texto, digitos) if prueba_texto else None,
            "aprobacion_ok": r["pidio_aprobacion"] == ("generar_etiqueta_devolucion" in r["ejecutadas"])}


def probar_agente():
    from agente import Agente
    contrato = json.loads((RAIZ / "evaluacion" / "casos_prueba.json").read_text(encoding="utf-8"))
    cache = json.loads(SALIDA_AGENTE.read_text(encoding="utf-8")) if SALIDA_AGENTE.exists() else {}
    agente = Agente()

    def guardar():
        SALIDA_AGENTE.parent.mkdir(parents=True, exist_ok=True)
        SALIDA_AGENTE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        for caso in contrato["casos"]:
            for rep in range(1, (3 if caso["critico"] else 1) + 1):
                clave = f"{caso['id']}#{rep}"
                if clave in cache:
                    continue
                r = correr(agente, caso["mensaje"])
                r["evaluacion"] = evaluar_corrida(caso, r)
                cache[clave] = r
                guardar()
                print(f"{clave:7s} herramientas={r['evaluacion']['herramientas_ok']!s:5} etiqueta={r['evaluacion']['etiqueta_ok']!s:5} "
                      f"sin_trazas={r['evaluacion']['sin_trazas']!s:5} contenido={r['evaluacion']['contenido_ok']!s:5} "
                      f"ejecutadas={r['ejecutadas']} {r['segundos']}s", flush=True)
        # El cliente cancela en la pantalla de aprobación: nunca debe generarse la etiqueta.
        if "RECHAZO" not in cache:
            r = correr(agente, "Quiero devolver mi pedido ORD-003, no me gustó.", aprobar=False)
            r["evaluacion"] = {"etiqueta_ok": not r["etiqueta_generada"] and r["pidio_aprobacion"] and r["estado"] == "cancelado"}
            cache["RECHAZO"] = r
            guardar()
            print(f"RECHAZO pidio_aprobacion={r['pidio_aprobacion']} estado={r['estado']} etiqueta={r['etiqueta_generada']}", flush=True)
        # Escenario de tres turnos (S1)
        if "S1" not in cache:
            h.reiniciar_estado()
            historial, turnos = [], []
            t1 = agente.conversar("Quiero devolver algo que compré.", historial)
            historial += [{"rol": "Cliente", "texto": "Quiero devolver algo que compré."}, {"rol": "Asistente", "texto": t1["respuesta"]}]
            m2 = "Es el pedido ORD-003, no me gustó."
            t2 = agente.conversar(m2, historial)
            t3 = agente.reanudar(t2["hilo"], True) if t2["pendiente"] else t2
            sin_fallos_del_modelo(t1, t3)
            cache["S1"] = {"turno1": {"respuesta": t1["respuesta"], "ejecutadas": t1["pasos_ejecutados"]},
                           "turno2_pendiente": t2["pendiente"], "turno3": {"respuesta": t3["respuesta"], "etiqueta_generada": t3.get("etiqueta_generada")},
                           "evaluacion": {"turno1_sin_herramientas": t1["pasos_ejecutados"] == [], "aprobacion_en_turno2": t2["pendiente"] is not None,
                                          "etiqueta_en_turno3": bool(t3.get("etiqueta_generada"))}}
            guardar()
            print("S1", cache["S1"]["evaluacion"], flush=True)
    except Exception as e:                          # por ejemplo, se agotó la cuota diaria de Groq: se guarda lo avanzado
        guardar()
        print("\nSe detuvo (lo avanzado quedó guardado; vuelve a ejecutar para continuar):", str(e)[:200])
        return False
    return resumir_agente(contrato, cache)


def resumir_agente(contrato, cache):
    casos = {c["id"]: c for c in contrato["casos"]}
    primeras = {k: v for k, v in cache.items() if k.endswith("#1")}
    herr = sum(v["evaluacion"]["herramientas_ok"] for v in primeras.values())
    print(f"\nSelección de herramientas correcta (una ejecución por caso): {herr} de {len(primeras)}  (criterio: 11 o más de 13)")
    criticos = {k: v for k, v in cache.items() if k.split("#")[0] in casos and casos[k.split('#')[0]]["critico"]}
    indebidas = [k for k, v in cache.items() if k.split("#")[0] in casos and v["etiqueta_generada"] != casos[k.split("#")[0]]["etiqueta_generada"]]
    print(f"Ejecuciones críticas: {len(criticos)} | etiquetas indebidas (en cualquier caso): {len(indebidas)} {indebidas}")
    print(f"Respuestas con trazas técnicas: {sum(not v['evaluacion']['sin_trazas'] for k, v in cache.items() if '#' in k)}")
    print(f"Aprobación solicitada exactamente cuando se iba a generar la etiqueta: {sum(v['evaluacion']['aprobacion_ok'] for k, v in cache.items() if '#' in k)} de {len([k for k in cache if '#' in k])}")
    print("Cancelación del cliente:", cache.get("RECHAZO", {}).get("evaluacion"))
    print("Escenario S1:", cache.get("S1", {}).get("evaluacion"))
    return True


def probar_interfaz():
    """La app completa (app.py) con el motor de pruebas de Streamlit y modelos simulados: no gasta cupo del proveedor."""
    from unittest.mock import patch

    from streamlit.testing.v1 import AppTest

    os.environ.setdefault("GROQ_API_KEY", "llave-de-prueba")

    def redactor(e):
        etiqueta = next((v for v in e["hechos"].values() if "etiqueta_id" in v), None)
        return f"Listo, tu etiqueta es {etiqueta['etiqueta_id']}. Reembolso estimado: $11.900." if etiqueta else "Entendido, no generé nada."

    def textos(app):
        return [m.value for m in app.markdown]

    def botones(app):
        return [b.key for b in app.button if b.key in ("confirmar", "cancelar")]

    def hay_etiqueta(app, contiene=""):
        return any('class="ardi-etiqueta"' in t and contiene in t for t in textos(app))

    h.reiniciar_estado()
    with modelos_simulados(redactor), patch.object(h, "preparar_indice", lambda: None):
        print("interfaz: devolución completa con confirmación")
        app = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60).run()
        verificar("la app arranca sin errores y muestra la bienvenida", not app.exception and any("Cuéntame qué necesitas" in t for t in textos(app)))
        app.chat_input[0].set_value("Quiero devolver mi pedido ORD-003, no me gustó").run()
        verificar("pide la aprobación con sus dos botones", botones(app) == ["confirmar", "cancelar"] and not app.exception)
        verificar("la tarjeta resume lo que se va a aprobar", any("ORD-003" in t and "$11.900" in t and "Kit de Pajillas" in t for t in textos(app)))
        verificar("mientras tanto el campo de texto está desactivado", app.chat_input[0].disabled)
        verificar("todavía no hay etiqueta", not hay_etiqueta(app))
        app.button(key="confirmar").click().run()
        verificar("al confirmar aparece la etiqueta", hay_etiqueta(app, "ETQ-") and botones(app) == [])
        verificar("el monto en pesos no se interpreta como fórmula", any(r"\$11.900" in t for t in textos(app)))
        verificar("la bitácora lista el turno, la herramienta y la aprobación",
                  any("Turno 1" in t and "generar_etiqueta_devolucion" in t and "Aprobación" in t for t in textos(app)))
        verificar("la bitácora resume cada resultado en una frase, sin JSON",
                  any("ORD-003: Entregado" in t and "= 11900" in t and "elegible, quedan 12 días" in t and '{"' not in t.split("Bitácora")[-1] for t in textos(app)))
        verificar("el campo de texto vuelve a estar activo", not app.chat_input[0].disabled)

        print("interfaz: cancelación y nueva conversación")
        h.reiniciar_estado()
        nueva = next(b for b in app.button if b.label == "Nueva conversación")
        nueva.click().run()
        verificar("nueva conversación vacía", any("Cuéntame qué necesitas" in t for t in textos(app)) and not hay_etiqueta(app))
        app.chat_input[0].set_value("Quiero devolver mi pedido ORD-003, no me gustó").run()
        app.button(key="cancelar").click().run()
        verificar("al cancelar no se genera ninguna etiqueta", "ORD-003" not in h._ETIQUETAS and not hay_etiqueta(app))
        verificar("y la conversación sigue", any("no generé nada" in t for t in textos(app)) and not app.chat_input[0].disabled)

        print("interfaz: sugerencias de la bienvenida")
        nueva = next(b for b in app.button if b.label == "Nueva conversación")
        nueva.click().run()
        app.button(key="sugerencia-Devolver un producto").click().run()
        verificar("una sugerencia equivale a escribir el mensaje", botones(app) == ["confirmar", "cancelar"])
    h.reiniciar_estado()
    print(f"\n{sum(resultados)} de {len(resultados)} pruebas superadas")
    return all(resultados)


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "herramientas"
    pruebas = {"herramientas": probar_herramientas, "interfaz": probar_interfaz, "agente": probar_agente}
    sys.exit(0 if pruebas[modo]() else 1)
