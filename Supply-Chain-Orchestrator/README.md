# Supply Chain Orchestration using Multi-Agent System

## Agents
### 1. The Weather Agent

- Primary Role: External Signal Monitoring and Quantification.
- Responsibilities:
  - Calls the OpenWeatherMap API (free tier is sufficient for a demo) to get the 8-day forecast for Atlanta.
  - Extracts key features from the forecast: maximum daily temperature, humidity, precipitation probability, and "feels like" temperature.
  - Translates weather data into a "Demand Adjustment Factor." (e.g., 95°F + high humidity = 1.8x baseline demand | 75°F + rain = 0.6x baseline demand). This translation can be a simple rule-based function for the demo.

### 2. The Data Analyst Agent

- Primary Role: Internal Historical Analysis and Baseline Forecasting.
- Responsibilities:
  - Queries the PostgreSQL database to analyze historical sales data.
  - Uses a simple time-series forecasting model (Exponential Smoothing) to generate a baseline 8-day demand forecast based purely on historical trends and seasonality.
- Provides current inventory levels and suppliers lead times/MOQs to other agents.

### 3. The Supply Chain Commander Agent

- Primary Role: Decision-Making and Optimization.
- Responsibilities:
  - This is where the LLM shines. It receives inputs from all other agents:
    - Baseline Forecast (from Data Analyst)
    - Demand Adjustment Factors (from Weather)
    - Current Inventory (from Data Analyst)
    - Supplier Lead Times & MOQs (from Data Analyst)
  - Performs "What-If" Analysis: The LLM is prompted to reason about the combined data. (e.g., "The baseline forecast is for 500 units, but with the heatwave, we should adjust to 900 units. We have 200 units in stock. Supplier 'The best Choco' has a 5-day lead time and a MOQ of 500. Therefore, to meet anticipated demand in 10 days, I recommend ordering 700 units now to cover the deficit and meet the MOQ.").
  - Outputs a final recommended order quantity for each key ingredient/supply (e.g., milk, sugar, cones) or finished product.

### 4. The Reporting & Communications Agent

- Primary Role: Synthesis and Storytelling.
- Responsibilities:
  - Takes the final recommendations and all supporting data.
  - Generate a polished PDF report.
  - Uses the LLM to write a concise natural language executive summary explaining the "why" behind the numbers.
  - Produces clear visualizations: charts showing the baseline vs. weather-adjusted forecast, an inventory burn-down chart, and a summary of recommended actions.


## Implementation

### Phase 1: Foundation & Data Setup (Pre-Agent Work)
1. Set Up Your PostgreSQL Database:
- Create the three tables with realistic columns.
- sales: id, date, product_id, quantity, region (optional)
- inventory: id, product_id, current_stock, last_updated
- suppliers: id, supplier_name, product_id, lead_time_days, min_order_quantity, cost_per_unit

2. Generate Synthetic Historical Data:
- Write a Python script using pandas and numpy to create 2-3 years of sales data. Crucially, inject a strong seasonal pattern (summer spikes) and some random noise. This realistic data is key.

3. Build a Simple Forecasting Function:
- Create a standalone function
- Use a simple model like Exponential Smoothing or SARIMA from the statsmodels library. Its job is to return a predicted demand for the next 8 days based only on history.

4. Set Up the Weather API:
- Create a free account on OpenWeatherMap.
- Write a simple function that calls their API, fetches the 8-day forecast for Atlanta, and returns the cleaned data (max temp, humidity, etc.).


### Phase 2: Define the Core Logic & Tools
5. Define Your "State":

- This is the central concept in LangGraph. Define a Pydantic model that represents the shared state of your workflow.

6. Create Your "Tools":

- Wrap the functions from Phase 1 into LangChain tools. These will be the capabilities your agents can use.
- QueryDatabaseTool: Gets inventory and supplier info.
- GetForecastTool: Calls your forecasting function.
- GetWeatherTool: Calls your weather API function.
- CalculateDemandFactorTool: Contains your logic (e.g., if temp > 90 and high humid: return 1.8).

- Key features:
  - Type Safety: Pydantic models for data validation
  - Summary Statistics: Provides useful aggregates for LLM consumption

### Phase 3: Build the Graph in LangGraph
7. Define the Graph Nodes:

- Each node is a function that takes the State and returns an updated State.
- Node 1: Data Analyst Node: Uses QueryDatabaseTool and GetForecastTool to populate current_inventory and baseline_forecast.
- Node 2: Weather Node: Uses GetWeatherTool and CalculateDemandFactorTool to populate weather_data and demand_adjustment_factor.
- Node 3: Supply Chain Commander Node: This is an LLM-powered node. The key is to construct a powerful prompt that provides the values from the state (forecast, inventory, weather, adjustment factor) and instructs the LLM to reason about the final recommended_order.
- Node 4: Reporting Node: Another LLM-powered node. Its prompt takes the entire state and asks the LLM to generate a concise executive_summary explaining the week's situation and the reasoning behind the order.

8. Define the Graph Edges:

- This is where you wire the nodes together. Your graph will likely be linear:
- Data Analyst Node -> Weather Node -> Supply Chain Commander Node -> Reporting Node -> END
- You can use LangGraph's conditional edges to add error handling (e.g., if inventory is zero, take a different path).

### Phase 4: Build the UI & Finalize (LangFlow)
9. Build a Simple Application Interface:

- You don't need a fancy front-end. A simple Streamlit is perfect.
- The app can have one button: "Generate Weekly Report". Clicking it runs the LangGraph workflow and displays the final output: the recommended_order and the executive_summary. You can also plot the forecast charts here.
