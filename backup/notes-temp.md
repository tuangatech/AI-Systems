### Notes
- Traditional workflow automation requires the user to define the rules (e.g., do X, when Y happens given Z constraint). Agentic AI goes one step further and takes care of the logic itself by using **an LLM (to think), memory (to remember), and tools (to act)**.
- These traditional tools depend on a user to define rules and logic for execution e.g., do X when Y happens. Each branch of the execution flow needs to be manually laid out to ensure a proper resolution.
- In contrast, the agentic workflow tools do NOT need a user to define the logic flow. The agent can reason and think on how to execute the task, avoid errors, and cover edge cases. All it needs is access to the tools (e.g., Calendar, Email, Weather API).

What is an agentic workflow? An agentic workflow refers to a process or system that incorporates the capabilities of autonomous agents—software programs that can perceive, reason, and act in an environment to achieve specific goals. These workflows leverage the agency of intelligent systems to automate, optimize, or enhance complex tasks. The term is commonly associated with artificial intelligence (AI) and can describe a collaborative interaction between humans and AI or fully autonomous systems.

**Key Features of an Agentic Workflow:**
- Autonomy: The agents operate independently, performing tasks without constant human intervention.
- Proactivity: They anticipate needs or problems and take initiative to address them.
- Adaptivity: The agents learn and adjust their behavior based on feedback and environmental changes.
- Goal-Oriented: Each agent has a clearly defined objective, aligning with the overall purpose of the workflow.
- Collaboration: Agents can work together or alongside humans, sharing information and tasks.
- Decision-Making: The workflow may include multi-agent reasoning, where agents make decisions based on logic, data, and predefined rules.

### E-commerce Order Fulfillment System

**Workflow**: Simulate an e-commerce order from placement to delivery with agents:
1. **Order Processing Agent**: Validates the order (checks inventory, payment).
2. **Inventory Agent**: Updates inventory and triggers restocking if needed.
3. **Shipping Agent**: Selects shipping method and generates a label.
4. **Escalation Agent**: for any errors

**Solution**:
- Build a Streamlit app for users to click "Buy" some items.
- Use a simple inventory database. Fake a shipping request to UPS and generate a shipping label. 
- Log agent decisions on web page for demo visuals

**Technical Solution**:
- Each agent is a separate service (showcases microservices skills)
- Implement pub/sub or RPC (e.g., RabbitMQ/ZeroMQ)
- Build in retries/fallbacks (e.g., "Escalation Agent" for errors)
- Use Python + LangChain/LlamaIndex + FastAPI + Streamlit + ...

**Benefits**:
- Shows integration of multiple steps in a business process.
- Involves state management (inventory, order status).
- Real-world application: e-commerce automation. Demonstrates real-world problem-solving while keeping complexity manageable.

**Key Technical Benefits for Your Portfolio:**
- Modular Design - Each agent is a separate service (showcases microservices skills)
- Communication Patterns - Implement pub/sub or RPC (e.g., RabbitMQ/ZeroMQ)
- Failure Handling - Build in retries/fallbacks (e.g., "Escalation Agent" for errors)
- Observability - Log agent decisions (great demo visuals)
- Lightweight Tech Stack - Use Python + LangChain/LlamaIndex + FastAPI (employer-friendly)


## Stock Screening Assistant

### Project Overview

Most stock screeners are built for finance pros. They expect users to know what “Price to earning to growth, Trailing 12 months under 1.5 in the tech sector” means — and even when you do, you're stuck with clunky filter panels and Excel downloads, like with [TradeingView](https://www.tradingview.com/screener/).

So I set out to build something different: a Stock Screening Assistant that understands plain English. You type:

“Show me 3 undervalued tech stocks under $50 with dividends”
and it does the rest — parses your intent, screens stocks in real time, ranks them using smart financial logic, and explains its picks using an LLM.

Under the hood, the assistant combines multi-agent coordination, real-time data pipelines, LLM-powered explanations, and async task execution. It's meant to be practical, portable, and fully local on your laptop — no giant infrastructure needed. Just spin it up with Docker and you're good to go.

This is a side project, but one with teeth — enough to show your NLP, multi-agent architecture, and full-stack orchestration skills without diving into overkill territory.

### Solution Overview
**1. Natural Language Understanding**: The chatbot takes whatever the user types and turns it into structured input (e.g., sector, price limits, fundamental filters). We also teach the system to understand fuzzy terms like "safe" or "growth" and map those to actual metrics - like low debt or high revenue growth.

