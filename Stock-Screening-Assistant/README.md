## Stock Screening Assistant

### Project Overview

Most stock screeners are built for finance pros. They expect users to know what “Price to earning to growth, Trailing 12 months under 1.5 in the tech sector” means — and even when you do, you're stuck with clunky filter panels and Excel downloads, like with [TradeingView](https://www.tradingview.com/screener/) .

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

**5. Interactive Frontend**: The UI is built with Streamlit for users to type in their stock query, see results in a sortable table and read short explanations for each stock.

**6. Caching & Performance**: We use Redis to speed things up and avoid hitting APIs unnecessarily. Common queries and benchmarks get cached, so the second time around is always faster. It helps with rate limits too.

**7. Dockerized Setup**: Everything - backend, frontend, task queue - runs in isolated Docker containers. One `docker-compose up` and you're live.

### Tech Stack Breakdown
- Frontend: Streamlit + AgGrid for user input and interactive table display
- Backend: FastAPI for async-ready API for LLM and screening logic
- Agents & Workflow: LangChain + HuggingFace (Llama 3 8B instruct) for multi-agent orchestration + LLM parsing/explanation
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

**2. Data Processor Agent**

Once the intent is structured, this agent fetches stock data using yfinance or Polygon.io. It:
- Applies the filters from the intent
- Scores the results based on logic (e.g., low P/E, high yield, low debt)
- Returns a ranked list of tickers with their financial metrics

It also injects benchmark data (like sector average P/E) into the logic so the screening isn't just rule-based — it's contextual.

**3. Research Agent**

This one takes the top stocks from the screener and digs deeper. It pulls filings from the SEC (like 10-Ks or 10-Qs), extracts important sections (risk factors, MD&A), and summarizes them using an LLM.

This gives the chatbot a layer of qualitative analysis — not just number crunching.

**4. Explanation Agent**
Finally, this agent ties everything together into a user-friendly explanation. It uses chain-of-thought prompting to generate a short summary for each recommendation:

“ABC is trading at a P/E of 20 vs. a sector average of 22, offers a 4.2% dividend yield, and has minimal debt. Its 10-K shows stable revenue growth and low exposure to foreign currency risk.”

This makes the chatbot feel like an analyst giving a pitch.

**Coordination with LangChain**

LangChain’s RunnableMap and RunnableSequence are used to compose the agents into an end-to-end pipeline. Each agent runs as a self-contained unit but passes structured outputs to the next step — making the workflow modular, testable, and easy to extend.


### Implementation

**1. Intent Parser Agent**
- All models like `meta-llama/Meta-Llama-3.1-8B-Instruct`, `Qwen/Qwen3-Reranker-8B`, `microsoft/Phi-3.5-mini-instruct`, `mistralai/Mistral-7B-Instruct-v0.3` do not generate the response as instructed in the prompt, I'm very disappointed. With the below prompt, all models REPEAT the instruction (aka. the prompt), then add MANY identical nested JSON objects, sometimes with explanation. It made me much more challenging to extract the right JSON object.

```
  Now parse this query:
  {user_input}

  Output ONLY the JSON object below - NO TEXT BEFORE OR AFTER.
```
- Some models from Meta and Mistral asked to have access approval, so remember to do that on HuggingFace.co first. Then you need to create a Read & Write token to use it to load the model.
- `microsoft/Phi-3.5-mini-instruct` did not generate an expected JSON
- Really slow inference on my RTX2080, like 7 minutes each, then I switched from a local LLM (like Llama or Mistral) to the OpenAI API.
- OpenAI "gpt-4o-mini-2024-07-18" performs better with prompt