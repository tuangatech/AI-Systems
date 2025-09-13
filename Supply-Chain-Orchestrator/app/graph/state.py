from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ProductInfo(BaseModel):
    """Information about a specific product"""
    product_id: str = Field(..., description="Unique identifier for the product")  # ... = required
    product_name: Optional[str] = Field(None, description="Human-readable product name")
    current_inventory: int = Field(0, description="Current units in stock")
    reorder_point: int = Field(0, description="Inventory level that triggers reordering")
    supplier_id: Optional[str] = Field(None, description="Primary supplier ID")

class WeatherData(BaseModel):
    """Detailed weather forecast data for a single day"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    day_of_week: str = Field(..., description="Day of the week")
    max_temp_f: float = Field(..., description="Maximum temperature in Fahrenheit")
    humidity: int = Field(..., description="Humidity percentage")
    precipitation_probability: int = Field(..., description="Chance of precipitation (0-100)")
    weather_condition: str = Field(..., description="General weather condition")
    demand_factor: float = Field(..., description="Demand multiplier based on weather")

class ForecastResult(BaseModel):
    """Baseline demand forecast from historical data"""
    product_id: str = Field(..., description="Product being forecasted")
    success: bool = Field(..., description="Whether forecast was successful")
    forecast: List[Dict[str, Any]] = Field(default_factory=list, description="Daily forecast predictions")
    total_predicted_demand: float = Field(0.0, description="Sum of forecasted demand")
    model_used: str = Field("exponential_smoothing", description="Forecasting model used")

class SupplierInfo(BaseModel):
    """Supplier information and constraints"""
    supplier_id: str = Field(..., description="Unique supplier identifier")
    lead_time_days: int = Field(..., description="Days required for delivery")
    min_order_quantity: int = Field(..., description="Minimum order quantity required")
    cost_per_unit: float = Field(..., description="Cost per unit from this supplier")
    reliability_score: float = Field(1.0, description="Supplier reliability rating (0.0-1.0)")

class Recommendation(BaseModel):
    """Final ordering recommendation"""
    product_id: str = Field(..., description="Product being recommended")
    supplier_id: str = Field(..., description="Recommended supplier")
    order_quantity: int = Field(..., description="Units to order")
    expected_delivery_date: str = Field(..., description="Expected delivery date")
    total_cost: float = Field(..., description="Total cost of order")
    justification: str = Field(..., description="Reasoning behind the recommendation")
    confidence_score: float = Field(1.0, description="Confidence in recommendation (0.0-1.0)")

class AgentState(BaseModel):
    """
    The central state object that flows through the Meltaway supply chain workflow.
    This state is updated by each agent in the sequence.
    """
    # Input parameters
    product_id: str = Field(..., description="Target product ID for analysis")
    forecast_days: int = Field(14, description="Number of days to forecast")
    
    # Data collection phase
    product_info: Optional[ProductInfo] = Field(None, description="Product metadata and current inventory")  # Optional, default None
    supplier_info: Optional[SupplierInfo] = Field(None, description="Supplier constraints and details")
    historical_sales_data: List[Dict] = Field(default_factory=list, description="Raw historical sales data")  # default value is a new empty list []
    
    # Analysis phase
    baseline_forecast: Optional[ForecastResult] = Field(None, description="Baseline statistical forecast")
    weather_forecast: List[WeatherData] = Field(default_factory=list, description="Weather forecast data")
    average_demand_factor: float = Field(1.0, description="Average weather-based demand multiplier")
    adjusted_forecast: List[Dict] = Field(default_factory=list, description="Weather-adjusted demand forecast")
    
    # Decision phase
    recommendation: Optional[Recommendation] = Field(None, description="Final ordering recommendation")
    alternatives: List[Recommendation] = Field(default_factory=list, description="Alternative recommendations considered")
    
    # Output phase
    executive_summary: str = Field("", description="Natural language summary for executives")
    report_data: Dict[str, Any] = Field(default_factory=dict, description="Data for PDF report generation")
    
    # Metadata
    current_step: str = Field("initialized", description="Current processing step")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered during processing")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Processing start time")
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True
        validate_assignment = True

# Helper function to create initial state
def create_initial_state(product_id: str, forecast_days: int = 8) -> AgentState:
    """Create a new state object with initial values"""
    return AgentState(
        product_id=product_id,
        forecast_days=forecast_days,
        current_step="initialized",
        timestamp=datetime.now().isoformat()
    )