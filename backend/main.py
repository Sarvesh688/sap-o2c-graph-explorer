"""
main.py — FastAPI application
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from query_engine import query as run_query
from graph_api import (
    get_overview_graph, get_entity_sample,
    get_node_neighbors, get_flow_subgraph
)

app = FastAPI(title="SAP O2C Graph API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = []

class NodeRequest(BaseModel):
    label: str
    id: str


VALID_LABELS = [
    "BusinessPartner", "SalesOrder", "SalesOrderItem",
    "Delivery", "DeliveryItem", "BillingDocument", "BillingItem",
    "Payment", "JournalEntry", "Product", "Plant", "Address"
]

EXAMPLE_QUERIES = [
    {"id": 1, "category": "Products",    "question": "Which products are associated with the highest number of billing documents?"},
    {"id": 2, "category": "Trace",       "question": "Trace the full flow of billing document 90504248"},
    {"id": 3, "category": "Exceptions",  "question": "Find sales orders that were delivered but never billed"},
    {"id": 4, "category": "Exceptions",  "question": "Show all cancelled billing documents"},
    {"id": 5, "category": "Customers",   "question": "Which customers have the highest total order value?"},
    {"id": 6, "category": "Payments",    "question": "Show billing documents that have not been paid yet"},
    {"id": 7, "category": "Exceptions",  "question": "Find orders with delivery status not completed"},
    {"id": 8, "category": "Plants",      "question": "Which plants shipped the most deliveries?"},
    {"id": 9, "category": "Orders",      "question": "Show me all sales orders created in April 2025"},
    {"id": 10,"category": "Products",    "question": "Which materials appear most frequently in sales order items?"},
]


@app.get("/")
def root():
    return {"status": "ok", "service": "SAP O2C Graph API"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/graph")
def graph_overview():
    try:
        return get_overview_graph()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/graph/entity/{label}")
def entity_sample(label: str, limit: int = 20):
    if label not in VALID_LABELS:
        raise HTTPException(400, f"Unknown label: {label}")
    try:
        return get_entity_sample(label, min(limit, 50))
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/graph/node")
def node_detail(req: NodeRequest):
    try:
        return get_node_neighbors(req.label, req.id)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/graph/flow/{sales_order_id}")
def flow_graph(sales_order_id: str):
    try:
        return get_flow_subgraph(sales_order_id)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/query")
def chat_query(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    if len(req.message) > 1000:
        raise HTTPException(400, "Message too long")
    try:
        return run_query(req.message, req.history)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/examples")
def examples():
    return EXAMPLE_QUERIES

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
