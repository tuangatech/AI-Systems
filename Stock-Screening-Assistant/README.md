## Building a Stock Screening Assistant using Multi-Agent System

Most stock screeners are built for finance pros. They expect users to know things like "Price to earning to growth, Trailing 12 months under 1.5 in the tech sector", and even when you do, you're stuck with clunky filter panels and Excel downloads, think TradingView or similar tools.

In this side project, I'm building a Stock Screening Assistant that understands plain English. You type something like "Show me 3 undervalued tech stocks under $250 with dividend" and it handle the rest - parses your intent, screens stocks using Yahoo Finance API, and explains its picks using a language model.

Behind the scenes, the system parses the nature language into structured metrics and filters, pulls financial data (like P/E, dividend yield, debt-to-equity, etc.), applies screening rules, collect sector-level stats and finally, presents its findings in a clear, explainable format like a helpful financial assistant. All the steps orchestrated through a multi-agent architecture. It's designed to be practical, portable, and fully local on your computer.

To keep things manageable (and realistic for a solo project), the assistant only screens stocks from the S&P 500. Definitions for terms like "undervalued" or "safe" are intentionally simple - this isn't about beating the market. I'm not a financial expert, and the assistant doesn't pretend to be one. I try to show what's technically possible when language models, financial data APIs, and autonomous agent workflows come together.

This post is about AI engineering behind it: natural language understanding, financial data processing, modular agent design, agent workflow with branching, and building an architecture that could scale into something production-grade. 

If you're a developer interested in NLP, agentic AI systems, or building intelligent tools that interface with real data, this project is for you.

## Solution Overview

I want to build a realistic and scalable multi-agent system.

**1. Natural Language Understanding**: The chatbot takes whatever the user types and turns it into structured input (e.g., sector, price limits, fundamental filters). We also teach the system to understand fuzzy terms like "safe" or "growth" and map those to actual metrics - like low debt or high revenue growth.

**2. Financial Data Access**: Once we know what the user wants, we pull the related data, like:
- The system use 8 metrics like "peRatio", "pbRatio", "freeCashFlowYield", "dividendYield", "debtToEquity", "revenueGrowth", "price", "marketCap". Except price, all other metrics are fundamental (correct word?) and do not change much everyday so I cache these stock info by sector (e.g., Health Care, Real Estate)
- Get Core metrics like P/E ratio, dividend yield, etc. from the cache.
- Calculate median values for each sector 
- We can implement more advanced feature like analyzing SEC filings (10-K, 10-Q) for in-depth insights about a company.

**3. Explainability**: After screening, we pass user query, filtered stock info, sector info to an LLM that writes a human-readable explanation. Something like:
"This stock has a P/E ratio below its sector average, offers a 3% dividend yield, and shows low debt - a good sign for conservative investors."


### Architecture Design
At its core, the Stock Screening Assistant is a modular, multi-agent system that turns natural language into structured screening results — using real financial data and explainable logic.


**1. Agentic Workflow**

The system is structured around three core agents, each responsible for a specific part of the flow. These agents are composed using LangChain’s Runnable interfaces, which makes chaining and branching straightforward. Every agent is loosely coupled and stateless, keeping the system clean, testable, and easy to maintain.

**2. Intent Parser Agent**

This is the first agent of the workflow, it takes raw user queries like 'Show me 3 undervalued tech stocks under $250' and extracts a structured intent object. This agent uses `gpt-4o-mini` to parse the plain English into a JSON-like schema. I originally tried with HuggingFace models running on local machine but they didn't work properly, I'll explain later in the Implementation section.

If the query is too vague (e.g., missing a section in this case), the agent flags for a clarification step and the system informs user accordingly.

```json
{
  "sector": "Information Technology", 
  "limit": 3, 
  "metrics": ["price", "peRatio", "pbRatio"], 
  "filters": {"price_lt": 250.0, "peRatio_lt": 25.0, "pbRatio_lt": 12.0, "freeCashFlowYield_gt": 0.05}
}
```

**3. Data Processor Agent**

This one does the heavy lifting for the system:
- Loads stock fundamental for the S&P 500 from Yahoo Finances.
- Filters stocks based on the structured intent provided by the Intent Parser Agent.
- Computes sector-level medians for all metrics to give Explainer Agent useful context.

To speed things up, this agent fetch stock data using multithreading and caches all sector data on app startup using `joblib`. So on first run it loads everything, and after that it's fast — no waiting on user input or hitting APIs unnecessarily (also helps with rate limits).

**4. Explainer Agent**

This final agent generates the response that goes back to the user. It takes:
- The user’s original query
- The top matching stocks
- Sector-level metrics for comparison

It then uses `gpt-4o-mini` again to produce a friendly, markdown-formatted explanation, including a comparison table that shows why each stock was picked.

**5. Orchestration Layer**

LangChain’s RunnableSequence is used to link the agents in order. If the intent parser detects a missing key (e.g., no sector specified), it flags a `clarification_needed`, the flow branches to a `short-circuit` return and prompts the user.

Each query is processed independently — the system is stateless by design. The app maintain minimal session state (e.g., remembering the previous query context) to infer the meaning of follow-up questions like “How about energy stocks?”.

**6. Backend & Frontend Stack**

- FastAPI: REST API endpoint for handling user queries and orchestrating agents
- Streamlit: Lightweight frontend with a chat-like UI. Good for prototyping, no need React or Next.js here.
- Joblib / ThreadPoolExecutor: Used for parallel data fetching and caching at startup, ensures we don’t hit APIs more than necessary. The query of getting all stock data get cached, so the second time around is always faster.
- LangChain + OpenAI: For all LLM-based reasoning and generation

This architecture is built to simulate a real-world intelligent assistant — not just a chatbot wrapper. You can add agents for sentiment analysis, ESG filtering, earnings call summaries, or even connect to order-routing APIs. The foundation is here — modular, explainable, and production-aware.

