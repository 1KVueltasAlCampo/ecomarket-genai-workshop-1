# Fase 2: Evaluación de Fortalezas, Limitaciones y Riesgos Éticos

## Fortalezas

Implementar el sistema RAG propuesto aporta un beneficio operativo inmediato y cuantificable en cuanto a que el tiempo de respuesta promedio para el 80% de consultas repetitivas pasa de veinticuatro horas a segundos. Esto se justifica en que, ya existen casos de despliegues reales de chatbots transaccionales en e-commerce, donde la disponibilidad continua y la estandarización de respuestas eliminan la variabilidad inherente a un equipo humano operando en turnos.

La arquitectura RAG añade una ventaja diferencial frente a un chatbot clásico basado en reglas puesto que al inyectar datos reales del pedido en el contexto del LLM, la respuesta no es una plantilla rígida sino una comunicación natural que adapta su tono y estructura al estado específico del caso. Por ejemplo, un pedido retrasado genera una disculpa empática con explicación, mientras que un pedido entregado genera una confirmación breve y positiva.

Adicionalmente, el sistema actúa como una primera línea de filtrado inteligente que alivia la carga cognitiva de los agentes humanos. En lugar de que un agente dedique tres minutos a buscar un pedido en el sistema, copiar los datos y redactar un mensaje estándar, ese trabajo mecánico se automatiza completamente, liberando al equipo humano para dedicar su atención a los casos del 20% complejo donde su criterio y empatía genuina son irremplazables.

## Limitaciones Técnicas

La principal limitación estructural radica en la dependencia absoluta de la calidad y disponibilidad de la fuente de datos. Por ejemplo, si la base de datos logística de EcoMarket tiene latencia en la actualización de estados (como el caso en el que el transportista actualizó el estado hace dos horas pero el sistema interno aún no refleja el cambio), el LLM generará una respuesta factualmente correcta según su contexto pero desactualizada respecto a la realidad del paquete.

La segunda limitación es la incapacidad del modelo para ejecutar acciones operativas, si bien, el LLM puede informar al cliente que su pedido está retrasado y ofrecer una disculpa, no puede autorizar un reembolso, reprogramar un envío ni contactar al transportista. Por el contrario, estas acciones requieren integración con sistemas transaccionales mediante function calling o herramientas externas, lo cual excede el alcance de un sistema puramente conversacional y entra en el terreno de agentes autónomos con permisos de escritura sobre la base de datos.

La tercera limitación es el riesgo residual de alucinación cuando el contexto es ambiguo o incompleto, en ese sentido, si un cliente pregunta por un pedido con un número que no existe en el sistema, dado a que las LLM tienden a querer responder, sin importar qué, se podría inventar un estado en lugar de admitir que no tiene información.

## Riesgos Éticos

Aclaracion: dado que EcoMarket no es una empresa real, considero que la mejor manera para explicar los riesgos y el funcionamiento es con ejemplos prácticos. 

### Alucinaciones con consecuencias legales

En febrero de 2024, el Tribunal de Resolución Civil de Columbia Británica falló contra Air Canada en el caso *Moffatt v. Air Canada* (2024 BCCRT 149), sucede que el chatbot de la aerolínea le indicó a un pasajero en duelo que podía comprar boletos a tarifa regular y solicitar retroactivamente el descuento por duelo dentro de los 90 días posteriores. Esa política no existía. Cuando el pasajero solicitó el reembolso, Air Canada argumentó que el chatbot era una "entidad legal separada" responsable de sus propias declaraciones. El tribunal rechazó ese argumento y condenó a la aerolínea a pagar la diferencia, sentando un precedente global: las empresas son legalmente responsables de las representaciones que hacen sus agentes de IA.

Para EcoMarket, esto significa que si el chatbot promete un plazo de entrega que no corresponde o aprueba una devolución de un producto no retornable, la empresa asume la responsabilidad legal.

### Sesgo demográfico en respuestas automatizadas

A mediados de 2019-2020, el chatbot de triaje médico de Babylon Health, desplegado a través del sistema nacional de salud del Reino Unido (NHS) bajo la iniciativa "GP at Hand", demostró disparidades sistemáticas de género: ante síntomas idénticos de infarto (dolor torácico irradiado a la mandíbula, náuseas) en un perfil de hombre fumador de 60 años, recomendaba llamar a emergencias; ante el mismo perfil clínico en mujer, clasificaba la condición como ataque de pánico y recomendaba autocuidado.

Para EcoMarket el riesgo es de menor gravedad clínica, pero no inexistente: un modelo podría ofrecer respuestas más detalladas, más pacientes o con mejores ofertas de compensación a ciertos perfiles de clientes sobre otros, replicando sesgos sociodemográficos presentes en los datos de entrenamiento del modelo base.

### Privacidad y manejo de datos sensibles (PII)

La inyección de contexto implica que información personal del cliente (nombre, dirección, historial de compras, número de pedido) transita hacia la API del proveedor del LLM.

Para EcoMarket, la mitigación requiere capas de anonimización o enmascaramiento de PII antes de enviar el contexto al LLM, o alternativamente el uso de modelos desplegados localmente (por ejemplo, a través de Ollama con modelos open-source) donde los datos nunca abandonan la infraestructura de la empresa.

### Impacto laboral

El caso de Dukaan, una plataforma de e-commerce india, ilustra el extremo destructivo de la automatización del soporte. En julio de 2023, su CEO anunció públicamente haber despedido al 90% de su equipo de soporte al cliente (aproximadamente 25 agentes) y reemplazarlos con un chatbot llamado "Lina", presumiendo una reducción del 85% en costos de soporte. El anuncio generó una condena internacional masiva por su tono deshumanizante.

Para EcoMarket, el objetivo debe ser explícitamente el empoderamiento: reasignar a los agentes de nivel básico hacia roles de resolución de conflictos complejos, retención de clientes insatisfechos y supervisión de calidad del sistema automatizado, donde su criterio humano aporta valor real.

### Vulnerabilidad a inyección de prompts

Existen hoy en día muchos "hacks" para manipular LLMs, incluyendo técnicas para forzar a un modelo a revelar contraseñas o instrucciones internas. Un caso emblemático ocurrió en diciembre de 2023, cuando usuarios manipularon el chatbot de Watsonville Chevrolet (impulsado por Fullpath AI con ChatGPT) mediante inyección de prompts, logrando que el bot aceptara vender un Chevrolet Tahoe 2024 por un dólar como "oferta legalmente vinculante".

Para EcoMarket, las restricciones del system prompt deben incluir defensas explícitas contra la manipulación del comportamiento del agente por parte de usuarios malintencionados.