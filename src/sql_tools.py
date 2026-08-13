"""Executes validated read-only SQL against MySQL and returns rows as dictionaries."""

import mysql.connector

from src import config
from src.safety import validate_sql


def run_select(sql: str) -> list[dict]:
    safe_sql = validate_sql(sql)

    conn = mysql.connector.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        database=config.MYSQL_DATABASE,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
    )
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(safe_sql)
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return rows
