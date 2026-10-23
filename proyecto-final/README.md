# Proyecto Final: agente de devoluciones para EcoMarket

Extiende el asistente RAG del Taller 2 con un agente que puede actuar: consulta pedidos y productos, verifica si una devolución es elegible y genera la etiqueta de devolución, pero solo después de que el cliente la apruebe. La interfaz es una aplicación de Streamlit con la mascota Ardi.

## Estructura

```
proyecto-final/
├── fase1_diseno_arquitectura.md     Fase 1: diseño (con los diagramas de diagramas/)
├── fase2_implementacion.md          Fase 2: qué se implementó y cómo se relaciona con el Taller 2
├── fase3_analisis_critico.md        Fase 3: seguridad, ética, observabilidad y mejoras
├── fase4_despliegue.md              Fase 4: interfaz y verificación de punta a punta
│
├── app.py                           Interfaz (Streamlit): el flujo y el estado de la conversación
├── interfaz.py                      Presentación: tema, tarjetas, bitácora
├── agente.py                        Agente: planificador, validador, ejecutor, aprobación y respuesta
├── herramientas.py                  Las seis herramientas y el registro de acciones
├── pedidos.py                       Pedidos de prueba (adaptado del Taller 2)
├── pruebas.py                       Pruebas: herramientas, interfaz y agente
│
├── cargadores.py, embeddings.py,    Copiados sin cambios del Taller 2
│   ingesta.py, base_conocimiento/
├── assets/                          Mascota Ardi (SVG)
├── .streamlit/config.toml           Tema de la aplicación
├── evaluacion/                      Contrato de pruebas (casos_prueba.json) y resultados guardados
├── experimentos/                    Comparación de planificadores y pruebas de viabilidad de la Fase 1
└── requirements.txt, .env.example
```

## Instalación

Requiere Python 3.10 o superior y una llave gratuita de [Groq](https://console.groq.com).

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu    # evita la versión con GPU, que pesa varios GB
pip install -r requirements.txt
cp .env.example .env               # y escribir la GROQ_API_KEY en .env
```

## Uso

```bash
streamlit run app.py
```

La primera vez, la aplicación construye el índice vectorial con los documentos de `base_conocimiento/` y descarga el modelo de embeddings BGE-M3 (cerca de 2 GB); tarda unos minutos y no se repite. Para probar sin la interfaz, `python agente.py` abre un chat en la terminal.

En la barra lateral, «Pedidos de prueba» indica qué número escribir para cada situación (devolución elegible, fuera de plazo, producto sin devolución, falla del servicio de etiquetas, entre otras). Cada pedido admite una sola etiqueta; «Restablecer etiquetas» permite repetir la demostración.

## Pruebas

```bash
python pruebas.py herramientas   # 66 pruebas deterministas, sin LLM
python pruebas.py interfaz       # la aplicación completa con modelos simulados, sin LLM
python pruebas.py agente         # el contrato de evaluacion/casos_prueba.json con el modelo real
```

Las dos primeras no consumen cupo del proveedor. La tercera sí: el plan gratuito de Groq permite 8.000 tokens por minuto y 200.000 por día para cada modelo, y una evaluación completa consume una parte considerable. Sus resultados se guardan en `evaluacion/resultados/agente.json` y se reutilizan; para repetirla desde cero hay que borrar ese archivo.

## Registro de acciones

Cada mensaje, plan, llamada a herramienta, aprobación, respuesta y fallo queda en `registro_acciones.jsonl` (una línea JSON por evento; no se versiona). La bitácora de la interfaz lee ese archivo.
