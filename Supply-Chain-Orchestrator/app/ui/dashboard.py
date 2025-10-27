import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import asyncio
from app.graph.workflow import supply_chain_workflow
from app.graph.state import create_initial_state
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set page config
st.set_page_config(
    page_title="Meltaway Supply Chain Orchestrator",
    # layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid #4CAF50;
        margin: 1rem 0;
    }
    .recommendation-box {
        background-color: #f0f8f0;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #4CAF50;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class SupplyChainDashboard:
    def __init__(self):
        self.products = ["vanilla", "chocolate"]  # Simplify to two products
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main UI layout"""
        # Header
        st.markdown('<h1 class="main-header">Meltaway Supply Chain Orchestrator</h1>', unsafe_allow_html=True)
        
        # Sidebar for controls
        with st.sidebar:
            st.header("Configuration")
            self.selected_product = st.selectbox(
                "Select Product",
                self.products,
                help="Choose which product to analyze"
            )
            self.forecast_days = st.slider(
                "Forecast Days",
                min_value=3,
                max_value=14,
                value=7,
                help="Number of days to forecast demand"
            )
            
            if st.button("🚀 Generate Recommendation", type="primary", width='stretch'):
                self.generate_recommendation()
            
            st.divider()
            st.info("💡 This system analyzes historical sales, weather data, and inventory levels to generate optimal ordering recommendations.")
        
        # Main content area
        # col1, col2 = st.columns([1, 1])
        
        # with col1:
        # self.show_sales_history()
        
        self.show_recommendation_result()
        if hasattr(self, 'final_state'):
            self.show_forecast_charts()
    
    def show_sales_history(self):
        # print("Showing sales history", self.agent_state.historical_sales_data)
        if self.agent_state.historical_sales_data:
            sales_data = self.agent_state.historical_sales_data

            st.subheader(f"📊 Sales History (Last 14 Days)") # {self.agent_state.forecast_days}
            
            df_sales = pd.DataFrame(sales_data)
            df_sales["date"] = pd.to_datetime(df_sales["date"]).dt.strftime('%Y-%m-%d')
            df_sales.drop(columns=['region'], inplace=True)
            
            # Show sales trend chart
            fig = px.line(
                df_sales,  
                x="date",  
                y="quantity", 
                color="product_code",
                # title=f"Sales Trend (Last {self.agent_state.forecast_days} Days)",
                markers=True
            )
            st.plotly_chart(fig, width='stretch')
 
    
    def generate_recommendation(self):
        """Generate supply chain recommendation"""
        with st.spinner("Analyzing data and generating recommendation..."):
            try:
                # Run the workflow
                initial_state = create_initial_state(self.selected_product, self.forecast_days)
                self.final_state = supply_chain_workflow.invoke(initial_state)
                
                # Convert to AgentState for easy access
                from app.graph.state import AgentState
                self.agent_state = AgentState(**self.final_state)
                
                st.success("✅ Recommendation generated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error generating recommendation: {str(e)}")
                st.exception(e)
    
    def show_recommendation_result(self):
        
        if not hasattr(self, 'agent_state'):
            st.info("👆 Click 'Generate Recommendation' to get started")
            return
        
        self.show_sales_history()

        st.subheader("🎯 Supply Chain Recommendation")

        if self.agent_state.recommendation:
            rec = self.agent_state.recommendation
            
            # Use st.container with custom CSS class
            with st.container():
                # st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Recommended Order", f"{rec.order_quantity:,} units")
                    st.metric("Supplier", rec.supplier_name)
                
                with col2: 
                    st.metric("Confidence Level", f"{rec.confidence_score:.0%}")
                    st.metric("Expected Impact", "High" if rec.confidence_score > 0.7 else "Medium")
                
                st.write("**Justification:**")
                st.write(rec.justification)
                
                # st.markdown('</div>', unsafe_allow_html=True)
        
        # Show executive summary
        if self.agent_state.executive_summary:
            st.subheader("📋 Executive Summary")
            st.write(self.agent_state.executive_summary)
    
    def show_forecast_charts(self):
        """Display forecast visualization"""
        if not hasattr(self, 'agent_state') or not self.agent_state.baseline_forecast:
            return
        
        st.subheader("📈 Demand Forecast")
        
        # Prepare forecast data
        forecast_data = self.agent_state.baseline_forecast.forecast
        baseline = [item['predicted_demand'] for item in forecast_data]
        baseline_by_date = {item['date']: item['predicted_demand'] for item in forecast_data}

        # Extract weather demand factors by date
        weather_by_date = {
            item.date: item.demand_factor 
            for item in self.agent_state.weather_forecast
        }

        dates = [item['date'] for item in forecast_data]
        
        # Calculate adjusted demand: predicted_demand * corresponding demand_factor
        adjusted = [
            baseline_by_date[date] * weather_by_date.get(date, 1.0)  # Use 1.0 if no weather factor found
            for date in dates
        ]
        
        # Create forecast comparison chart
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        fig.add_trace(
            go.Scatter(x=dates, y=baseline, name="Baseline Forecast", line=dict(color='blue')),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=adjusted, name="Weather-Adjusted Forecast", line=dict(color='red')),
            secondary_y=False,
        )
        
        fig.update_layout(
            title="Demand Forecast Comparison",
            xaxis_title="Date",
            yaxis_title="Units",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, width='stretch')
        
        # Show weather impact
        st.metric("Weather Impact Factor", f"{self.agent_state.average_demand_factor:.2f}x")
        
        if self.agent_state.average_demand_factor > 1.2:
            st.warning("🌡️ High weather impact expected - increased demand likely")
        elif self.agent_state.average_demand_factor < 0.8:
            st.info("🌧️ Low weather impact expected - reduced demand likely")

def main():
    """Main function to run the dashboard"""
    try:
        dashboard = SupplyChainDashboard()
    except Exception as e:
        st.error(f"Failed to initialize dashboard: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()