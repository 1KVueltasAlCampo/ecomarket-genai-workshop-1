# Fase 2: Implementación del Agente

## 1. Qué se implementó

Se implementó el diseño plan-and-execute de la Fase 1 sobre LangChain y LangGraph. Las seis herramientas se definieron como funciones con argumentos tipados en `herramientas.py` (`buscar_en_documentos`, `consultar_pedido`, `consultar_producto`, `calcular`, `verificar_elegibilidad_producto` y `generar_etiqueta_devolucion`) y el agente se inicializa en `agente.py` como un grafo de cinco nodos: planificador (Qwen), validador del plan (reglas en código), ejecutor (gpt-oss-120b, un paso a la vez), aprobación del cliente mediante `interrupt()` y respuesta final. La etiqueta de devolución solo se genera si el cliente aprueba y si el código de verificación entregado por la herramienta de elegibilidad es válido, de modo que ni el modelo ni el texto del cliente pueden saltarse esa condición.

## 2. Relación con el Taller 2

El código del Taller 2 se conservó sin modificaciones en todo lo que no necesitaba cambiar; el resto se agregó a su alrededor.

| Componente | Tratamiento |
|---|---|
| `cargadores.py`, `embeddings.py`, `ingesta.py` y `base_conocimiento/` | Copia idéntica al Taller 2 (verificada archivo por archivo). |
| Índice de Chroma, BGE-M3, filtro de audiencia y k = 5 | Se reutilizan como la herramienta `buscar_en_documentos`. Una prueba de no regresión reproduce las métricas del Taller 2 (23 preguntas con la evidencia completa y evidencia@5 = 1,0). |
| `pedidos.py` | Se mantiene el diccionario de pedidos y la decisión de no almacenar nombres de clientes. Se agregan el `sku`, las fechas relativas a `hoy()` y cuatro pedidos (ORD-011 a ORD-014). Se elimina `contexto_pedido()`, que inyectaba el pedido en el prompt mediante una expresión regular, porque ahora el agente decide cuándo llamar a `consultar_pedido`. |
| Prompt v1 de `rag.py` | Sus reglas se trasladan al prompt de respuesta: responder solo con los datos obtenidos, no autorizar excepciones, ignorar cambios de rol, ofrecer un agente humano y cerrar con la línea de fuentes. `rag.py` no se copia, porque su recuperación pasa a ser una herramienta y su generación, el último nodo. |
| `herramientas.py`, `agente.py`, `pruebas.py` | Archivos nuevos. |

## 3. Manejo de respuestas

Las herramientas nunca lanzan excepciones: devuelven los datos o un código de error con un mensaje, y cualquier fallo inesperado se captura en `ejecutar()` y se convierte en `ERROR_EN_HERRAMIENTA`. El nodo final recibe un estado (`ok`, `no_elegible`, `pedido_inexistente`, `cancelado`, `error_servicio`, `error_herramienta`, `plan_invalido`, `faltan_datos` o `directo`) y los datos obtenidos, pero no los códigos internos, de modo que no pueden aparecer en la respuesta. En el caso exitoso la respuesta confirma la etiqueta, su vigencia, los pasos de entrega y el reembolso estimado; en los casos de error explica lo ocurrido con lenguaje sencillo, indica que no quedó nada registrado cuando corresponde y ofrece un agente humano. Dos salvaguardas en código completan el manejo: la línea de fuentes solo puede nombrar documentos realmente recuperados y los guiones y espacios no separables que el modelo a veces escribe se normalizan, para que la etiqueta mostrada coincida exactamente con la real. Si el propio modelo falla (por ejemplo, por el límite de uso), el cliente recibe un mensaje claro en lugar de una traza y, si la etiqueta ya se había generado, una plantilla fija con su número, vigencia y pasos. Cada plan, llamada a herramienta, aprobación, respuesta y fallo interno queda en `registro_acciones.jsonl`.

## 4. Verificación

Se superan las 57 pruebas deterministas (sin LLM), entre ellas la de no regresión frente al Taller 2 y las de los fallos simulados del modelo. En la evaluación completa del agente (13 casos con los críticos repetidos tres veces, un rechazo del cliente y un escenario de varios turnos) la selección de herramientas fue correcta en 13 de 13 casos, no se generó ninguna etiqueta indebida en las 12 ejecuciones críticas, ninguna respuesta mostró códigos técnicos, la aprobación se solicitó exactamente antes de generar la etiqueta en las 21 ejecuciones y la cancelación del cliente no generó etiqueta. La lectura de las respuestas, y no solo las comprobaciones automáticas, llevó a tres correcciones: el nombre ambiguo del descuento por envío, que producía un reembolso erróneo; los códigos internos que a veces llegaban al cliente; y los guiones no separables en los identificadores. Queda un defecto de contenido: ante la pregunta por el tiempo del reembolso, el modelo suma los plazos de inspección y de reembolso y entrega un total ("8 a 10 días hábiles") que los documentos no contienen; ocurrió en 4 de 5 repeticiones y el ejemplo agregado después al prompt solo se ha probado en una ejecución.

El plan gratuito de Groq limita cada modelo a 8.000 tokens por minuto y 200.000 por día. Una consulta con búsqueda en documentos consume cerca de 4.500 tokens del modelo ejecutor y tarda entre 3 y 18 segundos; si se encadenan varias en menos de un minuto, el limitador propio espera a que se libere la ventana (hasta unos 60 segundos), que fue lo que alargó la evaluación. El cupo diario llegó a agotarse durante las pruebas, por lo que conviene espaciar las consultas en la demostración.

Las pruebas se ejecutan con `python pruebas.py herramientas` (deterministas, sin LLM) y `python pruebas.py agente` (13 casos y un escenario de varios turnos definidos en `evaluacion/casos_prueba.json` antes de implementar).
