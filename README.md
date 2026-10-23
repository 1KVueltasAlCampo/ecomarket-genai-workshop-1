# EcoMarket - Talleres de Inteligencia Artificial Generativa

Juan David Cruz Garcia - A00368421 · Trabajo individual
Maestría en Inteligencia Artificial Aplicada · Inteligencia Artificial Generativa

Este repositorio desarrolla un caso de estudio sobre la mejora de la atención al cliente de EcoMarket, una tienda en línea (ficticia) de productos sostenibles. El Taller 1 explora un modelo de lenguaje con ingeniería de prompts, el Taller 2 le incorpora un sistema RAG para que responda con la información de la empresa y el Proyecto Final lo convierte en un agente que puede actuar (verificar una devolución y generar su etiqueta, con aprobación del cliente).

## Estructura del repositorio

```
.
├── README.md
├── taller-1/                       Taller 1: selección de modelo, riesgos éticos y prompts
│   ├── fase1_seleccion_arquitectura.md
│   ├── fase2_analisis_critico.md
│   └── fase3_prompts.ipynb
└── taller-2/                       Taller 2: sistema RAG
    ├── fase1_seleccion_componentes.md       Fase 1 (texto): embeddings y base vectorial
    ├── fase2_base_conocimiento.md           Fase 2 (texto): documentos, chunking e indexación
    ├── fase3_integracion_limitaciones.md    Fase 3 (texto): integración, resultados y limitaciones
    ├── taller2_rag_evidencia.ipynb          Notebook con todas las pruebas y experimentos
    │
    ├── rag.py                      Asistente RAG (el programa que se ejecuta)
    ├── ingesta.py                  Construye el índice vectorial
    ├── cargadores.py               Lee cada formato de documento y lo divide en fragmentos
    ├── embeddings.py               Modelos de embeddings candidatos
    ├── pedidos.py                  Consulta exacta de pedidos por número
    ├── rag_ejemplo.py              Script de ejemplo del curso (referencia, no se usa)
    ├── requirements.txt
    ├── .env.example                Plantilla del archivo .env
    │
    ├── base_conocimiento/          Documentos de EcoMarket (ver su README)
    │   ├── publico/                PDF, CSV, JSON, Markdown, DOCX
    │   └── interno/                Guía interna de atención (no debe llegar al cliente)
    ├── evaluacion/
    │   ├── preguntas_evaluacion.json    Conjunto de 33 preguntas con respuesta esperada
    │   └── resultados/                  Resultados guardados de los experimentos
    │       ├── embeddings.json
    │       ├── chunking.json
    │       └── llm.json
    └── utilidades/                 Scripts que generan los documentos y ejecutan los experimentos
        ├── generar_documentos.py
        ├── experimentos_retrieval.py
        └── experimentos_llm.py
```

El Taller 1 permanece intacto en su carpeta. El Taller 2 se construye sobre su caso y reutiliza sus datos, es decir, los 10 pedidos de prueba y el modelo de lenguaje.

Junto a esas dos carpetas se encuentra `proyecto-final/`, que contiene el agente de devoluciones, su interfaz en Streamlit, las pruebas y los cuatro documentos de las fases del Proyecto Final (diseño, implementación, análisis crítico y despliegue). Copia sin cambios los módulos de ingesta del Taller 2 y le agrega el agente; su instalación y uso se explican en `proyecto-final/README.md`.

## Pruebas, experimentos y resultados

Las respuestas escritas a las tres fases del Taller 2 están en `taller-2/fase1_seleccion_componentes.md`, `fase2_base_conocimiento.md` y `fase3_integracion_limitaciones.md`. Las pruebas y los experimentos que las sustentan se realizan en el notebook `taller-2/taller2_rag_evidencia.ipynb`, que importa el código del directorio y presenta las tablas y gráficos detrás de cada decisión: la base de conocimiento, el índice vectorial, la comparación de bases vectoriales (Chroma, FAISS, Pinecone y Weaviate), la de modelos de embeddings, la de estrategias de chunking, el asistente completo, el experimento con el modelo de lenguaje y la prueba del filtro por audiencia.

Los experimentos más lentos guardan sus números en la carpeta `taller-2/evaluacion/resultados/`, desde donde el notebook los carga; al establecer `RECALCULAR = True` se repiten desde cero. Esa carpeta contiene `embeddings.json` y `chunking.json`, con las mediciones de recuperación, y `llm.json`, con cada respuesta del asistente, su calificación y el motivo de esta.

## Funcionamiento del código

El sistema responde una pregunta en tres etapas: se construye un contexto, se arma el prompt y se llama al modelo de lenguaje. Previamente se requiere construir el índice vectorial, lo cual se realiza una sola vez con `ingesta.py`.

