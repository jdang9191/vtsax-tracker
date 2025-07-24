from database import HoldingsDatabase
import os

# Check if database exists
db_path = "vtsax_holdings.db"
if os.path.exists(db_path):
    print(f"✓ Database file exists: {db_path}")
    print(f"  File size: {os.path.getsize(db_path)} bytes")
else:
    print("✗ Database file not found")
    exit()

# Connect to database
db = HoldingsDatabase()

# Get all holdings
holdings = db.get_all_holdings()
print(f"\n✓ Total holdings in database: {len(holdings)}")

# Show top 10 holdings
print("\n--- Top 10 Holdings ---")
print(f"{'Ticker':<8} {'Company':<30} {'Percentage':<10} {'Market Value':<20}")
print("-" * 70)
for i, (ticker, company, percentage, market_value) in enumerate(holdings[:10]):
    print(f"{ticker:<8} {company[:29]:<30} {percentage:<10.2f}% ${market_value:,.2f}")

# Test search functionality
print("\n--- Search Tests ---")
test_queries = [
    "AAPL",      # Apple by ticker
    "Tesla",     # Tesla by name
    "MSFT",      # Microsoft by ticker
    "Amazon",    # Amazon by name
    "GOOGL",     # Google by ticker
    "FAKE123"    # Non-existent stock
]

for query in test_queries:
    results = db.search_stock(query)
    if results:
        result = results[0]  # Get first result
        print(f"✓ '{query}' found: {result[2]} ({result[1]}) - {result[3]}% of fund")
    else:
        print(f"✗ '{query}' not found in VTSAX")

# Show some statistics
print("\n--- Database Statistics ---")
import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Total market value
cursor.execute("SELECT SUM(market_value) FROM holdings")
total_value = cursor.fetchone()[0]
print(f"Total market value: ${total_value:,.2f}")

# Number of unique sectors
cursor.execute("SELECT COUNT(DISTINCT sub_industry) FROM holdings")
sectors = cursor.fetchone()[0]
print(f"Number of sectors: {sectors}")

# Average holding percentage
cursor.execute("SELECT AVG(percentage) FROM holdings")
avg_percentage = cursor.fetchone()[0]
print(f"Average holding percentage: {avg_percentage:.4f}%")

conn.close()