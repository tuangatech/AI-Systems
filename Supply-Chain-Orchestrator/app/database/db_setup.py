import os
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from data_setup import insert_data
from dotenv import load_dotenv

load_dotenv()

# Load environment variable (set DATABASE_URL in .env or system)
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

engine = create_engine(DB_URL)

def create_tables():
    """Create the required tables if they don't exist."""
    with engine.connect() as conn:
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
                product_id INTEGER PRIMARY KEY,
                current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
                reorder_point INTEGER NOT NULL CHECK (reorder_point >= 0)
            );
        """))

        # Create suppliers table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
                min_order_quantity INTEGER NOT NULL CHECK (min_order_quantity > 0),
                cost_per_unit NUMERIC(10, 2) NOT NULL CHECK (cost_per_unit >= 0),
                FOREIGN KEY (product_id) REFERENCES inventory (product_id)
            );
        """))

        conn.commit()
    print("✅ Tables created successfully.")

def insert_sample_data():
    """Insert 2-3 sample records into each table."""
    with engine.connect() as conn:
        # Insert into sales
        insert_data()
        # sales_data = [
        #     ('2024-01-15', 'PROD001', 25),
        #     ('2024-01-16', 'PROD002', 15),
        #     ('2024-01-17', 'PROD001', 40)
        # ]
        # conn.execute(text("""
        #     INSERT INTO sales (date, product_code, quantity)
        #     VALUES (:date, :product_code, :quantity)
        #     ON CONFLICT DO NOTHING;
        # """), sales_data)

        # Insert into inventory
        inventory_data = [
            {'product_id': 1, 'current_stock': 100, 'reorder_point': 30},
            {'product_id': 2, 'current_stock': 45,  'reorder_point': 20},
            # {'product_id': 3, 'current_stock': 10,  'reorder_point': 15},  # needs reorder
        ]
        conn.execute(text("""
            INSERT INTO inventory (product_id, current_stock, reorder_point)
            VALUES (:product_id, :current_stock, :reorder_point)
            ON CONFLICT (product_id) DO NOTHING;
        """), inventory_data)

        # Insert into suppliers
        suppliers_data = [
            {'supplier_id': 101, 'product_id': 1, 'lead_time_days': 5, 'min_order_quantity': 50, 'cost_per_unit': 9.99},
            {'supplier_id': 102, 'product_id': 2, 'lead_time_days': 7, 'min_order_quantity': 30, 'cost_per_unit': 14.50},
            # {'supplier_id': 103, 'product_id': 3, 'lead_time_days': 4, 'min_order_quantity': 40, 'cost_per_unit': 19.99},
        ]
        conn.execute(text("""
            INSERT INTO suppliers (supplier_id, product_id, lead_time_days, min_order_quantity, cost_per_unit)
            VALUES (:supplier_id, :product_id, :lead_time_days, :min_order_quantity, :cost_per_unit)
            ON CONFLICT (supplier_id) DO NOTHING;
        """), suppliers_data)

        conn.commit()
    print("✅ Sample data inserted.")

if __name__ == "__main__":
    print("🚀 Setting up database...")
    create_tables()
    insert_sample_data()
    print("🎉 Database setup complete!")