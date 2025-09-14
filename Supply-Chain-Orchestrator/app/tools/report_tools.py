import os
from typing import Dict, Any, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import json
import logging
import tempfile
import io
from dotenv import load_dotenv
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Load environment variables from .env file
load_dotenv()   # .env is at the project root
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini-2024-07-18")

# Initialize LLM
llm = ChatOpenAI(
    temperature=0.1, 
    model=GPT_MODEL,
    openai_api_key=OPENAI_API_KEY
)

@tool
def generate_executive_summary(state: Dict[str, Any]) -> str:
    """
    Generates a concise executive summary based on the supply chain analysis state.
    Highlights key insights and recommendations for decision-makers.
    
    Args:
        state: The complete state object from the supply chain workflow
        
    Returns:
        String containing the executive summary
    """
    try:
        # Prepare context for LLM summary
        context = _prepare_summary_context(state)
        
        prompt = f"""
        You are an executive assistant at Meltaway Ice Cream. Create a concise, actionable 
        executive summary based on the following supply chain analysis. Focus on:
        
        1. Key findings and insights
        2. Recommended actions with justification
        3. Potential risks and opportunities
        4. Financial implications if available
        
        Write in professional business language suitable for C-level executives.
        Keep it under 300 words.
        
        ANALYSIS DATA:
        {context}
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        summary = response.content.strip()
        
        logger.info("Executive summary generated successfully")
        return summary
        
    except Exception as e:
        error_msg = f"Error generating executive summary: {str(e)}"
        logger.error(error_msg)
        return f"Executive Summary could not be generated due to an error: {str(e)}"

@tool
def create_pdf_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a comprehensive PDF report with charts, tables, and executive summary.
    
    Args:
        state: The complete state object from the supply chain workflow
        
    Returns:
        Dictionary containing report metadata and file path
    """
    try:
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Add title
        title_style = ParagraphStyle(
            'Weekly Report - Meltaway Ice Cream',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center aligned
        )
        
        story.append(Paragraph("MELTAWAY SUPPLY CHAIN OPTIMIZATION REPORT", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Add executive summary
        if state.get('executive_summary'):
            story.append(Paragraph("EXECUTIVE SUMMARY", styles['Heading2']))
            summary_text = state['executive_summary'].replace('\n', '<br/>')
            story.append(Paragraph(summary_text, styles['BodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        # Add key metrics table
        story.append(Paragraph("KEY METRICS", styles['Heading2']))
        metrics_data = _create_metrics_table_data(state)
        metrics_table = Table(metrics_data, colWidths=[2*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Add demand forecast chart
        if state.get('baseline_forecast') and state.get('weather_forecast'):
            chart_path = _create_forecast_chart(state)
            if chart_path:
                story.append(Paragraph("DEMAND FORECAST", styles['Heading2']))
                story.append(Image(chart_path, width=6*inch, height=4*inch))
                story.append(Spacer(1, 0.2*inch))
        
        # Add recommendation details
        if state.get('recommendation'):
            story.append(Paragraph("RECOMMENDATION", styles['Heading2']))
            rec_data = _create_recommendation_table_data(state['recommendation'])
            rec_table = Table(rec_data, colWidths=[1.5*inch, 3.5*inch])
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(rec_table)
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report created at: {pdf_path}")
        
        return {
            "success": True,
            "pdf_path": pdf_path,
            "file_size": os.path.getsize(pdf_path),
            "generated_at": datetime.now().isoformat(),
            "product_code": state.get('product_code', 'unknown'),
            "report_type": "supply_chain_optimization"
        }
        
    except Exception as e:
        error_msg = f"Error creating PDF report: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "pdf_path": None
        }

def _prepare_summary_context(state: Dict[str, Any]) -> str:
    """Prepare context string for executive summary generation"""
    context_parts = []
    
    # Basic information
    context_parts.append(f"Product: {state.get('product_code', 'N/A')}")
    context_parts.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d')}")
    context_parts.append(f"Forecast Period: {state.get('forecast_days', 14)} days")
    
    # Inventory and product info
    if state.get('product_info'):
        context_parts.append(f"Current Inventory: {state['product_info'].get('current_inventory', 0)} units")
        context_parts.append(f"Reorder Point: {state['product_info'].get('reorder_point', 0)} units")
    
    # Forecast information
    if state.get('baseline_forecast'):
        baseline = state['baseline_forecast']
        context_parts.append(f"Baseline Forecast: {baseline.get('total_predicted_demand', 0):.0f} units")
    
    # Weather impact
    context_parts.append(f"Weather Demand Factor: {state.get('average_demand_factor', 1.0):.2f}x")
    
    # Adjusted forecast calculation
    if state.get('baseline_forecast') and state.get('average_demand_factor'):
        baseline_demand = state['baseline_forecast'].get('total_predicted_demand', 0)
        adjusted_demand = baseline_demand * state['average_demand_factor']
        context_parts.append(f"Adjusted Forecast: {adjusted_demand:.0f} units")
    
    # Recommendation
    if state.get('recommendation'):
        rec = state['recommendation']
        context_parts.append(f"Recommended Order: {rec.get('order_quantity', 0)} units")
        context_parts.append(f"Supplier: {rec.get('supplier_id', 'N/A')}")
        context_parts.append(f"Justification: {rec.get('justification', 'N/A')}")
        context_parts.append(f"Confidence: {rec.get('confidence_score', 0.0):.1%}")
    
    return "\n".join(context_parts)

def _create_metrics_table_data(state: Dict[str, Any]) -> List[List[str]]:
    """Create data for the key metrics table"""
    data = [
        ["Metric", "Value"]
    ]
    
    # Current inventory
    if state.get('product_info'):
        data.append(["Current Inventory", f"{state['product_info'].get('current_inventory', 0):,} units"])
        data.append(["Reorder Point", f"{state['product_info'].get('reorder_point', 0):,} units"])
    
    # Forecast metrics
    if state.get('baseline_forecast'):
        baseline = state['baseline_forecast']
        data.append(["Baseline Forecast", f"{baseline.get('total_predicted_demand', 0):,.0f} units"])
    
    # Weather impact
    data.append(["Weather Impact", f"{state.get('average_demand_factor', 1.0):.2f}x"])
    
    # Adjusted forecast
    if state.get('baseline_forecast') and state.get('average_demand_factor'):
        baseline_demand = state['baseline_forecast'].get('total_predicted_demand', 0)
        adjusted_demand = baseline_demand * state['average_demand_factor']
        data.append(["Adjusted Forecast", f"{adjusted_demand:,.0f} units"])
    
    # Inventory status
    if state.get('product_info'):
        current_inv = state['product_info'].get('current_inventory', 0)
        reorder_point = state['product_info'].get('reorder_point', 0)
        status = "Above Reorder Point" if current_inv > reorder_point else "BELOW REORDER POINT - ACTION NEEDED"
        data.append(["Inventory Status", status])
    
    return data

def _create_forecast_chart(state: Dict[str, Any]) -> str:
    """Create a forecast comparison chart and return file path"""
    try:
        if not state.get('baseline_forecast') or not state.get('weather_forecast'):
            return None
        
        # Prepare data
        baseline_forecast = state['baseline_forecast'].get('forecast', [])
        weather_data = state.get('weather_forecast', [])
        
        if not baseline_forecast or not weather_data:
            return None
        
        # Create DataFrame
        dates = [item['date'] for item in baseline_forecast]
        baseline = [item['predicted_demand'] for item in baseline_forecast]
        
        # Calculate adjusted forecast
        adjusted = []
        for i, day in enumerate(baseline_forecast):
            if i < len(weather_data):
                adjusted.append(day['predicted_demand'] * weather_data[i].get('demand_factor', 1.0))
            else:
                adjusted.append(day['predicted_demand'])
        
        # Create plot
        plt.figure(figsize=(10, 6))
        plt.plot(dates, baseline, 'b-', label='Baseline Forecast', linewidth=2)
        plt.plot(dates, adjusted, 'r-', label='Weather-Adjusted Forecast', linewidth=2)
        
        plt.title('Demand Forecast Comparison', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Units')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight')
            plt.close()
            return tmp_file.name
            
    except Exception as e:
        logger.error(f"Error creating forecast chart: {e}")
        return None

def _create_recommendation_table_data(recommendation: Dict[str, Any]) -> List[List[str]]:
    """Create data for the recommendation table"""
    data = [
        ["Field", "Value"]
    ]
    
    data.append(["Product", recommendation.get('product_code', 'N/A')])
    data.append(["Recommended Quantity", f"{recommendation.get('order_quantity', 0):,} units"])
    data.append(["Supplier", recommendation.get('supplier_id', 'N/A')])
    data.append(["Confidence Level", f"{recommendation.get('confidence_score', 0.0):.1%}"])
    data.append(["Justification", recommendation.get('justification', 'No justification provided')])
    
    return data

@tool
def generate_detailed_analysis(state: Dict[str, Any]) -> str:
    """
    Generates a detailed technical analysis report for supply chain analysts.
    Includes raw data, calculations, and methodology.
    
    Args:
        state: The complete state object
        
    Returns:
        String containing detailed analysis
    """
    try:
        context = _prepare_detailed_context(state)
        
        prompt = f"""
        You are a supply chain analyst. Create a detailed technical analysis including:
        
        1. Data sources and methodology
        2. Calculation details
        3. Assumptions and limitations
        4. Alternative scenarios considered
        5. Risk assessment
        
        Be technical and detailed. Include specific numbers and calculations.
        
        ANALYSIS DATA:
        {context}
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
        
    except Exception as e:
        return f"Error generating detailed analysis: {str(e)}"

def _prepare_detailed_context(state: Dict[str, Any]) -> str:
    """Prepare context for detailed analysis"""
    context_parts = ["DETAILED ANALYSIS DATA:"]
    
    # Add raw data excerpts
    if state.get('product_info'):
        context_parts.append(f"Product Info: {json.dumps(state['product_info'], indent=2)}")
    
    if state.get('baseline_forecast'):
        context_parts.append(f"Baseline Forecast: {json.dumps(state['baseline_forecast'], indent=2)}")
    
    if state.get('weather_forecast'):
        context_parts.append(f"Weather Data Sample: {json.dumps(state['weather_forecast'][:3], indent=2)}")
    
    return "\n".join(context_parts)

# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_state = {
        "product_code": "vanilla",
        "forecast_days": 8,
        "product_info": {
            "product_code": "vanilla",
            "product_name": "Vanilla Bean Ice Cream",
            "current_inventory": 1500,
            "reorder_point": 2000,
            "safety_stock": 500
        },
        "baseline_forecast": {
            "success": True,
            "total_predicted_demand": 4200,
            "forecast": [
                {"date": "2025-09-15", "predicted_demand": 280},
                {"date": "2025-09-16", "predicted_demand": 310}
            ]
        },
        "average_demand_factor": 1.8,
        "recommendation": {
            "product_code": "vanilla",
            "order_quantity": 5000,
            "supplier_id": "100",
            "justification": "Heatwave expected to increase demand by 80%",
            "confidence_score": 0.85
        }
    }
    
    # Test executive summary
    summary = generate_executive_summary.invoke({"state": sample_state})
    print("EXECUTIVE SUMMARY:")
    print(summary)
    print("\n" + "="*50 + "\n")
    
    # Test PDF generation
    pdf_result = create_pdf_report.invoke({"state": sample_state})
    print("PDF RESULT:", pdf_result)