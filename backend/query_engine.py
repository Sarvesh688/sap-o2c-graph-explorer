"""
query_engine.py — NL → Cypher → Execute → Format answer
"""

import json
import os
from neo4j import GraphDatabase
from groq import Groq
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT, RESULT_FORMATTER_PROMPT

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def nl_to_cypher(question: str) -> dict:
    resp = groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": question}
        ],
        temperature=0.1,
        max_tokens=1024
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {"error": f"LLM returned unparseable response: {raw[:300]}"}


def run_cypher(cypher: str) -> list:
    with driver.session() as session:
        result = session.run(cypher)
        records = []
        for record in result:
            row = {}
            for key in record.keys():
                val = record[key]
                if hasattr(val, "_properties"):
                    row[key] = {**dict(val._properties), "_labels": list(val.labels)}
                else:
                    row[key] = val
            records.append(row)
        return records


def format_answer(question: str, cypher: str, records: list) -> str:
    display = records[:30]
    truncated = len(records) > 30
    prompt = f"""
Original question: {question}

Cypher used: {cypher}

Results ({len(records)} total{', showing first 30' if truncated else ''}):
{json.dumps(display, indent=2, default=str)}

Provide a clear, business-friendly answer.
"""
    resp = groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": RESULT_FORMATTER_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.3,
        max_tokens=512
    )
    return resp.choices[0].message.content.strip()


def extract_node_ids(records: list) -> list:
    ids = []
    for record in records:
        for val in record.values():
            if isinstance(val, dict) and "id" in val:
                ids.append(str(val["id"]))
    return list(set(ids))


def query(user_question: str, history: list = None) -> dict:
    llm_resp = nl_to_cypher(user_question)

    if "error" in llm_resp:
        return {
            "type": "error",
            "message": llm_resp["error"],
            "cypher": None,
            "records": [],
            "highlighted_nodes": []
        }

    cypher = llm_resp.get("cypher", "")
    explanation = llm_resp.get("explanation", "")

    if not cypher:
        return {
            "type": "error",
            "message": "Could not generate a query for this question.",
            "cypher": None,
            "records": [],
            "highlighted_nodes": []
        }

    try:
        records = run_cypher(cypher)
    except Exception as e:
        return {
            "type": "cypher_error",
            "message": f"Query execution failed: {str(e)}",
            "cypher": cypher,
            "records": [],
            "highlighted_nodes": []
        }

    answer = format_answer(user_question, cypher, records) if records \
        else "No records found matching your criteria in the dataset."

    return {
        "type": "success",
        "message": answer,
        "explanation": explanation,
        "cypher": cypher,
        "records": records[:50],
        "record_count": len(records),
        "highlighted_nodes": extract_node_ids(records)
    }
