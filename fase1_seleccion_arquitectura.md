# Fase 1: Selección y Justificación del Modelo de IA

## 1. Selección Específica del Modelo y Enfoque Arquitectural

Para resolver la optimización del servicio al cliente en EcoMarket, se propone **GPT-4o-mini** como motor de inferencia principal (respaldado por la alternativa de código abierto **Llama 3.1 8B** para entornos de nube privada), implementado bajo una arquitectura desacoplada de **Generación Aumentada por Recuperación (RAG)** asistida por enrutamiento condicional.

Se descarta usar el reentrenamiento de modelos fundacionales y el ajuste fino (*fine-tuning*) continuo para la capa transaccional, dado que el catálogo de productos sostenibles y el estado logístico de los pedidos son datos inherentemente dinámicos y volátiles, es decir, cambian minuto a minuto en los sistemas de inventario y transporte. Realizar fine-tuning para incorporar estos datos congelaría el conocimiento en los pesos de la red neuronal al momento del entrenamiento, generando desfases inmediatos entre la realidad física del pedido y la respuesta del modelo.

Por el contrario, la arquitectura RAG resuelve este desafío transformando al modelo de lenguaje en un sintetizador contextual: no se memoriza el estado de los pedidos, sino que se recibe en tiempo real la información exacta consultada de la base de datos de EcoMarket, inyectada directamente en la ventana de contexto a través de delimitadores estructurados.

## 2. La Complejidad de la Tarea

EcoMarket revela una distribución clásica de Pareto; en otras palabras, el 80% de las consultas son transaccionales y repetitivas (rastreo de envíos, compatibilidad de productos y viabilidad de devoluciones), mientras que el 20% restante involucra quejas complejas, excepciones operativas y fricciones emocionales que exigen empatía genuina y criterio de negocio.

Bajo este escenario, desplegar un modelo de frontera masivo (*frontier model* de gran escala, como GPT-4 completo o Claude 3.5 Sonnet) para resolver el 80% repetitivo sería sobreingeniería y desperdicio de recursos. Lo que debería priorizarse exclusivamente es:

1. Comprensión estricta de instrucciones negativas y límites operacionales (*guardrails*).
2. Capacidad para extraer atributos de un payload de datos inyectado (JSON o texto plano).
3. Formulación lingüística en español formal, cálido y empático.

Un modelo compacto de última generación como GPT-4o-mini (o Llama 3.1 8B) cuenta con un balance óptimo de parámetros para seguir fielmente la taxonomía del system prompt, ejecutar razonamiento guiado (*chain of thought*) y rechazar alucinaciones cuando un dato no se encuentra en el contexto, sin la sobrecarga computacional de modelos de más de 100 mil millones de parámetros. Para el 20% complejo, el sistema no fuerza al modelo a improvisar soluciones, sino que implementa un protocolo de transferencia (*handoff*) hacia los agentes humanos de soporte, quienes reciben el resumen contextual estructurado de la conversación previa.

## 3. Justificación Económica y Latencia de Inferencia

En un entorno de e-commerce en rápido crecimiento que atiende miles de solicitudes diarias a través de chat web, redes sociales y correo, la economía de los tokens y la latencia son factores de viabilidad operativa inmediata; por ejemplo, en cuanto a costes de tokens, los modelos densos de frontera promedian tarifas de entre $2.50 y $15.00 USD por millón de tokens generados. En contraste, GPT-4o-mini y Llama 3.1 se sitúan en torno a $0.15 USD por millón de tokens de entrada y $0.60 USD por millón de salida (aproximadamente un 95% más económicos).

Por otro lado, en cuanto a latencia y *Time-to-First-Token* (TTFT), el tiempo de respuesta actual de EcoMarket es de 24 horas, por lo que considero que la automatización por chat debe tener una latencia inferior a los 800 milisegundos para mantener la retención del usuario. En ese sentido, los modelos compactos poseen un tiempo hasta el primer token significativamente menor y una velocidad de decodificación que triplica la de modelos pesados, permitiendo una experiencia de chat en tiempo real prácticamente instantánea.

## 4. Privacidad de Datos, PII y Seguridad

Es deseable que antes de que el payload del cliente sea inyectado en el prompt, el motor de recuperación intermedia filtre y anonimice atributos innecesarios para que la consulta no transfiera datos de facturación ni historiales bancarios, sino que únicamente traslade el identificador del pedido, el estado logístico, la fecha estimada y la política específica del producto.

En ese mismo sentido, al consumir GPT-4o-mini mediante contratos empresariales de API, se exige la política de *Zero Data Retention* (ZDR), la cual garantiza que los datos entrantes no se almacenan para reentrenar modelos públicos.

## 5. Escalabilidad, Integración y Mantenibilidad

Usando RAG, EcoMarket no tiene que rediseñar su base de datos relacional existente (PostgreSQL, MySQL o ERP logístico); solo deben exponerse funciones o APIs internas de lectura para que el middleware RAG obtenga el estado del pedido a partir de su ID.

Si EcoMarket cambia de proveedor logístico, modifica sus políticas de devolución o amplía su catálogo, las reglas se actualizan en las bases de datos deterministas sin tocar los pesos del modelo ni requerir nuevos ciclos de entrenamiento. Asimismo, el sistema adquiere elasticidad nativa para absorber picos estacionales de alta demanda (como Black Friday o temporadas ecológicas) delegando la concurrencia a la infraestructura *serverless* del proveedor de inferencia.