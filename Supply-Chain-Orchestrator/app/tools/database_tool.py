import os
from typing import List, Dict, Optional, Any
from langchain.tools import tool
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
def get_db_engine():
    """Create and return a database engine"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return create_engine(database_url)

# Pydantic models for type safety
class ProductInfo(BaseModel):
    product_code: str = Field(..., description="Unique product code identifier")
    product_name: str = Field(..., description="Name of the product")
    category: str = Field(..., description="Product category")
    current_inventory: int = Field(0, description="Current units in stock")
    reorder_point: int = Field(0, description="Inventory level that triggers reordering")
    safety_stock: int = Field(0, description="Minimum safety stock level")
    unit_cost: float = Field(0.0, description="Cost per unit")
    selling_price: float = Field(0.0, description="Selling price per unit")

class SupplierInfo(BaseModel):
    supplier_id: str = Field(..., description="Unique supplier identifier")
    supplier_name: str = Field(..., description="Name of the supplier")
    product_code: str = Field(..., description="Product code supplied")
    lead_time_days: int = Field(..., description="Days required for delivery")
    min_order_quantity: int = Field(..., description="Minimum order quantity required")
    cost_per_unit: float = Field(..., description="Cost per unit from this supplier")
    reliability_score: float = Field(1.0, description="Supplier reliability rating (0.0-1.0)")

class SalesData(BaseModel):
    date: str = Field(..., description="Sale date in YYYY-MM-DD format")
    product_code: str = Field(..., description="Product code sold")
    quantity: int = Field(..., description="Number of units sold")
    region: Optional[str] = Field(None, description="Sales region if available")

@tool
def get_product_info(product_code: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific product including current inventory levels.
    
    Args:
        product_code: The unique code identifying the product (e.g., 'IC-VAN-001')
        
    Returns:
        Dictionary containing product information and inventory data
    """
    try:
        engine = get_db_engine()
        query = text("""
            SELECT 
                p.product_code,
                p.product_name,
                p.category,
                p.unit_cost,
                p.selling_price,
                COALESCE(i.current_stock, 0) as current_inventory,
                COALESCE(i.reorder_point, 0) as reorder_point,
                COALESCE(i.safety_stock, 0) as safety_stock
            FROM products p
            LEFT JOIN inventory i ON p.product_code = i.product_code
            WHERE p.product_code = :product_code
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"product_code": product_code})
            row = result.mappings().first()
            
        if not row:
            return {
                "success": False,
                "error": f"Product with code {product_code} not found",
                "product_code": product_code
            }
        
        product_info = dict(row)
        product_info["success"] = True
        
        logger.info(f"Retrieved product info for {product_code}: {product_info['current_inventory']} units in stock")
        return product_info
        
    except Exception as e:
        error_msg = f"Error retrieving product info for {product_code}: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "product_code": product_code}

@tool
def get_supplier_info(product_code: str) -> List[Dict[str, Any]]:
    """
    Retrieves supplier information for a specific product including lead times and order constraints.
    
    Args:
        product_code: The unique code identifying the product
        
    Returns:
        List of dictionaries containing supplier information
    """
    try:
        engine = get_db_engine()
        query = text("""
            SELECT 
                s.supplier_id,
                s.supplier_name,
                sp.product_code,
                sp.lead_time_days,
                sp.min_order_quantity,
                sp.cost_per_unit,
                sp.reliability_score
            FROM suppliers s
            JOIN supplier_products sp ON s.supplier_id = sp.supplier_id
            WHERE sp.product_code = :product_code
            ORDER BY sp.cost_per_unit ASC, sp.lead_time_days ASC
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"product_code": product_code})
            suppliers = [dict(row) for row in result.mappings().all()]
            
        if not suppliers:
            return {
                "success": False,
                "error": f"No suppliers found for product {product_code}",
                "product_code": product_code,
                "suppliers": []
            }
        
        logger.info(f"Retrieved {len(suppliers)} suppliers for product {product_code}")
        return {
            "success": True,
            "product_code": product_code,
            "suppliers": suppliers
        }
        
    except Exception as e:
        error_msg = f"Error retrieving suppliers for {product_code}: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "product_code": product_code}