**2. Financial Data Access**: Once we know what the user wants, we pull the related data, like:
- Core metrics like P/E ratio, dividend yield, and sector info.
- Current prices or cached stock prices and financial benchmarks from Yahoo Finance or Polygon.
- Retrieve and analyze SEC filings (10-K, 10-Q) for in-depth insights.

**3. Asynchronous Processing**: Some of this stuff (like grabbing and parsing a PDF 10-K and summarizing it with an LLM) takes time. We don't want to block the UI, so we offload heavy lifting to Celery workers.

**4. Explainability**: After screening and ranking, we pass everything to an LLM that writes a human-readable explanation. Something like:
"This stock has a P/E ratio below its sector average, offers a 3% dividend yield, and shows low debt - a good sign for conservative investors." One advanced feature that can be implemented here is to support chain-of-thought reasoning, so it explains how it got there.

**5. Interactive Frontend**: The UI is built with Streamlit - lightweight but solid. It lets users type in their stock query, see results in a sortable table and read short explanations for each stock.

**6. Caching & Performance**: We use Redis to speed things up and avoid hitting APIs unnecessarily. Common queries and benchmarks get cached, so the second time around is always faster. It helps with rate limits too.

**7. Dockerized Setup**: Everything - backend, frontend, task queue - runs in isolated Docker containers. One `docker-compose up` and you're live.

### Tech Stack Breakdown
- Frontend: Streamlit + AgGrid for user input and interactive table display
- Backend: FastAPI for async-ready API for LLM and screening logic
- Agents & Workflow: LangChain + HuggingFace (Llama 3 8B instruct) for multi-agent orchestration + LLM parsing/explanation
- Async Tasks: Celery + Redis for long-running research/extraction tasks
- Data APIs: yfinance + Polygon.io + SEC EDGAR for real-time stock metrics + public filing data
- Caching: Redis + Streamlit @st.cache_data for repeated API calls and filters
- Database: SQLite for logs (optional)
- Deployment: Docker Compose to bring up apps, Celery, Redis


**Goal:**

Build a lightweight but production-grade Stock screening assistant that interprets natural language queries (e.g., "Show me 3 undervalued tech stocks"), fetches/analyzes financial data (e.g, P/E ratio, dividend yield, debt-to-equity, deeper fundamental insights like Cash Flow Metrics from 10-K filings), and explains its recommendations using multiple AI agents.

The system will:
- Understand the user's intent
- Extract relevant financial metrics
- Query real-time or cached stock data
- Rank and return matching stocks with explanations

User queries:
- "Show me 3 undervalued tech stocks under $50 with dividends"
- "Show me undervalued tech stocks"
- "Find dividend-paying REITs under $40"
- "Top 5 undervalued stocks in healthcare"
- "Find me high-dividend energy stocks"

**Tech Stack (Lightweight Side Project Friendly):**
- Backend: FastAPI + Celery for Async task queue for research tasks
- Frontend: Streamlit + AgGrid Interactive tables with sorting
- LLM: Open-source LLMs from HuggingFace Llama-3-8B-instruct
- Agents: LangChain for Core AI workflow like Intent Parsing NLU, Multi-Agent Coordination (research/screening/explanation flows), LLM Integration (HuggingFace), Explainability (chain-of-thought prompting)
- Cache: Redis + @st.cache_data
- Financial Data: Yahoo Finance + Polygon.io (free), SEC EDGAR (free tiers)
- DevOps: Docker Compose brings up app, Celery, Redis cleanly. A single Docker container for the backend and one for the frontend (Streamlit)


User Query: "Find high-dividend energy stocks under $50"
        ↓
[Query Interpreter Agent] → Interprets query → {"intent": "screen", "sector": "energy", "metric": "dividend_yield", "threshold": "high", "price_under": 50}
        ↓
[Metric Selector Agent] → Maps intent to actual metrics → ["dividendYield", "regularMarketPrice"]
        ↓
[Data Fetcher Agent] → Gets live stock data from API → List of energy stocks + metrics
        ↓
[Ranking Engine Agent] → Filters and ranks based on criteria → Top 5 matches
        ↓
[Answer Generator Agent] → Formats results in natural language → Final response
        ↓
Output: Ranked list shown in Streamlit UI

