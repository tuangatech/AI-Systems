import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

# ==============================
# Configuration
# ==============================
END_DATE = datetime.today()  # Today
START_DATE = END_DATE - timedelta(days=2*365)  # Approx. 2 years ago
PRODUCTS = ["vanila", "chocolate"]  # Product IDs
BASE_SALES = {PRODUCTS[0]: 50, PRODUCTS[1]: 100}  # Base average daily sales
SEASONALITY_FACTOR = {
    # Month: multiplier (e.g., 1.0 = base, 1.4 = 40% increase)
    1: 0.7,   # Jan - winter drop
    2: 0.6,   # Feb - winter drop
    3: 0.9,   # Mar
    4: 1.0,   # Apr
    5: 1.2,   # May - ramp up
    6: 1.5,   # Jun - summer spike
    7: 1.6,   # Jul - peak
    8: 1.5,   # Aug - summer spike
    9: 1.1,   # Sep - tapering
    10: 1.0,  # Oct
    11: 0.9,  # Nov
    12: 0.7   # Dec - winter drop
}
NOISE_SCALE = 10  # Standard deviation of random noise

# Load environment variable (DATABASE_URL in .env)
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

engine = create_engine(DB_URL)

def create_tables():
    """Create the required tables if they don't exist."""
    with engine.connect() as conn:
        # Drop existing tables for a clean setup
        conn.execute(text("DROP TABLE IF EXISTS suppliers, inventory, sales CASCADE;"))
        conn.commit()

        # Create sales table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                product_code VARCHAR(50) NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0)
            );
        """))

        # Create inventory table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                product_code VARCHAR(50) PRIMARY KEY,
                current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
                reorder_point INTEGER NOT NULL CHECK (reorder_point >= 0)
            );
        """))

        # Create suppliers table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY,
                product_code VARCHAR(50) NOT NULL,
                lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
                min_order_quantity INTEGER NOT NULL CHECK (min_order_quantity > 0),
                cost_per_unit NUMERIC(10, 2) NOT NULL CHECK (cost_per_unit >= 0),
                FOREIGN KEY (product_code) REFERENCES inventory (product_code)
            );
        """))

        conn.commit()
    print("3 Tables created successfully.")

def generate_sales_data():
    # Generate Date Range
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq='D')

    print(f"Generating sales data from {START_DATE.date()} to {END_DATE.date()}")

    # Create DataFrame with all combinations of date and product
    data = []
    for date in dates:
        for product_code in PRODUCTS:
            base = BASE_SALES[product_code]
            month = date.month
            seasonal_multiplier = SEASONALITY_FACTOR[month]
            
            # Apply seasonality and add noise
            expected_sales = base * seasonal_multiplier
            noise = np.random.normal(loc=0, scale=NOISE_SCALE)
            quantity = max(1, int(round(expected_sales + noise)))  # Ensure at least 1
            
            data.append({
                'date': date,
                'product_code': product_code,
                'quantity': quantity
            })

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} sales records.")
    return df


def visualize_seasonality(df):
    df_plot = df.groupby(['date', 'product_code'])['quantity'].sum().unstack()
    df_plot.plot(title='Daily Sales Over Time', figsize=(12, 6))
    plt.ylabel('Quantity Sold')
    plt.savefig('sales_seasonality.png')


def insert_sales_data():
    df = generate_sales_data()
    try:
        # create PostgreSQL engine
        engine = create_engine(DB_URL)
        
        # Write to PostgreSQL
        df.to_sql('sales', engine, if_exists='append', index=False, method='multi')
        print("Data successfully inserted into PostgreSQL 'sales' table.")

        visualize_seasonality(df)

    except Exception as e:
        print("Error inserting data:", e)


def insert_sample_data():
    """Insert 2-3 sample records into each table."""
    with engine.connect() as conn:
        # Insert into sales
        insert_sales_data()

        # Insert into inventory
        inventory_data = [
            {'product_code': PRODUCTS[0], 'current_stock': 100, 'reorder_point': 30},
            {'product_code': PRODUCTS[1], 'current_stock': 45,  'reorder_point': 20},
            # {'product_code': 3, 'current_stock': 10,  'reorder_point': 15},  # needs reorder
        ]
        conn.execute(text("""
            INSERT INTO inventory (product_code, current_stock, reorder_point)
            VALUES (:product_code, :current_stock, :reorder_point)
            ON CONFLICT (product_code) DO NOTHING;
        """), inventory_data)

        # Insert into suppliers
        suppliers_data = [
            {'supplier_id': 101, 'product_code': PRODUCTS[0], 'lead_time_days': 5, 'min_order_quantity': 50, 'cost_per_unit': 9.99},
            {'supplier_id': 102, 'product_code': PRODUCTS[1], 'lead_time_days': 7, 'min_order_quantity': 30, 'cost_per_unit': 14.50},
            # {'supplier_id': 103, 'product_code': 3, 'lead_time_days': 4, 'min_order_quantity': 40, 'cost_per_unit': 19.99},
        ]
        conn.execute(text("""
            INSERT INTO suppliers (supplier_id, product_code, lead_time_days, min_order_quantity, cost_per_unit)
            VALUES (:supplier_id, :product_code, :lead_time_days, :min_order_quantity, :cost_per_unit)
            ON CONFLICT (supplier_id) DO NOTHING;
        """), suppliers_data)

        conn.commit()
    print("Sample data inserted to 3 tables.")

if __name__ == "__main__":
    print("🚀 Setting up database...")
    create_tables()
    insert_sample_data()
    print("🎉 Database setup complete!")