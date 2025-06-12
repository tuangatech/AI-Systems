## Stock Screening Assistant

### Project Overview

Most stock screeners are built for finance pros. They expect users to know what “Price to earning to growth, Trailing 12 months under 1.5 in the tech sector” means — and even when you do, you're stuck with clunky filter panels and Excel downloads, like with [TradeingView](https://www.tradingview.com/screener/) .

So I set out to build something different: a Stock Screening Assistant that understands plain English. You type:

“Show me 3 undervalued tech stocks under $50 with dividends”
and it does the rest — parses your intent, screens stocks in real time, ranks them using smart financial logic, and explains its picks using an LLM.

Under the hood, the assistant combines multi-agent coordination, real-time data pipelines, LLM-powered explanations, and async task execution. It's meant to be practical, portable, and fully local on your laptop — no giant infrastructure needed. Just spin it up with Docker and you're good to go.

This is a side project, but one with teeth — enough to show your NLP, multi-agent architecture, and full-stack orchestration skills without diving into overkill territory.

### Solution Overview

I want to build a realistic but not overly complex, scalable multi-agent system.

**1. Natural Language Understanding**: The chatbot takes whatever the user types and turns it into structured input (e.g., sector, price limits, fundamental filters). We also teach the system to understand fuzzy terms like "safe" or "growth" and map those to actual metrics - like low debt or high revenue growth.

**2. Financial Data Access**: Once we know what the user wants, we pull the related data, like:
- Core metrics like P/E ratio, dividend yield, and sector info.
- Current prices or cached stock prices and financial benchmarks from Yahoo Finance or Polygon.
- Retrieve and analyze SEC filings (10-K, 10-Q) for in-depth insights.

**3. Asynchronous Processing**: Some of this stuff (like grabbing and parsing a PDF 10-K and summarizing it with an LLM) takes time. We don't want to block the UI, so we offload heavy lifting to Celery workers.

**4. Explainability**: After screening and ranking, we pass everything to an LLM that writes a human-readable explanation. Something like:
"This stock has a P/E ratio below its sector average, offers a 3% dividend yield, and shows low debt - a good sign for conservative investors." One advanced feature that can be implemented here is to support chain-of-thought reasoning, so it explains how it got there.

**5. Interactive Frontend**: The UI is built with Streamlit for users to type in their stock query, see results in a sortable table and read short explanations for each stock.

**6. Caching & Performance**: We use Redis to speed things up and avoid hitting APIs unnecessarily. Common queries and benchmarks get cached, so the second time around is always faster. It helps with rate limits too.

**7. Dockerized Setup**: Everything - backend, frontend, task queue - runs in isolated Docker containers. One `docker-compose up` and you're live.

### Tech Stack Breakdown
- Frontend: Streamlit + AgGrid for user input and interactive table display. Good for prototyping, no need React or Next.js here.
- Backend: FastAPI for async-ready API for LLM and screening logic
- Agents & Workflow: LangChain + OpenAI API for multi-agent orchestration + LLM parsing/explanation
- Async Tasks: Celery + Redis for long-running research/extraction tasks. 
  - Celery is a distributed task queue for Python. It lets you run functions (tasks) in the background, outside the normal flow of your application. 
  - Redis is an in-memory data structure store — often used as a message broker , cache, or database. In this project, Redis works as the broker for Celery tasks.
- Data APIs: yfinance + Polygon.io + SEC EDGAR for real-time stock metrics + public filing data
- Caching: Redis + Streamlit @st.cache_data for repeated API calls and filters
- Database: SQLite for logs (optional)
- Deployment: Docker Compose to bring up apps, Celery, Redis

### Agentic Workflow
This project is built around an agent-based architecture using LangChain to coordinate a set of modular, task-specific agents. Each agent focuses on one part of the user query workflow — think of them as cooperative microservices that speak the same LLM-powered language.

Here’s how the agents work together:

**1. Intent Parser Agent**

This is the first stop. It takes raw natural language input from the user and converts it into a structured command. For example with user's input like "Find me 3 undervalued tech stocks under $20"

```json
{
  "intent": "screen",
  "sector": "technology",
  "filters": {
    "price_under": 20,
    "metrics": ["peRatio", "dividendYield"]
  }
}
```

It knows how to interpret investing jargon like “undervalued”, “safe”, or “growth potential” and maps those to actual filters.

- Parses NL query into structured intent (sector, filters, etc.)
- Uses OpenAI LLM with LangChain prompt templates + few-shot
- Validates output against IntentSchema (Pydantic)
- Returns `clarification_needed` field if ambiguous

**2. Data Processor Agent**

Once the intent is structured, this agent fetches stock data using yfinance or Polygon.io. It:
- Applies the filters from the intent
- Default sort by market cap
- Returns a ranked list of tickers with their financial metrics
- Calculates sector metrics (e.g., median P/E)
- caches SP500 stock data (group by sector tech, energy ...) & sector stats in Redis.
- Returns validated StockList and sector metrics using StockSchema