La construcción del índice sigue estos pasos:

1. `cargadores.py` lee cada documento con el lector de su formato y lo divide en fragmentos según su estructura: el PDF por sección numerada, el catálogo por producto, el FAQ por pregunta, el Markdown por encabezado, el Word por título y la guía interna por sección. A cada fragmento se le antepone el documento y la sección de origen, y se guardan como metadatos el documento, el formato, la sección y la audiencia (`publico` o `interno`, según la carpeta).
2. `embeddings.py` carga el modelo de embeddings (BGE-M3 por defecto) y convierte cada fragmento en un vector de 1024 valores.
3. `ingesta.py` guarda los vectores, con su texto y metadatos, en una colección de Chroma ubicada en `taller-2/chroma_db/`. Esa carpeta no se incluye en el repositorio, ya que se reconstruye con la ingesta en alrededor de un minuto en CPU.

La respuesta a una pregunta la realiza la clase `AsistenteRAG` de `rag.py`, mediante los siguientes pasos:

1. Se recupera de Chroma los 5 fragmentos más cercanos a la pregunta, aplicando el filtro `audiencia = publico` para que el documento interno nunca llegue al contexto.
2. Si el mensaje menciona un número de pedido, como `ORD-002`, se consulta ese pedido en `pedidos.py`. Se trata de una búsqueda exacta, no semántica, que no incluye el nombre del cliente.
3. Se arma el contexto con los datos del pedido y los fragmentos recuperados, cada uno marcado con su documento.
4. Se invoca al modelo de lenguaje (`gpt-oss-120b` en Groq) mediante una cadena de LangChain, `plantilla | llm`, donde la plantilla combina el prompt del sistema, el contexto y la pregunta. El prompt del sistema se elige entre `sin_rag`, `v0` y `v1`.
5. Se devuelve la respuesta junto con los fragmentos utilizados, los tokens consumidos y el tiempo de la llamada.

El prompt `v1`, que emplea el sistema final, es un prompt especializado: define el rol, los pasos de trabajo, un procedimiento por tipo de caso (pedido, devolución, envíos y costos, producto, sin información y ajeno a EcoMarket), las restricciones y cuatro ejemplos. El prompt `v0` consta de dos líneas y `sin_rag` corresponde al rol del Taller 1 sin contexto; ambos existen para medir la contribución de cada componente.

Los scripts de `utilidades/` cumplen funciones de apoyo. `experimentos_retrieval.py` mide la calidad de la búsqueda, sin modelo de lenguaje, con 23 preguntas que tienen una lista de textos necesarios para responder, y contiene dos experimentos: `embeddings` (cuatro modelos) y `chunking` (cuatro estrategias). `experimentos_llm.py` compara tres configuraciones del asistente (sin RAG, RAG con prompt mínimo y RAG con prompt especializado) y una prueba con el filtro desactivado sobre 9 preguntas, donde un segundo modelo, de otra familia, califica cada respuesta contra la respuesta esperada; el script es reanudable, de modo que lo ya calculado se omite. Por último, `generar_documentos.py` regenera el PDF, el Word y el CSV de la base de conocimiento, mientras que el Markdown, el JSON y el texto interno están redactados a mano.

## Ejecución

Se requiere Python 3.10 o superior. Los comandos se ejecutan desde `taller-2/`.

```bash
cd taller-2
python -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # y escribir la GROQ_API_KEY dentro de .env
```

Para evitar la descarga de la versión de PyTorch con soporte para GPU, que pesa varios GB, conviene instalar antes la versión para CPU con `pip install torch --index-url https://download.pytorch.org/whl/cpu`. Los embeddings se calculan en CPU y el modelo se descarga de Hugging Face la primera vez.

```bash
python ingesta.py --modelo bge-m3    # construye el índice (una sola vez)
python rag.py                        # asistente interactivo en la terminal
```

El notebook se abre con `jupyter` o con VS Code usando el entorno anterior y, si el índice no existe, lo construye. Para ejecutar `rag.py`, las celdas del asistente del notebook y `experimentos_llm.py` se necesita una llave de Groq (plan gratuito, <https://console.groq.com>) en el archivo `taller-2/.env`, que no se incluye en el repositorio. Dicho plan permite unas 1000 solicitudes diarias y 8000 tokens por minuto, por lo que los experimentos con el modelo de lenguaje espacian sus llamadas automáticamente.

Los experimentos pueden repetirse desde la terminal:

```bash
python utilidades/experimentos_retrieval.py embeddings
python utilidades/experimentos_retrieval.py chunking --modelos e5-small e5-base bge-m3
python utilidades/experimentos_llm.py              # requiere la llave de Groq; --rehacer para recalcular
```
