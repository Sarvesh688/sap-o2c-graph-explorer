# SAP O2C Graph Explorer

A context graph system with LLM-powered natural language query interface for SAP Order-to-Cash data.

**Live demo:** [your-app.vercel.app](https://your-app.vercel.app)  
**GitHub:** [github.com/your-username/sap-o2c-graph](https://github.com/your-username/sap-o2c-graph)

---

## What This Does

In real SAP environments, Order-to-Cash data is split across 19 separate tables — sales orders, deliveries, billing documents, payments, journal entries, customers, and products. There is no easy way to answer a question like *"was this order actually paid, and what happened along the way?"* without manually joining multiple files.

This system solves that by:
1. Loading all 19 datasets into a **Neo4j graph database** where every entity is a node and every business relationship is an edge
2. Exposing a **visual graph explorer** so users can browse entities and their connections
3. Providing a **natural language chat interface** where users ask questions in plain English — the system translates them into Cypher queries, executes them against real data, and returns grounded answers

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                 │
│   GraphView (React Flow)    │   ChatPanel (NL Query UI)   │
└──────────────┬──────────────────────────┬────────────────┘
               │ HTTP / REST              │ HTTP / REST
┌──────────────▼──────────────────────────▼────────────────┐
│                    Backend (FastAPI / Python)              │
│   graph_api.py               │   query_engine.py          │
│   (graph visualization)      │   (NL → Cypher → Format)   │
└──────────────┬───────────────────────┬────────────────────┘
               │ Neo4j Python Driver   │ Groq Python SDK
┌──────────────▼───────────┐  ┌────────▼───────────────────┐
│    Neo4j AuraDB           │  │    Groq API                │
│    (Graph Database)       │  │  llama-3.3-70b-versatile   │
└───────────────────────────┘  └────────────────────────────┘
```

**Request flow for a natural language query:**
1. User types question → React sends POST to `/api/query`
2. FastAPI calls Groq with question + full schema + guardrail instructions
3. Groq returns `{"cypher": "MATCH ...", "explanation": "..."}`
4. FastAPI executes Cypher on Neo4j, receives records
5. FastAPI calls Groq again to format raw records into English answer
6. React displays answer + Cypher + record count

---

## Technology Choices and Tradeoffs

### Neo4j — Graph Database

**Why Neo4j over PostgreSQL:**

The O2C dataset is fundamentally relational — a BillingDocument references a Delivery which fulfills a SalesOrder which belongs to a BusinessPartner. Storing this in PostgreSQL would require 4–6 JOINs for a single trace query.

Compare the same question in both:

**SQL (PostgreSQL) — "trace billing document 90504248":**
```sql
SELECT so.id, d.id, b.id, pay.id, je.id
FROM billing_document_headers b
LEFT JOIN billing_document_items bi ON bi.billing_document = b.id
LEFT JOIN outbound_delivery_headers d ON d.id = bi.reference_sd_document
LEFT JOIN outbound_delivery_items di ON di.delivery_document = d.id
LEFT JOIN sales_order_headers so ON so.id = di.reference_sd_document
LEFT JOIN payments_accounts_receivable pay ON pay.accounting_document = b.accounting_document
LEFT JOIN journal_entry_items_ar je ON je.reference_document = b.id
WHERE b.id = '90504248';
```

**Cypher (Neo4j) — same question:**
```cypher
MATCH (b:BillingDocument {id: "90504248"})
OPTIONAL MATCH (b)-[:HAS_ITEM]->(bi)-[:BASED_ON_DELIVERY]->(d)
OPTIONAL MATCH (d)-[:HAS_ITEM]->(di)-[:FULFILLS]->(so)
OPTIONAL MATCH (pay:Payment)-[:CLEARS]->(b)
OPTIONAL MATCH (je:JournalEntry)-[:RECORDS]->(b)
RETURN b, d, so, pay, je
```

The Cypher mirrors how a human would describe the question. More importantly, `NOT EXISTS {}` in Cypher makes incomplete-flow detection trivial — finding delivered-but-not-billed orders is a single pattern match rather than a complex outer join with NULL checks.

**Tradeoff acknowledged:** For this dataset size (~17,000 records), PostgreSQL would also work fine. The Neo4j choice is justified by query expressiveness and architectural fit, not raw performance.

---

### Groq — LLM API

Groq was chosen for inference speed — llama-3.3-70b-versatile runs in under 1 second, making the chat interface feel responsive. Google Gemini or OpenRouter would work as drop-in replacements. The free tier handles ~14,400 requests/day, sufficient for demo use.

---

### FastAPI — Backend Framework

Chosen for: async request handling, automatic OpenAPI docs at `/docs`, Pydantic request validation, and clean integration with both the Neo4j Python driver and Groq SDK.

---

### React Flow — Graph Visualization

Purpose-built for interactive node-edge graphs with built-in support for custom node types, zoom/pan/fit, minimap, and click handlers. Cytoscape.js was considered but React Flow has better React integration and the layout model suited the schema-overview use case better.

---

## LLM Prompting Strategy

### Two-call pipeline

Every query goes through two separate LLM calls:

**Call 1 — NL → Cypher (temperature: 0.1)**

The system prompt contains:
- Complete node schema (all 12 labels + their properties)
- All 15 relationship types with direction
- O2C business flow definitions
- Delivery status code mappings (A=Not started, B=Partial, C=Complete)
- 6 Cypher example patterns covering aggregation, trace, exception detection, filter, ranking
- Strict output format: `{"cypher": "...", "explanation": "..."}`
- Explicit guardrail instructions with rejection format: `{"error": "..."}`

Low temperature (0.1) ensures deterministic, valid Cypher output.

**Call 2 — Results → Natural language (temperature: 0.3)**

A separate formatter prompt receives the original question + raw records and produces a plain-English business answer that references specific IDs and amounts from the data.

**Why two calls instead of one:**

A single call asked to both generate Cypher AND explain results produces worse Cypher. The model splits attention between structural correctness and narrative quality, compromising both. Two focused calls — one structured, one conversational — consistently outperform a single combined call.

### The actual system prompt (Call 1)

```
You are a data assistant for an SAP Order-to-Cash (O2C) system.
You answer ONLY questions about the dataset described below.

=== DATABASE: Neo4j Graph ===

NODE LABELS AND PROPERTIES:
- BusinessPartner   {id, name, category, companyCode, salesOrganization, paymentTerms}
- Address           {id, city, country, region, postalCode, street}
- SalesOrder        {id, type, salesOrg, amount, currency, deliveryStatus, creationDate}
- SalesOrderItem    {id, material, quantity, unit, amount, plant, materialGroup}
- Delivery          {id, creationDate, shippingPoint, pickingStatus, goodsMovementStatus}
- DeliveryItem      {id, quantity, plant, storageLocation, referenceOrder}
- BillingDocument   {id, type, amount, currency, date, isCancelled, accountingDocument}
- BillingItem       {id, material, quantity, amount, referenceDelivery}
- Payment           {id, amount, currency, clearingDate, customer, accountingDocument}
- JournalEntry      {id, amount, glAccount, postingDate, documentType, companyCode}
- Product           {id, description, type, group, baseUnit}
- Plant             {id, name, salesOrganization, distributionChannel}

RELATIONSHIPS:
(SalesOrder)-[:SOLD_TO]->(BusinessPartner)
(SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)
(SalesOrderItem)-[:REFERENCES_PRODUCT]->(Product)
(Delivery)-[:HAS_ITEM]->(DeliveryItem)
(DeliveryItem)-[:FULFILLS]->(SalesOrder)
(DeliveryItem)-[:SHIPPED_FROM]->(Plant)
(BillingDocument)-[:HAS_ITEM]->(BillingItem)
(BillingDocument)-[:BILLED_TO]->(BusinessPartner)
(BillingItem)-[:BASED_ON_DELIVERY]->(Delivery)
(BillingItem)-[:FOR_PRODUCT]->(Product)
(Payment)-[:CLEARS]->(BillingDocument)
(Payment)-[:PAID_BY]->(BusinessPartner)
(JournalEntry)-[:RECORDS]->(BillingDocument)
(Product)-[:STORED_AT]->(Plant)

=== OUTPUT FORMAT ===
Return ONLY valid JSON. No markdown, no explanation outside JSON.
For valid O2C questions: {"cypher": "MATCH ...", "explanation": "..."}
For off-topic questions: {"error": "This system only answers questions about the SAP Order-to-Cash dataset."}

=== GUARDRAILS ===
REJECT and return error JSON for:
- General knowledge (history, science, geography, math)
- Creative writing, jokes, poems, stories
- Questions about other software, datasets, or companies
- Anything not answerable from the O2C graph above
```

---

## Guardrails

Guardrails are enforced at the prompt level. The same LLM that generates Cypher also rejects off-topic questions — no separate classifier is needed.

**How it works:**
1. User asks "Write me a poem about supply chains"
2. Groq sees the guardrail instructions in the system prompt
3. Groq returns `{"error": "This system only answers questions about the SAP Order-to-Cash dataset."}`
4. FastAPI detects the `error` key — no Cypher is generated, no database query runs
5. Frontend displays the rejection message

**Tested rejection cases:**

| Input | Response |
|---|---|
| "Write me a poem about supply chains" | Rejected — off-topic |
| "Who is the CEO of SAP?" | Rejected — general knowledge |
| "What is the capital of France?" | Rejected — general knowledge |
| "Explain blockchain" | Rejected — out of domain |
| "Delete all sales orders" | Rejected — write operation not permitted |
| "Which orders are unpaid?" | Accepted — valid O2C query |

**Why prompt-level guardrails instead of a keyword filter:**
Keyword filters would block legitimate questions containing words like "write" (e.g. "write a query for..."). The LLM-based approach understands intent, not just words. It correctly rejects "explain blockchain" while accepting "explain the O2C flow for order 740506."

---

## Graph Model

### Node types (12)

| Label | Key Properties | Source Files |
|---|---|---|
| BusinessPartner | id, name, category, companyCode | business_partners/, business_partner_addresses/ |
| Address | id, city, country, region, postalCode | business_partner_addresses/ |
| SalesOrder | id, amount, deliveryStatus, creationDate | sales_order_headers/ |
| SalesOrderItem | id, material, quantity, amount | sales_order_items/, sales_order_schedule_lines/ |
| Delivery | id, pickingStatus, shippingPoint | outbound_delivery_headers/ |
| DeliveryItem | id, quantity, plant, referenceOrder | outbound_delivery_items/ |
| BillingDocument | id, amount, isCancelled, accountingDocument | billing_document_headers/, billing_document_cancellations/ |
| BillingItem | id, material, quantity, amount | billing_document_items/ |
| Payment | id, amount, clearingDate | payments_accounts_receivable/ |
| JournalEntry | id, glAccount, postingDate | journal_entry_items_accounts_receivable/ |
| Product | id, description, group | products/, product_descriptions/ |
| Plant | id, name, salesOrganization | plants/ |

### Relationship types (15)

```
(SalesOrder)-[:SOLD_TO]->(BusinessPartner)
(SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)
(SalesOrderItem)-[:REFERENCES_PRODUCT]->(Product)
(BusinessPartner)-[:HAS_ADDRESS]->(Address)
(Delivery)-[:HAS_ITEM]->(DeliveryItem)
(DeliveryItem)-[:FULFILLS]->(SalesOrder)
(DeliveryItem)-[:SHIPPED_FROM]->(Plant)
(BillingDocument)-[:HAS_ITEM]->(BillingItem)
(BillingDocument)-[:BILLED_TO]->(BusinessPartner)
(BillingItem)-[:BASED_ON_DELIVERY]->(Delivery)
(BillingItem)-[:FOR_PRODUCT]->(Product)
(Payment)-[:CLEARS]->(BillingDocument)
(Payment)-[:PAID_BY]->(BusinessPartner)
(JournalEntry)-[:RECORDS]->(BillingDocument)
(Product)-[:STORED_AT]->(Plant)
```

### Why 12 nodes from 19 source files

Several source files describe the same business entity. For example:
- `products/`, `product_descriptions/`, `product_plants/`, `product_storage_locations/` — all merged into one `Product` node, with `STORED_AT` edges to `Plant`
- `billing_document_headers/` and `billing_document_cancellations/` — both become `BillingDocument` nodes, with `isCancelled=true` set for cancellations
- `customer_company_assignments/` and `customer_sales_area_assignments/` — both enrich the `BusinessPartner` node properties

This consolidation keeps the graph model clean and queries simple.

---

## How I Used AI Tools

This project was built using Claude (claude.ai) and Claude Code as the primary AI coding assistants.

**AI was used for:**
- Designing the graph schema (iterating on which of the 19 files map to which node type)
- Writing and refining the system prompt — multiple iterations to improve Cypher quality and guardrail reliability
- Debugging Neo4j ingestion — particularly the OPTIONAL MATCH + FOREACH pattern for conditional relationship creation
- Writing the FastAPI route handlers and Pydantic models
- Building the React Flow custom node component and the chat panel state management

**What I verified manually:**
- All Cypher queries were tested in Neo4j Browser before being added to the system prompt as examples
- Guardrail rejections were tested with ~10 different off-topic inputs
- The three required example queries were confirmed to return correct, data-backed answers

AI coding session logs are included in the `/ai-logs/` directory of this repository (as required by the submission guidelines).

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Free Neo4j AuraDB account — [neo4j.com/cloud/aura-free](https://neo4j.com/cloud/aura-free)
- Free Groq API key — [console.groq.com](https://console.groq.com)

### 1. Place your data

Unzip the dataset into the `data/` directory. Each subfolder contains one or more `part-*.jsonl` files:

```
data/
  sales_order_headers/
  sales_order_items/
  sales_order_schedule_lines/
  outbound_delivery_headers/
  outbound_delivery_items/
  billing_document_headers/
  billing_document_items/
  billing_document_cancellations/
  payments_accounts_receivable/
  journal_entry_items_accounts_receivable/
  business_partners/
  business_partner_addresses/
  customer_company_assignments/
  customer_sales_area_assignments/
  products/
  product_descriptions/
  product_plants/
  product_storage_locations/
  plants/
```

### 2. Backend setup

```bash
cd backend
cp .env.example .env
# Fill in: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, GROQ_API_KEY

pip install -r requirements.txt

# Loads all 19 entity types into Neo4j — takes 1–2 minutes, ~17,000 total records
python ingest.py

# Verify ingestion worked (run in Neo4j Browser):
# MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC

# Run smoke tests before starting the server
python test_backend.py

python uvicorn main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
cp .env.example .env
# VITE_API_URL=http://localhost:8000

npm install
npm run dev   # opens at http://localhost:3000
```

---

## Example Queries

| Question | Query type | What it demonstrates |
|---|---|---|
| Which products are associated with the highest number of billing documents? | Aggregation | Cross-entity counting |
| Trace the full flow of billing document 90504248 | Flow trace | Multi-hop graph traversal |
| Find sales orders that were delivered but never billed | Exception detection | NOT EXISTS pattern |
| Show all cancelled billing documents | Filter | Property-based filter |
| Which customers have the highest total order value? | Ranking | Aggregation + sorting |
| Show billing documents that have not been paid yet | Exception detection | Missing relationship detection |
| Which plants shipped the most deliveries? | Aggregation | Relationship counting |

---

## Deployment

### Backend → Render.com (free tier)

1. Push to GitHub
2. New Web Service → connect repo → Root Directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `GROQ_API_KEY`

Note: Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

### Frontend → Vercel (free tier)

1. New project → connect repo → Root Directory: `frontend`
2. Add environment variable: `VITE_API_URL=https://your-render-app.onrender.com`
3. Deploy

---

## Limitations and Future Work

**Current limitations:**
- Render free tier cold starts (~30s) make the first query slow after inactivity
- The LLM occasionally generates Cypher with incorrect property names — a retry mechanism would improve reliability
- Graph visualization shows entity-type overview only; individual record-level graph exploration is not implemented

**What I would add with more time:**
- Streaming LLM responses so answers appear word-by-word instead of all at once
- Node highlighting in the graph when a query references specific entities
- Conversation memory so follow-up questions can reference previous answers
- A confidence score on each answer indicating how complete the data trace is

---

## Project Structure

```
sap-o2c-graph/
├── backend/
│   ├── main.py            FastAPI app + all API routes
│   ├── ingest.py          Loads all 19 JSONL folders → Neo4j (run once)
│   ├── query_engine.py    NL → Cypher → Execute → Format pipeline
│   ├── graph_api.py       Graph visualization endpoints
│   ├── prompts.py         Full system prompts + guardrail instructions
│   ├── test_backend.py    Smoke tests (run after ingest)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── components/
│   │   │   ├── GraphView.jsx      React Flow visualization
│   │   │   ├── ChatPanel.jsx      NL query interface + example queries
│   │   │   ├── NodeDetailPanel.jsx
│   │   │   └── Header.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── data/                  Place dataset folders here (not committed)
├── ai-logs/               AI coding session transcripts
├── render.yaml            Render deployment config
└── README.md
```