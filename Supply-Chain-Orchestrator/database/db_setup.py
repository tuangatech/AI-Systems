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
END_DATE = datetime.today()
START_DATE = END_DATE - timedelta(days=3 * 365)	# 3*365 approx. 3 years ago
PRODUCTS = ["vanilla", "chocolate"]
PRODUCT_NAMES = ["Vanilla Ice Cream", "Chocolate Ice Cream"]
BASE_SALES = {"vanilla": 100, "chocolate": 50}
SEASONALITY_FACTOR = {	# summer spike and winter drop
    1: 0.7, 2: 0.6, 3: 0.9, 4: 1.0, 5: 1.2, 6: 1.5,
    7: 1.6, 8: 1.5, 9: 1.1, 10: 1.0, 11: 0.9, 12: 0.7
}
NOISE_SCALE = 10  # Standard deviation of random noise

# Database setup
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(database_url)


def create_tables():
    """Create tables with proper foreign keys."""
    with engine.begin() as conn:  # auto-commits or rolls back
		# Drop existing tables for a clean setup
        conn.execute(text("DROP TABLE IF EXISTS sales, inventory, supplier_products, products, suppliers CASCADE;"))

        conn.execute(text("""
            CREATE TABLE products (
                product_code VARCHAR(50) PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(50),
                unit_cost DECIMAL(10,2),
                selling_price DECIMAL(10,2),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # safety_stock: Minimum buffer stock to prevent stockouts
        # reorder_point: Inventory level that triggers a reorder = Safety Stock + (Average Daily Demand × Lead Time in Days)
        conn.execute(text("""
            CREATE TABLE inventory (
                product_code VARCHAR(50) PRIMARY KEY REFERENCES products(product_code),
                current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
                reorder_point INTEGER NOT NULL CHECK (reorder_point >= 0),
                safety_stock INTEGER NOT NULL CHECK (safety_stock >= 0),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE suppliers (
                supplier_id INTEGER PRIMARY KEY,
                supplier_name VARCHAR(100) NOT NULL,
                contact_info TEXT
            );
        """))

        conn.execute(text("""
            CREATE TABLE supplier_products (
                supplier_id INTEGER REFERENCES suppliers(supplier_id),
                product_code VARCHAR(50) REFERENCES products(product_code),
                lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
                min_order_quantity INTEGER NOT NULL CHECK (min_order_quantity > 0),
                cost_per_unit NUMERIC(10, 2) NOT NULL CHECK (cost_per_unit >= 0),
                reliability_score DECIMAL(3,2) DEFAULT 1.0,
                PRIMARY KEY (supplier_id, product_code)
            );
        """))

        # Now safe to add FK since products will be inserted first
        conn.execute(text("""
            CREATE TABLE sales (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                product_code VARCHAR(50) REFERENCES products(product_code),
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                region VARCHAR(50) DEFAULT 'North',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
    print("✅ Tables created successfully.")


def generate_sales_data():
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq='D')
    data = []

    for date in dates:
        for product_code in PRODUCTS:
            base = BASE_SALES[product_code]
            seasonal_mult = SEASONALITY_FACTOR[date.month]
            # Apply seasonality and add noise
            expected = base * seasonal_mult
            noise = np.random.normal(0, NOISE_SCALE)
            quantity = max(1, int(round(expected + noise)))	  # Ensure at least 1
            data.append({
                'date': date.date(),  # Store as date, not datetime
                'product_code': product_code,
                'quantity': quantity,
                'region': 'North Atlanta'  # or randomize if needed
            })

    return pd.DataFrame(data)


def visualize_seasonality(df):
    df_plot = df.groupby(['date', 'product_code'])['quantity'].sum().unstack(fill_value=0)
    df_plot.plot(title='Daily Sales Over Time', figsize=(12, 6))
    plt.ylabel('Quantity Sold')
    plt.tight_layout()
    plt.savefig('sales_seasonality.png')
    plt.close()


def insert_sales_data(df):
    try:
        df.to_sql('sales', engine, if_exists='append', index=False, method='multi')
        print(f"✅ Inserted {len(df)} sales records.")
        visualize_seasonality(df)
    except Exception as e:
        print(f"❌ Error inserting sales data: {e}")
        raise


def insert_sample_data():
    with engine.begin() as conn:
        # 1. Products
        product_data = [
            {'code': PRODUCTS[0], 'name': PRODUCT_NAMES[0], 'cat': 'IceCream', 'cost': 2.0, 'price': 3.0},
            {'code': PRODUCTS[1], 'name': PRODUCT_NAMES[1], 'cat': 'IceCream', 'cost': 2.2, 'price': 3.5}
        ]
        conn.execute(text("""
            INSERT INTO products (product_code, product_name, category, unit_cost, selling_price)
            VALUES (:code, :name, :cat, :cost, :price)
            ON CONFLICT (product_code) DO NOTHING;
        """), product_data)

        # 2. Inventory
        inventory_data = [
            {'product_code': PRODUCTS[0], 'current_stock': 470, 'reorder_point': 600, 'safety_stock': 100},
            {'product_code': PRODUCTS[1], 'current_stock': 510, 'reorder_point': 400, 'safety_stock': 50}
        ]
        conn.execute(text("""
            INSERT INTO inventory (product_code, current_stock, reorder_point, safety_stock)
            VALUES (:product_code, :current_stock, :reorder_point, :safety_stock)
            ON CONFLICT (product_code) DO NOTHING;
        """), inventory_data)

        # 3. Suppliers
        conn.execute(text("""
            INSERT INTO suppliers (supplier_id, supplier_name, contact_info)
            VALUES 
                (101, 'Atlanta IceSup', 'tony@atlantaice.com'),
                (102, 'Chocolate The Best', 'lan@chocobest.com'),
                (103, 'Vanilla The Second', 'lan@vanilsnd.com')
            ON CONFLICT (supplier_id) DO NOTHING;
        """))

        # 4. Supplier-Products
        supplier_products_data = [
            {'supplier_id': 101, 'product_code': PRODUCTS[0], 'lead_time_days': 5, 'min_order_quantity': 300, 'cost_per_unit': 2.0},
            {'supplier_id': 101, 'product_code': PRODUCTS[1], 'lead_time_days': 7, 'min_order_quantity': 500, 'cost_per_unit': 2.3}
        ]
        conn.execute(text("""
            INSERT INTO supplier_products (supplier_id, product_code, lead_time_days, min_order_quantity, cost_per_unit)
            VALUES (:supplier_id, :product_code, :lead_time_days, :min_order_quantity, :cost_per_unit)
            ON CONFLICT (supplier_id, product_code) DO NOTHING;
        """), supplier_products_data)

    # 5. Generate and insert sales
    sales_df = generate_sales_data()
    insert_sales_data(sales_df)

    print("✅ Sample data inserted into all tables.")


if __name__ == "__main__":
    print("🚀 Setting up database...")
    create_tables()
    insert_sample_data()
    print("🎉 Database setup complete!")