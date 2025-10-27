# Supply Chain Orchestration using Multi-Agent System

A multi-agent AI system that automates supply chain decision-making for businesses facing demand volatility. Built with LangGraph, this system coordinates specialized agents to transform raw data into actionable procurement recommendations.

## What Problem Does This Solve?

Traditional ERP systems show what happened in the past, but can't predict what to do next. This system helps businesses like ice cream companies navigate demand spikes from heatwaves or drops from cold weather by providing data-driven production and ordering decisions.

## Agent Team

- **Data Analyst**: Analyzes historical sales, inventory levels, and generates baseline forecasts
- **Weather Forecaster**: Predicts demand impact based on weather conditions and forecasts
- **Supply Chain Commander**: Makes procurement decisions using business rules and LLM reasoning
- **Reporter**: Generates executive summaries and justification for recommendations

## Tech Stack

- **LangGraph** for agent orchestration and state management
- **LLMs** for complex decision-making and natural language reporting
- **Python** with custom tools for data access and external APIs
- **unittest** with comprehensive mocking for reliable testing

## Key Features

- Real-time demand prediction using weather data
- Automated procurement recommendations
- Multi-agent collaboration with shared state
- Comprehensive testing strategy (unit, integration, workflow)
- Executive-level reporting with decision justification

## Example Output

- Product: vanilla
- Analysis Date: 2025-10-26
- Forecast Period: 4 days
- Current Inventory: 470 units
- Reorder Point: 600 units
- Baseline Forecast: 407 units
- Weather Demand Factor: 0.42x
- Adjusted Forecast: 171 units
- Recommended Order: 300 units
- Supplier: Atlanta IceSup
- Justification: Projected demand over the next 4 days is 170.94 units (407.0 * 0.42), which is less than the current inventory of 470 units. However, since the reorder point is 600 units and we need to account for the 5-day lead time, ordering the minimum quantity of 300 units ensures we will not run out of stock before the next order arrives.
- Confidence: 85.0%

## Database
- superuser (postgres): admin555
- port: 5432

## Getting Started

- Create a sample database with `db_setup.py` before running the solution.
- Set Up the Weather API: Create a free account on OpenWeatherMap.

```bash
cd project-root/        
source .venv/Scripts/activate
python database/db_setup.py
python -m app.tools.forecast_tools
python -m app.test.test_workflow

streamlit run app/ui/dashboard.py
```

## 📊 Testing Strategy

Comprehensive test coverage including:
- Unit tests for individual tools
- Integration tests for agents with mocked dependencies 
- End-to-end workflow validation

---

*Built to demonstrate how multi-agent AI systems can solve real-world business problems beyond typical chatbot applications.*