@tool
def get_historical_sales(product_code: str, days: int = 730) -> Dict[str, Any]:
    """
    Retrieves historical sales data for a product for forecasting purposes.
    
    Args:
        product_code: The unique code identifying the product
        days: Number of days of historical data to retrieve (default: 730 = 2 years)
        
    Returns:
        Dictionary containing historical sales data and summary statistics
    """
    try:
        engine = get_db_engine()
        query = text("""
            SELECT 
                date,
                product_code,
                quantity,
                region
            FROM sales 
            WHERE product_code = :product_code 
            AND date >= CURRENT_DATE - INTERVAL ':days days'
            ORDER BY date ASC
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"product_code": product_code, "days": days})
            sales_data = [dict(row) for row in result.mappings().all()]
            
        if not sales_data:
            return {
                "success": False,
                "error": f"No sales data found for product {product_code} in last {days} days",
                "product_code": product_code,
                "sales_data": [],
                "summary": {}
            }
        
        # Calculate summary statistics
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date'])
        
        summary = {
            "total_period_days": days,
            "total_sales_units": int(df['quantity'].sum()),
            "average_daily_sales": round(df['quantity'].mean(), 2),
            "max_daily_sales": int(df['quantity'].max()),
            "min_daily_sales": int(df['quantity'].min()),
            "sales_start_date": df['date'].min().strftime('%Y-%m-%d'),
            "sales_end_date": df['date'].max().strftime('%Y-%m-%d'),
            "total_sales_days": len(df['date'].unique())
        }
        
        logger.info(f"Retrieved {len(sales_data)} sales records for {product_code}, total {summary['total_sales_units']} units")
        
        return {
            "success": True,
            "product_code": product_code,
            "sales_data": sales_data,
            "summary": summary
        }
        
    except Exception as e:
        error_msg = f"Error retrieving sales data for {product_code}: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "product_code": product_code}

@tool
def get_current_inventory(product_code: str) -> Dict[str, Any]:
    """
    Gets the current inventory level for a specific product.
    
    Args:
        product_code: The unique code identifying the product
        
    Returns:
        Dictionary containing current inventory information
    """
    try:
        engine = get_db_engine()
        query = text("""
            SELECT 
                product_code,
                current_stock as current_inventory,
                reorder_point,
                safety_stock,
                last_updated
            FROM inventory 
            WHERE product_code = :product_code
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"product_code": product_code})
            row = result.mappings().first()
            
        if not row:
            return {
                "success": False,
                "error": f"No inventory record found for product {product_code}",
                "product_code": product_code,
                "current_inventory": 0
            }
        
        inventory_data = dict(row)
        inventory_data["success"] = True
        
        logger.info(f"Current inventory for {product_code}: {inventory_data['current_inventory']} units")
        return inventory_data
        
    except Exception as e:
        error_msg = f"Error retrieving inventory for {product_code}: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "product_code": product_code, "current_inventory": 0}

@tool
def get_low_inventory_products(threshold: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all products with inventory levels below their reorder point.
    
    Args:
        threshold: Optional custom threshold (if not provided, uses product's reorder_point)
        
    Returns:
        List of products needing reordering
    """
    try:
        engine = get_db_engine()
        
        if threshold:
            query = text("""
                SELECT 
                    i.product_code,
                    p.product_name,
                    i.current_stock as current_inventory,
                    i.reorder_point,
                    i.safety_stock,
                    i.last_updated
                FROM inventory i
                JOIN products p ON i.product_code = p.product_code
                WHERE i.current_stock <= :threshold
                ORDER BY i.current_stock ASC
            """)
            params = {"threshold": threshold}
        else:
            query = text("""
                SELECT 
                    i.product_code,
                    p.product_name,
                    i.current_stock as current_inventory,
                    i.reorder_point,
                    i.safety_stock,
                    i.last_updated
                FROM inventory i
                JOIN products p ON i.product_code = p.product_code
                WHERE i.current_stock <= i.reorder_point
                ORDER BY i.current_stock ASC
            """)
            params = {}
        
        with engine.connect() as conn:
            result = conn.execute(query, params)
            low_inventory_products = [dict(row) for row in result.mappings().all()]
            
        logger.info(f"Found {len(low_inventory_products)} products with low inventory")
        return {
            "success": True,
            "low_inventory_products": low_inventory_products,
            "threshold_used": threshold if threshold else "reorder_point"
        }
        
    except Exception as e:
        error_msg = f"Error retrieving low inventory products: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "low_inventory_products": []}

# Example usage
if __name__ == "__main__":
    # Test the tools
    try:
        # Test product info
        product_info = get_product_info.invoke({"product_code": "vanilla"})
        print("Product Info:", product_info)
        
        print("\n" + "="*50 + "\n")
        
        # Test supplier info
        supplier_info = get_supplier_info.invoke({"product_code": "vanilla"})
        print("Supplier Info:", supplier_info)
        
        print("\n" + "="*50 + "\n")
        
        # Test sales data
        sales_data = get_historical_sales.invoke({"product_code": "vanilla", "days": 10})
        print("Sales Data Summary:", sales_data.get('summary', {}))
        
    except Exception as e:
        print(f"Error testing database tools: {e}")