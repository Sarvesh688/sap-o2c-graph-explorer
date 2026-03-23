"""
graph_api.py — Neo4j data → JSON for React Flow
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

NODE_COLORS = {
    "SalesOrder":       "#7F77DD",
    "SalesOrderItem":   "#AFA9EC",
    "Delivery":         "#1D9E75",
    "DeliveryItem":     "#5DCAA5",
    "BillingDocument":  "#D85A30",
    "BillingItem":      "#F0997B",
    "Payment":          "#EF9F27",
    "JournalEntry":     "#639922",
    "BusinessPartner":  "#378ADD",
    "Address":          "#85B7EB",
    "Product":          "#E24B4A",
    "Plant":            "#888780",
}

POSITIONS = {
    "BusinessPartner":  (80,  300),
    "Address":          (80,  480),
    "SalesOrder":       (320, 180),
    "SalesOrderItem":   (320, 380),
    "Delivery":         (560, 180),
    "DeliveryItem":     (560, 380),
    "BillingDocument":  (800, 180),
    "BillingItem":      (800, 380),
    "Payment":          (1040, 180),
    "JournalEntry":     (1040, 380),
    "Product":          (320, 560),
    "Plant":            (560, 560),
}

SCHEMA_EDGES = [
    ("SalesOrder",      "BusinessPartner", "SOLD_TO"),
    ("SalesOrder",      "SalesOrderItem",  "HAS_ITEM"),
    ("SalesOrderItem",  "Product",         "REFERENCES_PRODUCT"),
    ("BusinessPartner", "Address",         "HAS_ADDRESS"),
    ("Delivery",        "DeliveryItem",    "HAS_ITEM"),
    ("DeliveryItem",    "SalesOrder",      "FULFILLS"),
    ("DeliveryItem",    "Plant",           "SHIPPED_FROM"),
    ("BillingDocument", "BillingItem",     "HAS_ITEM"),
    ("BillingDocument", "BusinessPartner", "BILLED_TO"),
    ("BillingItem",     "Delivery",        "BASED_ON_DELIVERY"),
    ("BillingItem",     "Product",         "FOR_PRODUCT"),
    ("Payment",         "BillingDocument", "CLEARS"),
    ("Payment",         "BusinessPartner", "PAID_BY"),
    ("JournalEntry",    "BillingDocument", "RECORDS"),
    ("Product",         "Plant",           "STORED_AT"),
]


def get_overview_graph() -> dict:
    with driver.session() as s:
        result = s.run("""
            MATCH (n)
            WITH labels(n)[0] AS label, count(n) AS cnt
            RETURN label, cnt ORDER BY cnt DESC
        """)
        counts = {r["label"]: r["cnt"] for r in result}

    nodes = []
    for label, cnt in counts.items():
        x, y = POSITIONS.get(label, (500, 300))
        nodes.append({
            "id": f"label_{label}",
            "type": "entityNode",
            "data": {
                "label": label,
                "count": cnt,
                "color": NODE_COLORS.get(label, "#888"),
                "nodeType": "summary"
            },
            "position": {"x": x, "y": y}
        })

    node_ids = {n["id"] for n in nodes}
    edges = []
    for src, tgt, rel in SCHEMA_EDGES:
        if f"label_{src}" in node_ids and f"label_{tgt}" in node_ids:
            edges.append({
                "id": f"e_{src}_{tgt}",
                "source": f"label_{src}",
                "target": f"label_{tgt}",
                "label": rel,
                "animated": False,
                "style": {"stroke": "#94928a", "strokeWidth": 1.5}
            })

    return {"nodes": nodes, "edges": edges}


def get_entity_sample(label: str, limit: int = 20) -> list:
    with driver.session() as s:
        result = s.run(f"MATCH (n:{label}) RETURN n LIMIT $limit", limit=limit)
        return [
            {
                "id": r["n"]._properties.get("id", ""),
                "label": label,
                "properties": dict(r["n"]._properties),
                "color": NODE_COLORS.get(label, "#888")
            }
            for r in result
        ]


def get_node_neighbors(label: str, node_id: str) -> dict:
    with driver.session() as s:
        result = s.run(f"""
            MATCH (n:{label} {{id: $id}})
            OPTIONAL MATCH (n)-[r]->(nb)
            RETURN n, type(r) AS rel, nb
            LIMIT 50
        """, id=node_id)

        main_node = None
        neighbors = []
        edges = []

        for record in result:
            n = record["n"]
            if main_node is None:
                lbl = list(n.labels)[0] if n.labels else label
                main_node = {
                    "id": node_id, "label": lbl,
                    "properties": dict(n._properties),
                    "color": NODE_COLORS.get(lbl, "#888")
                }
            nb = record.get("nb")
            rel = record.get("rel")
            if nb and rel:
                nb_label = list(nb.labels)[0] if nb.labels else "Unknown"
                nb_id = str(nb._properties.get("id", id(nb)))
                if not any(x["id"] == nb_id for x in neighbors):
                    neighbors.append({
                        "id": nb_id, "label": nb_label,
                        "properties": dict(nb._properties),
                        "color": NODE_COLORS.get(nb_label, "#888")
                    })
                edges.append({"source": node_id, "target": nb_id, "relationship": rel})

        return {"node": main_node, "neighbors": neighbors, "edges": edges}


def get_flow_subgraph(sales_order_id: str) -> dict:
    with driver.session() as s:
        result = s.run("""
            MATCH (so:SalesOrder {id: $soId})
            OPTIONAL MATCH (so)-[:SOLD_TO]->(bp:BusinessPartner)
            OPTIONAL MATCH (so)-[:HAS_ITEM]->(soi:SalesOrderItem)
            OPTIONAL MATCH (di:DeliveryItem)-[:FULFILLS]->(so)
            OPTIONAL MATCH (d:Delivery)-[:HAS_ITEM]->(di)
            OPTIONAL MATCH (bi:BillingItem)-[:BASED_ON_DELIVERY]->(d)
            OPTIONAL MATCH (b:BillingDocument)-[:HAS_ITEM]->(bi)
            OPTIONAL MATCH (pay:Payment)-[:CLEARS]->(b)
            OPTIONAL MATCH (je:JournalEntry)-[:RECORDS]->(b)
            RETURN so, bp, soi, di, d, bi, b, pay, je LIMIT 30
        """, soId=sales_order_id)

        nodes_map = {}
        edges = []

        def add(node, lbl):
            if node is None:
                return None
            props = dict(node._properties)
            nid = str(props.get("id", id(node)))
            if nid not in nodes_map:
                nodes_map[nid] = {
                    "id": nid, "label": lbl,
                    "properties": props,
                    "color": NODE_COLORS.get(lbl, "#888")
                }
            return nid

        def edge(s, t, r):
            if s and t:
                edges.append({"source": s, "target": t, "relationship": r})

        for rec in result:
            so  = add(rec["so"],  "SalesOrder")
            bp  = add(rec["bp"],  "BusinessPartner")
            soi = add(rec["soi"], "SalesOrderItem")
            di  = add(rec["di"],  "DeliveryItem")
            d   = add(rec["d"],   "Delivery")
            bi  = add(rec["bi"],  "BillingItem")
            b   = add(rec["b"],   "BillingDocument")
            pay = add(rec["pay"], "Payment")
            je  = add(rec["je"],  "JournalEntry")

            edge(so, bp,  "SOLD_TO")
            edge(so, soi, "HAS_ITEM")
            edge(d,  di,  "HAS_ITEM")
            edge(di, so,  "FULFILLS")
            edge(b,  bi,  "HAS_ITEM")
            edge(bi, d,   "BASED_ON_DELIVERY")
            edge(pay, b,  "CLEARS")
            edge(je,  b,  "RECORDS")

        return {"nodes": list(nodes_map.values()), "edges": edges}
