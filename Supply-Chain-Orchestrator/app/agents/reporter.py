from app.graph.state import AgentState
from app.tools.report_tools import generate_executive_summary, create_pdf_report
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def reporter_agent(state: AgentState) -> Dict[str, Any]:
    """
    Reporter Agent: Generates executive summary and PDF report.
    """
    logger.info("Reporter generating executive report")
    
    updates = {}
    
    try:
        # Generate executive summary
        summary = generate_executive_summary.invoke({"state": state.model_dump()})
        updates["executive_summary"] = summary
        
        # Create PDF report
        report_data = create_pdf_report.invoke({"state": state.model_dump()})
        updates["report_data"] = report_data
        
        updates["current_step"] = "report_complete"
        updates["errors"] = state.errors
        
    except Exception as e:
        error_msg = f"Reporter error: {str(e)}"
        logger.error(error_msg)
        updates["errors"] = state.errors + [error_msg]
    
    return updates  # state.copy(update=updates)