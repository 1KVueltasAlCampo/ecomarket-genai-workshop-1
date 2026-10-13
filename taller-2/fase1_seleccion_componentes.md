# Fase 1: Selección de Componentes Clave del Sistema RAG

## 1. Modelo de Embeddings

Para el sistema RAG de EcoMarket se selecciona **BGE-M3** (`BAAI/bge-m3`), un modelo de código abierto disponible en Hugging Face que se ejecuta de forma local, en CPU. 

Para llegar a esta decisión, se construyó una base de conocimiento de prueba (seis documentos que generan 95 fragmentos) y un conjunto de preguntas cuya respuesta requiere textos específicos, como un precio o un plazo, sobre el cual se midieron las alternativas. Dado que EcoMarket es una empresa ficticia y los documentos fueron redactados para este ejercicio, las cifras permiten comparar opciones entre sí, pero no anticipan el rendimiento que se obtendría con documentos reales. El detalle de las mediciones se encuentra en las secciones 3 y 4 del notebook [taller2_rag_evidencia.ipynb](taller2_rag_evidencia.ipynb).

Se compararon cuatro modelos multilingües de código abierto, todos con soporte para español. Con cada uno se indexaron los mismos fragmentos y se respondieron 23 preguntas, midiendo qué fracción de los textos necesarios aparece entre los 3 o 5 fragmentos más cercanos a la pregunta, sin intervención del modelo de lenguaje.

| Modelo | Parámetros | Máx. tokens | Evidencia@3 | Evidencia@5 | Preguntas completas con k=5 (de 23) | ms por consulta |
|---|---|---|---|---|---|---|
| paraphrase-multilingual-MiniLM | 118 M | 128 | 0.79 | 0.88 | 19 | 26 |
| multilingual-e5-small | 118 M | 512 | 0.87 | 0.96 | 22 | 25 |
| multilingual-e5-base | 278 M | 512 | 0.96 | 0.98 | 22 | 57 |
| BGE-M3 | 568 M | 512 | 0.96 | 1.00 | 23 | 155 |

Los resultados muestran que MiniLM obtiene el menor desempeño, en buena parte porque procesa únicamente 128 tokens por texto y varios fragmentos superan esa longitud. E5-small, por su parte, ofrece una relación calidad-velocidad favorable. E5-base y BGE-M3 se igualan con k=3, mientras que con k=5 solo BGE-M3 recupera toda la evidencia en las 23 preguntas. 

Dado que esta diferencia equivale a una sola pregunta, no resulta concluyente; el argumento principal a favor de BGE-M3 es su costo. Es el más lento, con 155 ms por consulta, pero este tiempo es reducido frente a la llamada al modelo de lenguaje, que toma cerca de un segundo, y los vectores de los documentos se calculan una única vez durante la indexación. En un equipo más limitado, E5-base sería la alternativa más razonable.

Respecto a la elección entre un modelo abierto y uno propietario, no se evaluó este último, ya que, utilizar un modelo propietario implicaría enviar a un tercero tanto los documentos como cada pregunta de los clientes, y entre los documentos existe uno de uso interno (una guía con topes de aprobación y códigos de descuento) que no debería salir de la empresa. Asi, con un modelo local esto no ocurre y el costo por consulta es nulo, aunque no es posible afirmar que un modelo propietario recupere peor, pues no fue medido. Finalmente, la importancia de este componente radica en que define qué se considera "cercano": si el fragmento que contiene la respuesta no es recuperado, el modelo de lenguaje no puede responder correctamente, por muy bien diseñado que esté el prompt, por lo que la calidad de la recuperación se mide de forma independiente.

## 2. Base de Datos Vectorial

Se selecciona **Chroma**, con el índice almacenado en disco. Para ello se probaron las dos alternativas que se ejecutan localmente, Chroma y FAISS, utilizando exactamente los mismos vectores, y se contrastaron con Pinecone y Weaviate unicamente a partir de su documentación, ya que estas últimas requieren, respectivamente, un servicio externo y un servidor propio. Los datos de planes y límites de estos servicios corresponden a lo vigente al 10 de octubre de 2026, fecha de realización del taller.

En las pruebas locales se observó, en primer lugar, que ambas bases recuperan lo mismo: en las 33 preguntas del conjunto devolvieron los mismos 5 fragmentos y el mismo fragmento en la primera posición, por lo que, a esta escala, la calidad de la búsqueda no las distingue. 

La diferencia relevante aparece en el filtrado por metadatos, necesario para que el documento interno nunca llegue al contexto del modelo. Chroma filtra antes de buscar y devolvió siempre los 5 fragmentos solicitados; FAISS, a través de LangChain, obtiene primero `fetch_k` candidatos y filtra después, de manera que con `fetch_k=5` devolvió 0, 4, 1 y 3 fragmentos en las cuatro preguntas confidenciales, pues los mejores candidatos pertenecían al documento interno y fueron descartados. Con `fetch_k=20` el resultado es correcto, pero obliga a fijar ese valor de forma arbitraria.

 En cuanto a la velocidad, FAISS busca en 0.2 ms y Chroma entre 8 y 12 ms; sin embargo, calcular el embedding de la pregunta toma cerca de 140 ms y la llamada al modelo de lenguaje cerca de un segundo, por lo que esta diferencia no resulta determinante.

Según su documentación, Pinecone ofrece un plan gratuito con 2 GB de almacenamiento, 5 índices y cuotas mensuales de lectura y escritura, restringido a la región AWS us-east-1, y aplica los filtros por metadatos durante la búsqueda. Weaviate, por su parte, es de código abierto (licencia BSD-3), puede autoalojarse con Docker o Kubernetes, cuenta con un plan gratuito en su nube de 100.000 objetos y filtra antes de buscar. Ambas resuelven el requisito del filtro; su desventaja para este caso es la complejidad, pues con Pinecone los documentos residen en la nube del proveedor y con Weaviate se requiere operar un servidor, para un índice de apenas 95 fragmentos.

En cuanto a la escalabilidad, no se midió el comportamiento de Chroma con volúmenes mayores. A 95 fragmentos una búsqueda toma entre 8 y 12 ms, pero con un catálogo considerablemente más grande y miles de consultas diarias un despliegue de Chroma en un solo equipo podría resultar insuficiente, caso en el cual se migraría a Weaviate autoalojado o a Pinecone. Este cambio afectaría principalmente a `ingesta.py` y al formato del filtro en `rag.py`, dado que el resto del código utiliza la interfaz de LangChain. 

En síntesis, Chroma reúne lo que EcoMarket requiere en este momento: almacena el índice en disco, filtra por metadatos antes de buscar, no envía datos a terceros, no tiene costo y se instala con una sola línea.
