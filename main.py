import json
import sqlite3
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastmcp import FastMCP, Context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP Server
mcp = FastMCP("Expense Tracker Pro")

# --- Cloud Deployment Setup ---
# Resolve the directory where the script is located
BASE_DIR = Path(__file__).parent.resolve()
CATEGORIES_FILE = BASE_DIR / "data" / "categories.json"

# Use a temporary directory for the SQLite database if running in an ephemeral environment
# This ensures we have write permissions in cloud environments like FastMCP Cloud
TEMP_DB_DIR = Path(tempfile.gettempdir()) / "expense_tracker"
TEMP_DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = TEMP_DB_DIR / "expenses.db"


def load_categories_config():
    if not os.path.exists(CATEGORIES_FILE):
        return {}
    with open(CATEGORIES_FILE, "r") as f:
        return json.load(f)


def init_db():
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                note TEXT
            )
        """
        )
        conn.commit()


@mcp.tool()
def add_expense(
    amount: float,
    category: str,
    subcategory: Optional[str] = None,
    note: Optional[str] = None,
    date: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Add a new expense to the SQLite database.

    Args:
        amount: Cost of the expense (must be positive)
        category: Main category (e.g., Food, Transport)
        subcategory: Optional specific category (e.g., Grocery, Uber)
        note: Optional description or note
        date: Optional date in YYYY-MM-DD format (defaults to today)
    """
    if amount <= 0:
        if ctx:
            ctx.error(f"Validation failed: amount {amount} <= 0")
        return "Error: Amount must be a positive number."

    record_date = date or datetime.now().strftime("%Y-%m-%d")

    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO expenses (amount, date, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
                (amount, record_date, category, subcategory, note),
            )
            expense_id = cursor.lastrowid
            conn.commit()

            if ctx:
                ctx.info(f"Added expense ID {expense_id}: ${amount} for {category}")
            return f"Successfully added expense ID {expense_id}: {category} ({subcategory or 'N/A'}) - ${amount:.2f} on {record_date}"
    except Exception as e:
        if ctx:
            ctx.error(f"Database error: {str(e)}")
        return f"Error: Failed to save expense to database: {str(e)}"


@mcp.tool()
def list_expenses(
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    List recent expenses with advanced filtering.

    Args:
        category: Filter by specific category
        start_date: Filter from this date (YYYY-MM-DD)
        end_date: Filter until this date (YYYY-MM-DD)
        limit: Number of records to return
    """
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM expenses WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " ORDER BY date DESC, id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return "No expenses found matching the criteria."

            output = [
                f"{'ID':<4} | {'Date':<10} | {'Category':<12} | {'Subcategory':<12} | {'Amount':<8} | {'Note'}"
            ]
            output.append("-" * 80)

            for r in rows:
                output.append(
                    f"{r['id']:<4} | {r['date']:<10} | {r['category']:<12} | {r['subcategory'] or 'N/A':<12} | ${r['amount']:<7.2f} | {r['note'] or ''}"
                )

            return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_summary(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> str:
    """
    Get an optimized spending summary grouped by category/subcategory using SQL.

    Args:
        start_date: Start date for summary (YYYY-MM-DD)
        end_date: End date for summary (YYYY-MM-DD)
    """
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            # Optimized Group By Query
            query = """
                SELECT category, subcategory, SUM(amount), COUNT(*) 
                FROM expenses 
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += (
                " GROUP BY category, subcategory ORDER BY category, SUM(amount) DESC"
            )

            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return "No data recorded for the selected period."

            total_query = "SELECT SUM(amount) FROM expenses WHERE 1=1"
            if start_date:
                total_query += " AND date >= ?"
            if end_date:
                total_query += " AND date <= ?"
            cursor.execute(total_query, params)
            total_sum = cursor.fetchone()[0] or 0

            output = [
                f"Expense Summary Report ({start_date or 'Beginning'} to {end_date or 'Now'})"
            ]
            output.append(f"TOTAL SPEND: ${total_sum:.2f}")
            output.append("-" * 40)

            current_cat = None
            for cat, sub, amt, count in rows:
                if cat != current_cat:
                    output.append(
                        f"\n[{cat.upper()}] - Total: ${amt:.2f} ({count} entries)"
                    )
                    current_cat = cat
                if sub:
                    output.append(f"  └─ {sub}: ${amt:.2f}")

            return "\n".join(output)
    except Exception as e:
        return f"Error gathering summary: {str(e)}"


@mcp.resource("expenses://categories")
def get_categories_and_subcategories() -> str:
    """List all available expense categories and their subcategories."""
    config = load_categories_config()
    if not config:
        return "No categories configured."

    output = ["Full Expense Categories Hierarchy:"]
    output.append("-" * 35)

    for cat in sorted(config.keys()):
        output.append(f"\n{cat.upper()}")
        subs = sorted(config[cat])
        if subs:
            for sub in subs:
                output.append(f"  └─ {sub}")
        else:
            output.append("  (No subcategories)")

    return "\n".join(output)


@mcp.resource("expenses://summary")
def get_resource_summary() -> str:
    """Get a quick summary of total spend."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM expenses")
        total = cursor.fetchone()[0] or 0
        return f"Database: {DB_PATH}\nTotal lifetime spend tracked: ${total:.2f}"


def main():
    init_db()
    # Support automatic transport detection for Cloud vs Local
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
