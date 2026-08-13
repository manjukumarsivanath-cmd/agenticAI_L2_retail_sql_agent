"""Load the five retail CSVs into the retail_agent_assignment MySQL database."""

import os
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")

# Load order respects foreign key dependencies: parents before children.
TABLES = ["stores", "products", "customers", "sales_transactions", "returns"]

COLUMNS = {
    "stores": ["store_id", "store_name", "region", "city", "store_type"],
    "products": ["product_id", "product_name", "category", "sub_category", "base_price"],
    "customers": ["customer_id", "customer_segment", "signup_date", "preferred_channel", "city"],
    "sales_transactions": [
        "order_id", "order_date", "store_id", "product_id", "customer_id",
        "sales_channel", "units_sold", "unit_price", "discount_pct",
        "payment_status", "delivery_status",
    ],
    "returns": ["return_id", "order_id", "return_date", "return_reason"],
}


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
    )


def load_table(cursor, table_name: str) -> int:
    csv_path = DATA_DIR / f"{table_name}.csv"
    df = pd.read_csv(csv_path)
    df = df.where(pd.notna(df), None)  # NaN -> NULL

    columns = COLUMNS[table_name]
    placeholders = ", ".join(["%s"] * len(columns))
    column_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

    rows = [tuple(row[col] for col in columns) for _, row in df.iterrows()]
    cursor.executemany(insert_sql, rows)
    return len(rows)


def main():
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing data before reloading, children before parents (FK order).
    for table_name in reversed(TABLES):
        cursor.execute(f"DELETE FROM {table_name}")

    row_counts = {}
    for table_name in TABLES:
        row_counts[table_name] = load_table(cursor, table_name)

    conn.commit()
    cursor.close()
    conn.close()

    print("Data load complete. Row counts:")
    for table_name, count in row_counts.items():
        print(f"  {table_name}: {count}")


if __name__ == "__main__":
    main()
