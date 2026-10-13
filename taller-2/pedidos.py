# Consulta exacta de pedidos por número. Es la segunda fuente de contexto del bot,
# junto con la búsqueda semántica en los documentos.
#
# Los pedidos NO van al índice vectorial: un número de pedido no se busca "por
# parecido", se busca por igualdad. Un RAG semántico podría devolver el pedido
# ORD-007 cuando alguien pregunta por el ORD-006, porque sus textos se parecen.
#
# Son los mismos 10 pedidos del Taller 1, con las fechas llevadas a octubre de 2026.
# Se omite el nombre del cliente: el bot no lo necesita para informar el estado, y no
# conviene enviar datos personales al proveedor del LLM (ver Taller 1, Fase 1, sección 4).
import re

PEDIDOS = {
    "ORD-001": {"producto": "Termo de Acero Inoxidable 500 ml", "estado": "En tránsito", "fecha_estimada": "2026-10-14", "retrasado": False},
    "ORD-002": {"producto": "Bolsa Reutilizable Pack x3", "estado": "Retrasado en aduana", "fecha_estimada": "2026-10-28", "retrasado": True},
    "ORD-003": {"producto": "Kit de Pajillas de Bambú x6", "estado": "Entregado", "fecha_estimada": "2026-10-03", "retrasado": False},
    "ORD-004": {"producto": "Jabón Artesanal Orgánico 100 g", "estado": "Procesando", "fecha_estimada": "2026-10-16", "retrasado": False},
    "ORD-005": {"producto": "Cepillo de Dientes de Bambú", "estado": "Cancelado por el cliente", "fecha_estimada": "N/A", "retrasado": False},
    "ORD-006": {"producto": "Botella Plegable de Silicona 600 ml", "estado": "En tránsito", "fecha_estimada": "2026-10-13", "retrasado": False},
    "ORD-007": {"producto": "Set de Cubiertos Portátiles", "estado": "Extraviado por transportista", "fecha_estimada": "N/A", "retrasado": True},
    "ORD-008": {"producto": "Champú Sólido Natural 80 g", "estado": "Entregado", "fecha_estimada": "2026-10-01", "retrasado": False},
    "ORD-009": {"producto": "Envoltura de Cera de Abeja Set x3", "estado": "Devuelto al remitente", "fecha_estimada": "N/A", "retrasado": True},
    "ORD-010": {"producto": "Esponja Vegetal de Luffa x2", "estado": "En tránsito", "fecha_estimada": "2026-10-15", "retrasado": False},
}


def contexto_pedido(mensaje: str) -> str:
    """Si el mensaje menciona números de pedido (ORD-123), devuelve sus datos como texto;
    si no menciona ninguno, devuelve una cadena vacía."""
    ids = list(dict.fromkeys(re.findall(r"ORD-\d{3}", mensaje.upper())))
    lineas = []
    for i in ids:
        p = PEDIDOS.get(i)
        if p is None:
            lineas.append(f"Pedido {i}: NO EXISTE en el sistema.")
        else:
            lineas.append(
                f"Pedido {i}: producto {p['producto']}; estado {p['estado']}; "
                f"fecha estimada de entrega {p['fecha_estimada']}; "
                f"presenta retraso: {'sí' if p['retrasado'] else 'no'}; "
                f"enlace de rastreo https://ecomarket.com/track/{i}")
    return "DATOS DEL PEDIDO (consulta exacta por número):\n" + "\n".join(lineas) if lineas else ""