### Agents
1. Intent Parser Agent: Understands natural language input and extracts structured intent (e.g., metric, sector, filters). 

- Maps intent to specific fundamental metrics (e.g., “undervalued” → P/E < industry average)
- Add synonyms/variations (cheap stocks, value plays) via a synonym dictionary or embeddings-based intent expansion using LangChain tools.
- Cache frequent intent → metric mappings using Redis.
```json
{
  "intent": "screen",
  "sector": "technology",
  "metrics": ["peRatio", "revenueGrowth"],
  "filters": {"price_under": 20}
}
```

2. Data Processor Agent: Fetch stock fundamentals (price, dividend yield, P/E, market cap) using yfinance. Apply filters from the query. Rank results based on scoring logic
- Pre-loaded sector benchmarks into Redis or SQLite on startup (updated daily)
- Add try/except for missing data (common in yfinance).
- Preprocess benchmark values in a background task (daily Celery beat).
- Consider adding volatility or beta filtering for more nuanced control.
- Batch screening via pandas
```python
def screen_stocks(df, filters):
    return df[
        (df['sector'] == filters['sector']) &
        (df['pe'] < df['sector_pe']) &
        (df['price'] < filters.get('price_limit', float('inf')))
    ].head(3)

def rank_stocks(stocks):
    return sorted(
        stocks,
        key=lambda x: (
            -x['dividend_yield'],  # Higher better
            x['debt_to_equity']     # Lower better
        )
    )
```

3. Research Agent: Pull deeper fundamental insights from 10-K filings for top 3 ranked stocks. 
- Pull 10-Q/8-K filings via sec-api.io (free tier)
- Extract key sections using unstructured.io
- Summarize risks/growth factors with Llama-3-8B
- Consider classifying risks into categories (macro, competitive, operational).
- Consider an auto-retry mechanism on Celery failure for 10-K fetch or API timeouts.

```python
stocks_df = pd.DataFrame({
    'ticker': ['AAPL', 'MSFT'],
    'pe': [28.5, 32.1],
    'sector_pe': 25.3,
    'dividend_yield': [0.5, 0.8],
    'debt_to_equity': [1.2, 0.3]
})

```
4. Explanation Agent: Generate a natural language summary of results using an LLM.
- Use LangChain’s RefineChain or stuff + template for better explanations.
- Just a short summary for users

###  UI Design (Streamlit)
Simple and clean layout:

- Text input box for query
- Submit button
- Loading spinner
- Results section showing:
  - Stock ticker
  - Key metrics
  - Short explanation (generated by LLM)

### Performance Optimizations
- Pre-Computation: Daily cache of S&P 500 metrics
- Lazy Loading: 
```python
@st.cache_resource
def load_model():
    return Llama.from_pretrained(...)
```
### Demo Script Idea:

1. Show "Find me undervalued fintech stocks"

2. Demonstrate how agents:
- Parse "undervalued" = P/E < sector avg + positive FCF
- Filter to fintech sector
- Rank by margin of safety

3. Display SEC filing highlights for top pick


fundamental metrics (P/E ratio, debt-to-equity, dividend yield, etc.)
SEC filings (10-Q, 8-K), SeekingAlpha
User Query: "Find me high-dividend energy stocks"
Maps intent to specific fundamental metrics (e.g., “undervalued” → P/E < industry average)
"Show me cheap tech stocks" = Stocks with low P/E ratios in the tech sector
"Find dividend-paying REITs under $40" = REITs with positive dividend yield priced below $40
"Top 5 undervalued stocks in healthcare" = Healthcare stocks trading below intrinsic value estimates

Cash Flow Metrics -> SEC 10-K filings
Historical Dividends -> yfinance

Combine LLMs for fluency and rules/data for accuracy 
- Use rules to extract key facts (e.g., “dividend grew for 5 years”)
- Feed those facts into the LLM as part of the prompt
- Let the LLM write the final explanation

### Wrap-Up
This project is built to be both developer-friendly and user-centric — you get a clean architecture to tinker with multi-agent AI workflows, and users get a smart assistant that speaks their language and delivers actual investment insights.

It's the kind of project that’s:
- Fun to build
- Easy to demo
- Deep enough to showcase AI orchestration skills
- Fully runnable on your laptop


**Not suitable:**

- Automation: n8n for Pipeline Orchestration, Error Recovery Workflows, Third-Party Integrations