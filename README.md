# 🤖 DataBot — Text-to-SQL Agent

> Visagio Rocket Lab 2026 · GenAI Activity  
> A conversational agent that translates natural-language questions into SQL queries against an e-commerce SQLite database.

---

## Architecture

```
atividade_genai_rocketlab/
├── banco.db                  # SQLite database (download separately)
├── database_manager.py       # DB connection, schema extraction, safe query execution
├── agent.py                  # Pydantic AI agent, tools (list_tables, get_schema, run_sql_query)
├── main.py                   # Entry point — async conversational loop
├── requirements.txt
├── .env.example
└── README.md
```

### Component Responsibilities

| File | Responsibility |
|---|---|
| `database_manager.py` | Connects to `banco.db`, extracts DDL, executes **SELECT-only** queries |
| `agent.py` | Defines the `Agent[AgentDeps, QueryResponse]`, system prompt, guardrails, and ReAct tools |
| `main.py` | Initialises dependencies, runs the async `input()` loop with conversation history |

### Data Flow

```
User Question
     │
     ▼
  agent.run()
     │  ┌──────────────────────────────────┐
     ├─►│ list_tables()   → table names    │
     ├─►│ get_schema()    → DDL            │  ← ReAct loop
     └─►│ run_sql_query() → rows / error   │
        └──────────────────────────────────┘
              │
              ▼
        QueryResponse (answer, sql_used, data_summary, row_count)
```

---

## Setup

### Prerequisites

- Python 3.11+
- A valid **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey)
- The `banco.db` file from the shared activity folder

### Installation

```bash
# 1. Clone the repository

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Place banco.db in the project root
# (download from the shared activity folder)

# 6. Run the agent
python main.py
```

---

## Example Queries

| Category | Example Question |
|---|---|
| Sales & Revenue | "Quais são os 10 produtos mais vendidos?" |
| Logistics | "Qual o percentual de pedidos entregues no prazo por estado?" |
| Satisfaction | "Qual a média de avaliação por vendedor? Top 10." |
| Consumer Behavior | "Quais estados têm o maior ticket médio?" |
| Seller Performance | "Quais categorias têm maior taxa de avaliação negativa?" |
| General | "How many orders are in each status?" |

---

## Guardrails

- **SELECT-only**: The `DatabaseManager` rejects any non-SELECT statement at the Python level before it reaches the database.
- **Row limit**: All queries are capped at **30 rows**.
- **Error self-correction**: If a query fails, the error message is returned as JSON to the LLM, which rewrites and retries the SQL automatically.
- **Scope enforcement**: The system prompt instructs the agent to refuse questions unrelated to the database.

---

## Extending the Agent

- **Add a tool**: Decorate an async function with `@agent.tool` in `agent.py`.
- **Change the model**: Update `GeminiModel("gemini-2.5-flash")` in `agent.py` to `gemini-2.5-flash-lite` for lower latency.
- **Add a FastAPI layer**: Wrap `agent.run()` in a POST endpoint and expose `QueryResponse` as the response model.
- **Add charts**: Detect numeric columns in `QueryResponse.rows` and render with `matplotlib` or `plotly`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `pydantic-ai` | Agent framework, tool orchestration, structured output |
| `pydantic` | `BaseModel` for `QueryResponse` and `AgentDeps` |
| `google-generativeai` | Gemini 2.5 Flash model provider |
| `python-dotenv` | Load `GEMINI_API_KEY` from `.env` |

---

## 📄 License

MIT — free for academic and commercial use.
