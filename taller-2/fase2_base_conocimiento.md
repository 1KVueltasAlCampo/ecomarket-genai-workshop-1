# Fase 2: Creación de la Base de Conocimiento de Documentos

## 1. Identificación de Documentos

Dado que EcoMarket es una empresa ficticia, se redactaron los documentos que tendría una tienda en línea de productos sostenibles, cada uno en el formato en que habitualmente se almacena ese tipo de información. Estos se encuentran en [base_conocimiento/](base_conocimiento/), y las mediciones que se citan están en las secciones 1, 2 y 5 del notebook [taller2_rag_evidencia.ipynb](taller2_rag_evidencia.ipynb). Se identificaron seis documentos.

| Documento | Formato | Contenido | Utilidad para el asistente |
|---|---|---|---|
| `politica_devoluciones.pdf` | PDF | Plazos, categorías sin devolución, productos dañados, reembolsos | Las devoluciones son el tema más repetitivo del servicio y tienen reglas con excepciones |
| `catalogo_productos.csv` | CSV | 30 productos con precio, disponibilidad, devolución permitida y garantía | Responde consultas de producto e indica si un producto concreto puede devolverse |
| `faq.json` | JSON | 30 preguntas frecuentes con su respuesta | Cubre consultas cortas y repetitivas (pagos, cupones, cuenta) |
| `politica_envios.md` | Markdown | Zonas, tiempos, costos, estados del pedido y retrasos | Los costos y tiempos dependen de la zona y exigen leer una tabla completa |
| `politica_garantias_sostenibilidad.docx` | Word | Garantías por material, derecho de retracto, programa de recompra | Complementa las devoluciones con las reglas de garantía |
| `guia_atencion_interna.txt` | Texto plano | Reglas de escalamiento, topes de aprobación, códigos de descuento | Es un documento interno que el asistente no debe utilizar con clientes |


Por otra parte, los pedidos se dejaron fuera del índice vectorial, porque un número de pedido se busca por igualdad y no por similitud: una búsqueda semántica podría devolver el pedido ORD-007 ante una consulta por el ORD-006, dado que sus textos son parecidos. En su lugar, los pedidos se consultan por número exacto (`pedidos.py`) y el resultado se agrega al contexto junto con los fragmentos recuperados.

La calidad de los documentos resulta determinante para el desempeño del sistema, y durante su construcción se identificaron tres aspectos. El primero es la coherencia: los plazos, precios y reglas deben coincidir entre documentos (los 30 días de devolución aparecen en el PDF, el FAQ y el documento Word), pues de contradecirse el asistente respondería de forma distinta según el fragmento recuperado. El segundo es la redundancia, ya que algunas preguntas están contestadas en más de un documento, como ocurre con el FAQ, que resume lo que establece el PDF; en las pruebas, el FAQ tiende a aparecer antes que la política porque sus textos cortos se parecen más a la pregunta. El tercero es que las tablas de un PDF se aplanan al extraer el texto, perdiéndose la relación entre cada celda y su fila: en el PDF construido esto no afectó los resultados porque el contenido de cada fila quedó contiguo, pero constituye un riesgo con documentos reales.

## 2. Segmentación (Chunking)

Se compararon cuatro estrategias de segmentación sobre los mismos documentos, con tres modelos de embeddings, midiendo la fracción de la evidencia necesaria que aparece entre los tres fragmentos más cercanos.

| Estrategia | Descripción | Fragmentos | BGE-M3 | E5-base | E5-small |
|---|---|---|---|---|---|
| A. Tamaño fijo | 200 palabras con 50 de solapamiento | 39 | 0.83 | 0.80 | 0.80 |
| B. Recursivo | 1000 caracteres con 200 de solapamiento (el de `rag_ejemplo.py`) | 52 | 0.85 | 0.85 | 0.83 |
| C. Por estructura | Cada formato según su organización | 95 | 0.89 | 0.94 | 0.89 |
| D. Por estructura con encabezado | Como C, anteponiendo "documento \| sección" a cada fragmento | 95 | 0.96 | 0.96 | 0.87 |

Se adopta la estrategia D. Dividir según la estructura del documento recupera más información que ignorarla con los tres modelos, lo cual es coherente con el caso: una ventana de tamaño fijo puede cortar una respuesta del FAQ por la mitad o separar una fila de una tabla de sus encabezados, mientras que al dividir por pregunta, producto o sección cada fragmento conserva su sentido completo. En concreto, el PDF se divide por secciones numeradas; el catálogo, en un fragmento por producto redactado como frase; el FAQ, en un fragmento por pregunta con su respuesta; el documento Markdown, por encabezados, de modo que la tabla de zonas permanece íntegra; el documento Word, por títulos, convirtiendo cada fila de tabla en una línea con sus encabezados; y la guía interna, por secciones delimitadas con líneas de signos igual. Las secciones de más de 1200 caracteres se subdividen con un splitter recursivo (1000 caracteres, solapamiento de 150), lo que da como resultado 95 fragmentos de entre 104 y 1154 caracteres.

Adicionalmente, a cada fragmento se le antepone el documento y la sección de origen (encabezado contextual), porque un texto como "5 a 7 días hábiles" no indica por sí solo a qué se refiere. El efecto es pequeño y mixto: con k=3 mejora la evidencia en BGE-M3 y E5-base, pero empeora en E5-small, y con E5-base reduce el desempeño en la primera posición. Dado que se trata de 23 preguntas y las diferencias son de una o dos, se interpreta como un indicio y no como una conclusión.

## 3. Indexación

El proceso de indexación se compone de los siguientes pasos:

1. Se carga cada documento con el lector correspondiente a su formato (`cargadores.py`).
2. Se divide en fragmentos según su estructura, como se describió en la sección anterior.
3. Se asocian a cada fragmento sus metadatos: documento, formato, sección y audiencia (`publico` o `interno`, según la carpeta de origen).
4. Se convierte cada fragmento en un vector de 1024 valores con BGE-M3, normalizado, de modo que la similitud coseno equivalga al producto punto (`embeddings.py`).
5. Se almacenan los vectores, junto con el texto y los metadatos, en una colección de Chroma con métrica coseno, persistida en disco (`ingesta.py`).

Este proceso se ejecuta una sola vez y toma alrededor de un minuto en CPU para los 95 fragmentos. Posteriormente, para responder una pregunta, esta se convierte en vector con el mismo modelo y se buscan los fragmentos más cercanos aplicando el filtro `audiencia = publico`; si los documentos cambian, se repite la ingesta. El filtro por audiencia forma parte del diseño: el documento interno está indexado, pero no puede llegar al contexto del modelo, y en la sección 8 del notebook se mide lo que ocurre sin él.