It also injects benchmark data (like sector average P/E) into the logic so the screening isn't just rule-based — it's contextual.

**3. Explanation Agent**
- Explains why each stock was selected
- Uses LLM with sector context and stock metrics
- Outputs structured explanations using LangChain chains and prompt patterns

**3. Research Agent**

This one takes the top stocks from the screener and digs deeper. It pulls filings from the SEC (like 10-Ks or 10-Qs), extracts important sections (risk factors, MD&A), and summarizes them using an LLM.

This gives the chatbot a layer of qualitative analysis — not just number crunching.

**4. Explanation Agent**
Finally, this agent ties everything together into a user-friendly explanation. It uses chain-of-thought prompting to generate a short summary for each recommendation:

“ABC is trading at a P/E of 20 vs. a sector average of 22, offers a 4.2% dividend yield, and has minimal debt. Its 10-K shows stable revenue growth and low exposure to foreign currency risk.”

This makes the chatbot feel like an analyst giving a pitch.


### Infra
Backend (FastAPI):
- Endpoints: 
  - /health
  - /parse: invokes IntentParserAgent
  - /screen: invokes DataProcessorAgent
  - /explain:  invokes ExplanationAgent
  - /ask that runs full chain ??
- CORS, and future expansion support

Frontend (Streamlit):
- Displays table + explanations using AgGrid
- Stores chat history in session_state
- If clarification_needed, prompts user to rephrase
- Sends requests to backend endpoints
- Handles clarification loop (e.g., invalid sector) User gets a message like “Please send another request with a correct sector”
- Supports follow-up questions like “What about energy stocks?” by sending previous context

LangChain Usage:
- Agent orchestration
- Shared memory/state/context handling
- Inter-agent chaining (parse → screen → explain)

Redis for:
- Caching SP500 + sector stats (via redis-py)

System Patterns:
- Agent Interface Abstraction for consistent interface
- Dockerized deployment with docker-compose.yml and Dockerfile
- Config management for API keys, Redis URL, timeouts and runtime defaults



### Implementation

**1. Intent Parser Agent**
- All models like `meta-llama/Meta-Llama-3.1-8B-Instruct`, `Qwen/Qwen3-Reranker-8B`, `microsoft/Phi-3.5-mini-instruct`, `mistralai/Mistral-7B-Instruct-v0.3` do not generate the response as instructed in the prompt, I'm very disappointed. With the below prompt, all models REPEAT the instruction (aka. the prompt), then add MANY identical nested JSON objects, sometimes with explanation. It made me much more challenging to extract the right JSON object (nested JSON exists).

```
  Now parse this query:
  {user_input}

  Output ONLY the JSON object below - NO TEXT BEFORE OR AFTER.
```
- Some models from Meta and Mistral asked to have access approval, so remember to do that on HuggingFace.co first. Then you need to create a Read & Write token to use it to load the model.
- `microsoft/Phi-3.5-mini-instruct` did not generate an expected JSON
- Really slow inference on my RTX2080, like 7 minutes each, then I switched from a local LLM (like Llama or Mistral) to the OpenAI API.
- OpenAI "gpt-4o-mini-2024-07-18" performs better with prompt
- Returns `clarification_needed` if query is ambiguous (e.g. invalid sector).

```bash
pytest test_intent_parser.py -v -s
```

**2. Data Processor Agent**
- With limited resources for a side project, I will just only query stocks in SP500 (top 500 companies in US). I get the list from wikipedia and it might not up-to-date, but if it could be, no problem to our project at all.
- Modular Design: Separated concerns into distinct classes
  - StockIntent: Data model for parsing requests
  - StockData: Data model for stock information
  - MetricCalculator: Handles financial metric calculations
  - StockDataFetcher: Manages data retrieval from Yahoo Finance
  - FilterProcessor: Applies screening filters
  - SP500DataSource: Manages S&P 500 data loading
  - DataProcessorAgent: Main orchestrator
- Multi-threaded Data Fetching
  - Concurrent API calls to Yahoo Finance with configurable thread pool
  - Rate limiting to avoid API throttling
- Metrics
  - P/E Ratio (trailing/forward)
  - P/B Ratio
  - Dividend Yield (converted to percentage)
  - Free Cash Flow Yield
  - Market Cap and Current Price

metric_keys = ["peRatio", "pbRatio", "freeCashFlowYield", "price", "dividendYield", "debtToEquity", "revenueGrowth", "marketCap"]

1. P/E Ratio (Price-to-Earnings Ratio)
Formula: P/E Ratio = Stock Price / Earnings Per Share (EPS)
A high P/E may mean overvalued or high growth expected

