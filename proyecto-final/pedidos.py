# Pedidos de prueba (simulados). Parte de pedidos.py del Taller 2, con tres cambios:
#   - Cada pedido lleva el sku del producto, para cruzarlo con el catálogo.
#   - Las fechas se expresan como desfase relativo a hoy (días desde la entrega o días para
#     la entrega), de modo que cada caso de prueba se comporta igual en cualquier fecha.
#   - Se agregan cuatro pedidos (ORD-011 a ORD-014) para probar las ramas de la devolución.
# Se mantiene la decisión del Taller 2: no se guarda el nombre del cliente, porque el agente
# no lo necesita y no conviene enviar datos personales al LLM.
PEDIDOS = {
    "ORD-001": {"producto": "Termo de Acero Inoxidable 500 ml", "sku": "PROD-002", "estado": "En tránsito", "llega_en_dias": 2, "retrasado": False},
    "ORD-002": {"producto": "Bolsa Reutilizable Pack x3", "sku": "PROD-004", "estado": "Retrasado en aduana", "llega_en_dias": 7, "retrasado": True},
    "ORD-003": {"producto": "Kit de Pajillas de Bambú x6", "sku": "PROD-005", "estado": "Entregado", "entregado_hace_dias": 18, "retrasado": False},
    "ORD-004": {"producto": "Jabón Artesanal Orgánico 100 g", "sku": "PROD-003", "estado": "Procesando", "llega_en_dias": 4, "retrasado": False},
    "ORD-005": {"producto": "Cepillo de Dientes de Bambú", "sku": "PROD-001", "estado": "Cancelado por el cliente", "retrasado": False},
    "ORD-006": {"producto": "Botella Plegable de Silicona 600 ml", "sku": "PROD-006", "estado": "En tránsito", "llega_en_dias": 1, "retrasado": False},
    "ORD-007": {"producto": "Set de Cubiertos Portátiles", "sku": "PROD-007", "estado": "Extraviado por transportista", "retrasado": True},
    "ORD-008": {"producto": "Champú Sólido Natural 80 g", "sku": "PROD-008", "estado": "Entregado", "entregado_hace_dias": 20, "retrasado": False},
    "ORD-009": {"producto": "Envoltura de Cera de Abeja Set x3", "sku": "PROD-009", "estado": "Devuelto al remitente", "retrasado": True},
    "ORD-010": {"producto": "Esponja Vegetal de Luffa x2", "sku": "PROD-010", "estado": "En tránsito", "llega_en_dias": 3, "retrasado": False},
    # Nuevos, para probar la elegibilidad de devolución
    "ORD-011": {"producto": "Termo de Acero Inoxidable 500 ml", "sku": "PROD-002", "estado": "Entregado", "entregado_hace_dias": 46, "retrasado": False},
    "ORD-012": {"producto": "Cepillo de Dientes de Bambú", "sku": "PROD-001", "estado": "Entregado", "entregado_hace_dias": 3, "retrasado": False},
    "ORD-013": {"producto": "Granola Orgánica 350 g", "sku": "PROD-014", "estado": "Entregado", "entregado_hace_dias": 1, "retrasado": False},
    "ORD-014": {"producto": "Termo de Acero Inoxidable 500 ml", "sku": "PROD-002", "estado": "Entregado", "entregado_hace_dias": 5, "retrasado": False},
}
