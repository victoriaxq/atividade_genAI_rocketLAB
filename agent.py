from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from database_manager import DatabaseManager
from dotenv import load_dotenv

load_dotenv()


# ── Dependency container ────────────────────────────────────────
@dataclass
class AgentDeps:
    """Dependencies injected into every tool call."""
    db: DatabaseManager


# ── Structured output model ──────────────────────────────────────────────────
class QueryResponse(BaseModel):
    """Structured response returned by the agent after every interaction."""
    answer: str = Field(description="Clear, concise answer in plain language for the user.")
    sql_used: str | None = Field(
        default=None,
        description="The final SQL query executed, if any."
    )
    data_summary: str | None = Field(
        default=None,
        description="Brief summary of the data returned (e.g., 'Top result: Product X with 1,200 sales')."
    )
    row_count: int | None = Field(
        default=None,
        description="Number of rows returned by the query."
    )


# ── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are DataBot, an expert Data Analyst assistant for an e-commerce company.
Your mission is to help non-technical users understand their business data
by translating natural-language questions into SQL and interpreting results.

## CAPABILITIES
You have access to a SQLite database (banco.db) with these tables:
- dim_consumidores   — consumer dimension (demographics, location)
- dim_produtos       — product dimension (name, category, price)
- dim_vendedores     — seller dimension (seller info, location)
- fat_pedidos        — orders fact table (status, timestamps, delivery info)
- fat_pedido_total   — order totals (revenue, freight)
- fat_itens_pedidos  — order items (product, quantity, price)
- fat_avaliacoes_pedidos — order reviews (score, comments)

## TOOLS
- `list_tables`: Use to confirm which tables exist.
- `get_schema`: Use to inspect table columns and types before writing SQL.
- `run_sql_query`: Use to execute SELECT queries. Results are capped at 30 rows.

## WORKFLOW (ReAct pattern)
1. THINK — Understand the user's question and identify relevant tables.
2. ACT — Use `get_schema` to confirm column names, then write the SQL.
3. OBSERVE — Run the query with `run_sql_query` and inspect results.
4. CORRECT — If the query fails, read the error, fix the SQL, and retry.
5. ANSWER — Summarise the data in plain language.

## GUARDRAILS (MANDATORY)
- ONLY generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Always LIMIT results to 30 rows maximum.
- If the question is unrelated to the database, politely decline.
- Never expose raw connection strings or internal file paths.
- If the user asks something ambiguous, ask one clarifying question.
- Format monetary values as R$ with two decimal places.
- Always translate your final answer to the same language the user wrote in.
"""


# ── Agent definition ─────────────────────────────────────────────────────────
model = GeminiModel(
    "gemini-2.5-flash",
    provider=GoogleGLAProvider(api_key=os.getenv("GEMINI_API_KEY"))
)

agent: Agent[AgentDeps, QueryResponse] = Agent(
    model=model,
    deps_type=AgentDeps,
    output_type=QueryResponse,
    system_prompt=SYSTEM_PROMPT,
)


# ── Tools ────────────────────────────────────────────────────────────────────
@agent.tool
async def list_tables(ctx: RunContext[AgentDeps]) -> str:
    """Returns all table names available in the database."""
    tables = ctx.deps.db.list_tables()
    return json.dumps(tables)


@agent.tool
async def get_schema(ctx: RunContext[AgentDeps]) -> str:
    """Returns the full DDL (CREATE TABLE statements) of all tables.
    Use this to understand column names and types before writing SQL."""
    return ctx.deps.db.get_schema_ddl()


@agent.tool
async def run_sql_query(ctx: RunContext[AgentDeps], sql: str) -> str:
    """
    Executes a SELECT SQL query against the database.

    Args:
        sql: A valid SQLite SELECT statement. Results are capped at 30 rows.

    Returns:
        JSON string with keys: columns, rows, count.
        On error, returns a JSON object with key 'error' describing the problem
        so the agent can self-correct the SQL.
    """
    try:
        result: dict[str, Any] = ctx.deps.db.execute_query(sql)
        return json.dumps(result, ensure_ascii=False, default=str)
    except (ValueError, RuntimeError) as exc:
        # Feed error back to LLM for self-correction
        return json.dumps({"error": str(exc)})
