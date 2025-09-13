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
START_DATE = END_DATE - timedelta(days=2*365)  # 2*365 Approx. 2 years ago
PRODUCTS = ["vanilla", "chocolate"]  # Product codes
PRODUCT_NAMES = ["Vanilla Ice Cream", "Chocolate Ice Cream"]
BASE_SALES = {PRODUCTS[0]: 100, PRODUCTS[1]: 50}  # Base average daily sales
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
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(database_url)

def create_tables():
    """Create the required tables if they don't exist."""
    with engine.connect() as conn:
        # Drop existing tables for a clean setup
        conn.execute(text("DROP TABLE IF EXISTS sales, inventory, supplier_products, products, suppliers CASCADE;"))
        conn.commit()

        # Create products table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                product_code VARCHAR(50) PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(50),
                unit_cost DECIMAL(10,2),
                selling_price DECIMAL(10,2),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create inventory table
        # safety_stock: Minimum buffer stock to prevent stockouts
        # reorder_point: Inventory level that triggers a reorder = Safety Stock + (Average Daily Demand × Lead Time in Days)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                product_code VARCHAR(50) PRIMARY KEY REFERENCES products(product_code),
                current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
                reorder_point INTEGER NOT NULL CHECK (reorder_point >= 0),
                safety_stock INTEGER NOT NULL CHECK (safety_stock >= 0),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create suppliers table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY,
                supplier_name VARCHAR(100) NOT NULL,
                contact_info TEXT
            );
        """))

        # Create supplier_products table (junction table)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS supplier_products (
                supplier_id INTEGER REFERENCES suppliers(supplier_id),
                product_code VARCHAR(50) REFERENCES products(product_code),
                lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
                min_order_quantity INTEGER NOT NULL CHECK (min_order_quantity > 0),
                cost_per_unit NUMERIC(10, 2) NOT NULL CHECK (cost_per_unit >= 0),
                reliability_score DECIMAL(3,2) DEFAULT 1.0,
                PRIMARY KEY (supplier_id, product_code)
            );
        """))

        # Create sales table - cannot insert data with "REFERENCES products(product_code)" (?)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                product_code VARCHAR(50),
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                region VARCHAR(50),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.commit()
    print("5 Tables created successfully.")

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
        engine = create_engine(database_url)
        
        # Write to PostgreSQL
        df.to_sql('sales', engine, if_exists='append', index=False, method='multi')
        print("Data successfully inserted into PostgreSQL 'sales' table.")

        visualize_seasonality(df)

    except Exception as e:
        print("Error inserting data:", e)


def insert_sample_data():
    """Insert 2-3 sample records into each table."""
    with engine.connect() as conn:
        # Insert into products
        product_data = [
            {'product_code': PRODUCTS[0], 'product_name': PRODUCT_NAMES[0], 'category': 'IceCream', 'unit_cost': 2.0, 'selling_price': 3.0},
            {'product_code': PRODUCTS[1], 'product_name': PRODUCT_NAMES[1], 'category': 'IceCream', 'unit_cost': 2.2,  'selling_price': 3.5}
        ]
        conn.execute(text("""
            INSERT INTO products (product_code, product_name, category, unit_cost, selling_price)
            VALUES (:product_code, :product_name, :category, :unit_cost, :selling_price)
            ON CONFLICT (product_code) DO NOTHING;
        """), product_data)

        # Insert into inventory
        # safety_stock: Minimum buffer stock to prevent stockouts
        # reorder_point: Inventory level that triggers a reorder = Safety Stock + (Average Daily Demand × Lead Time in Days)
        inventory_data = [
            {'product_code': PRODUCTS[0], 'current_stock': 470, 'reorder_point': 600, 'safety_stock': 100},
            {'product_code': PRODUCTS[1], 'current_stock': 510, 'reorder_point': 400, 'safety_stock': 50},
        ]
        conn.execute(text("""
            INSERT INTO inventory (product_code, current_stock, reorder_point, safety_stock)
            VALUES (:product_code, :current_stock, :reorder_point, :safety_stock)
            ON CONFLICT (product_code) DO NOTHING;
        """), inventory_data)

        # Insert into suppliers
        suppliers_data = [
            {'supplier_id': 101, 'supplier_name': "Atlanta Ice Cream Supplier", 'contact_info': "tony@atlantaice.com"},
            {'supplier_id': 102, 'supplier_name': "Chocolate The Best", 'contact_info': "lan@chocobest.com"},
        ]
        conn.execute(text("""
            INSERT INTO suppliers (supplier_id, supplier_name, contact_info)
            VALUES (:supplier_id, :supplier_name, :contact_info)
            ON CONFLICT (supplier_id) DO NOTHING;
        """), suppliers_data)

        # Insert into supplier_products 
        suppliers_products_data = [
            {'supplier_id': 101, 'product_code': PRODUCTS[0], 'lead_time_days': 5, 'min_order_quantity': 100, 'cost_per_unit': 2.0},
            {'supplier_id': 102, 'product_code': PRODUCTS[1], 'lead_time_days': 7, 'min_order_quantity': 130, 'cost_per_unit': 2.2},
        ]
        conn.execute(text("""
            INSERT INTO supplier_products (supplier_id, product_code, lead_time_days, min_order_quantity, cost_per_unit)
            VALUES (:supplier_id, :product_code, :lead_time_days, :min_order_quantity, :cost_per_unit)
            ON CONFLICT (supplier_id, product_code) DO NOTHING;
        """), suppliers_products_data)

        # Insert into sales
        insert_sales_data()

        conn.commit()
    print("Sample data inserted to 5 tables.")

if __name__ == "__main__":
    print("🚀 Setting up database...")
    create_tables()
    insert_sample_data()
    print("🎉 Database setup complete!")