2. P/B Ratio (Price-to-Book Ratio)
Formula: P/B Ratio = Stock Price / Book Value Per Share
(Book Value = Total Assets - Liabilities)
<1.0 suggests potentially undervalued (price < book value)

3. Free Cash Flow Yield (FCF Yield)
Formula:
FCF Yield = Free Cash Flow / Market Capitalization
(Free Cash Flow = Operating Cash Flow - Capital Expenditures)
High yield = strong cash generation ability. More reliable than P/E (cash is harder to manipulate than earnings)

4. Dividend Yield
Formula: Annual Dividends Per Share (DPS) / Current Stock Price  x 100
- ​High Dividend Yield (>4%) → 
  - Could mean a good income stock (e.g., utilities, REITs).
  - Stable companies tend to maintain/grow dividends.

An "undervalued" stock might have: --> too complex, keep it simple for now
- P/E < sector average
- P/B < 1.5
- FCF Yield > 4%

Full picture:
- Dividend Yield: >3% (Good income) - not just this metric, High-yield stocks mean less investment = may grow slower
- Payout Ratio: <60% (Sustainable)
- Dividend Growth Streak: 5+ years (Reliable)

```bash
pytest test_intent_parser.py -v -s
pytest test_data_processor.py -v -s
```

**3. Main API**
- Go to rootdir: C:\TuanTA\ML Projects\AI-Systems\Stock-Screening-Assistant, test with `pytest -s backend/tests/test_main.py::test_parse_endpoint` to print out the response. 

**4. Frontend App**

**5. Testing frontend - backend**

Start the server `uvicorn` for FastAPI app (main.py)
```bash
cd api
uvicorn main:app --reload
```

Go to http://localhost:8000/docs, test the `/parse` endpoint.
```json
# sample query
{
  "query": "Show me 3 undervalued tech stocks under $50 with dividends"
}
# return:
{
  "intent": {
    "intent": "screen",
    "sector": "technology",
    "limit": 3,
    "metrics": [
      "peRatio",
      "pbRatio",
      "dividendYield"
    ],
    "filters": {
      "price_lt": 50,
      "dividendYield_gt": 0,
      "freeCashFlowYield_gt": 5
    }
  }
}
```

Run FastAPI app locally

```bash
cd backend/api
uvicorn main:app --reload
```

Run Streamlit app locally

```bash
cd frontend
streamlit run app.py
```

http://localhost:8501

Type: Show me 3 undervalued tech stocks under $250 with dividends

### Improvements
- inter-agent communication Add Agent Communication Allow agents to:
  - Send messages to each other
  - Request information
  - Clarify ambiguous inputs
- Add Autonomy & Reasoning: If using LLMs (e.g., GPT, Gemini, Mistral), agents can:
  - Decide what data they need
  - Generate their own queries
  - Evaluate responses
  - Refuse invalid requests
- Add Planning & Coordination with LangChain:
  - Plan steps (e.g., parse → screen → explain)
  - Delegate tasks
  - Reflect and improve over time

User Input
     ↓
[IntentParserAgent]
   - Parses intent
   - Checks for ambiguity
   - If ambiguous → returns clarification request
   - Else → returns structured intent

If clarification needed:
     ↓
[Frontend]
   - Displays question to user
   - Gets response

Back to IntentParserAgent:
     ↓
[IntentParserAgent.refine_intent()]
   - Merges original intent + user clarification

Then:
     ↓
[DataProcessorAgent]
   - Uses final intent to fetch and filter stocks

Finally:
     ↓
[Frontend]
   - Shows results


User Request
   |
   ▼
[IntentParserAgent] ←─── Few-shot prompt, intent schema, clarification flag
   |
   ▼
[DataProcessorAgent] ←─── Pull from yfinance, SP500 cache in Redis, sector stats
   |
   ▼
[ExplanationAgent] ←─── Generates LLM-based explanations using LangChain chains
   |
   ▼
[Frontend (Streamlit)] ←─── Receives result + explanation or clarification message


stock_screening_assistant/
│
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseAgent definition
│   │   ├── intent_parser.py           # Refactored IntentParserAgent
│   │   ├── data_processor.py          # Future DataProcessorAgent
│   │   └── explanation_agent.py       # Future ExplanationAgent
│   │
│   ├── chains/
│   │   └── main_chain.py              # LangChain RunnableSequence (parse → screen → explain)
│   │
│   ├── api/
│   │   └── routes.py                  # FastAPI endpoints for parse/screen/explain
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── intent.py                  # Pydantic schema for parsed intent
│   │   └── stock.py                   # Stock list schema
│   │
│   ├── utils/
│   │   └── redis_cache.py             # Redis helper functions
│   │
│   ├── main.py                        # FastAPI entry point
│   └── .env
│
├── frontend/
│   └── streamlit_app.py               # Streamlit frontend
│
├── Dockerfile
├── docker-compose.yml                # Redis + app
└── README.md
