# Base de conocimiento de EcoMarket

EcoMarket es una empresa ficticia. Estos documentos emulan los que tendría una tienda real de productos sostenibles en Colombia. Todos los datos (precios, plazos, teléfonos, certificaciones) son inventados para el ejercicio.

| Archivo | Formato | Audiencia | Qué contiene | Estructura |
|---|---|---|---|---|
| `publico/politica_devoluciones.pdf` | PDF | Público | Plazos, categorías sin devolución, daños, reembolsos | Texto con secciones numeradas y 3 tablas |
| `publico/catalogo_productos.csv` | CSV | Público | 30 productos con precio, stock, disponibilidad, devolución y garantía | Una fila por producto |
| `publico/faq.json` | JSON | Público | 30 preguntas frecuentes con su respuesta | Un objeto por pregunta |
| `publico/politica_envios.md` | Markdown | Público | Zonas, tiempos, costos, estados del pedido, retrasos | Secciones con encabezados y una tabla |
| `publico/politica_garantias_sostenibilidad.docx` | Word | Público | Garantías por material, retracto, programa de recompra | Secciones con encabezados, una tabla y listas |
| `interno/guia_atencion_interna.txt` | Texto plano | Interno | Reglas de escalamiento, topes de aprobación, códigos de compensación | Secciones separadas por líneas de `=` |

La carpeta `interno/` simula un documento que una empresa real guardaría en su base de conocimiento pero que el bot de cara al cliente no debe usar ni citar.

Los archivos PDF, DOCX y CSV se generan con `utilidades/generar_documentos.py`. El Markdown, el JSON y el TXT están escritos a mano.

Las preguntas con las que se mide el sistema están en `../evaluacion/preguntas_evaluacion.json`.
