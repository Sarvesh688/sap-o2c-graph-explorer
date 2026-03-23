"""
test_backend.py — Quick smoke tests for the backend
Run AFTER ingest.py: python test_backend.py

Tests:
  1. Neo4j connection + node counts
  2. Graph API overview endpoint
  3. Entity sample fetch
  4. NL query pipeline (requires GROQ_API_KEY)
  5. Guardrail rejection test
"""

import os, json
from dotenv import load_dotenv

load_dotenv()

print("=" * 55)
print("  SAP O2C Backend Smoke Tests")
print("=" * 55)

# ── Test 1: Neo4j connection ───────────────────────────────
print("\n[1] Neo4j connection + node counts...")
try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    with driver.session() as s:
        result = s.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS cnt
            ORDER BY cnt DESC
        """)
        rows = list(result)
        if not rows:
            print("  ✗ No nodes found — did you run ingest.py?")
        else:
            total = sum(r["cnt"] for r in rows)
            print(f"  ✓ Connected. {total:,} total nodes across {len(rows)} labels:")
            for r in rows:
                print(f"      {r['label']:<25} {r['cnt']:>6,}")
    driver.close()
except Exception as e:
    print(f"  ✗ Neo4j connection failed: {e}")
    print("    Check NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD in .env")
    exit(1)

# ── Test 2: Graph API overview ─────────────────────────────
print("\n[2] Graph API overview...")
try:
    from graph_api import get_overview_graph
    g = get_overview_graph()
    print(f"  ✓ {len(g['nodes'])} nodes, {len(g['edges'])} edges returned")
except Exception as e:
    print(f"  ✗ graph_api.get_overview_graph() failed: {e}")

# ── Test 3: Entity sample ──────────────────────────────────
print("\n[3] Entity sample (SalesOrder, limit 3)...")
try:
    from graph_api import get_entity_sample
    rows = get_entity_sample("SalesOrder", 3)
    print(f"  ✓ Got {len(rows)} SalesOrder records")
    if rows:
        print(f"    Sample ID: {rows[0].get('id', 'N/A')}")
except Exception as e:
    print(f"  ✗ get_entity_sample failed: {e}")

# ── Test 4: NL query (valid question) ─────────────────────
print("\n[4] NL query — valid question...")
try:
    from query_engine import query
    result = query("Which customers have the highest total order value?")
    if result["type"] == "success":
        print(f"  ✓ Query succeeded")
        print(f"    Cypher: {result['cypher'][:80]}...")
        print(f"    Records: {result['record_count']}")
        print(f"    Answer: {result['message'][:120]}...")
    else:
        print(f"  ✗ Query returned type={result['type']}: {result['message'][:100]}")
except Exception as e:
    print(f"  ✗ query() failed: {e}")

# ── Test 5: Guardrail rejection ────────────────────────────
print("\n[5] Guardrail — off-topic question...")
try:
    from query_engine import query
    result = query("Write me a poem about Python programming")
    if result["type"] == "error":
        print(f"  ✓ Off-topic rejected correctly")
        print(f"    Message: {result['message'][:100]}")
    else:
        print(f"  ✗ Off-topic was NOT rejected (type={result['type']})")
        print(f"    This is a guardrail failure — fix prompts.py")
except Exception as e:
    print(f"  ✗ guardrail test failed: {e}")

# ── Test 6: Flow subgraph ──────────────────────────────────
print("\n[6] Flow subgraph for first SalesOrder...")
try:
    from graph_api import get_entity_sample, get_flow_subgraph
    orders = get_entity_sample("SalesOrder", 1)
    if orders:
        so_id = orders[0]["id"]
        flow = get_flow_subgraph(so_id)
        print(f"  ✓ Flow for SalesOrder {so_id}: "
              f"{len(flow['nodes'])} nodes, {len(flow['edges'])} edges")
    else:
        print("  ⚠ No SalesOrders found to test with")
except Exception as e:
    print(f"  ✗ get_flow_subgraph failed: {e}")

print("\n" + "=" * 55)
print("  Done. Fix any ✗ items before deploying.")
print("=" * 55 + "\n")
