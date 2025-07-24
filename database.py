import sqlite3
import pandas as pd
from datetime import datetime

class HoldingsDatabase:
    def __init__(self, db_path="vtsax_holdings.db"):
        self.db_path = db_path
        self.conn = None
        self.create_table()
    
    def create_table(self):
        """Create the holdings table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sedol TEXT,
                holdings TEXT,
                ticker TEXT,
                percentage REAL,
                sub_industry TEXT,
                country TEXT,
                security_type TEXT,
                depository TEXT,
                receipt_type TEXT,
                market_value REAL,
                shares INTEGER,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on ticker for faster searches
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ticker ON holdings(ticker)
        ''')
        
        conn.commit()
        conn.close()
    
    def insert_holdings(self, df):
        """Insert holdings data from a pandas DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        # Clear existing data (optional - remove if you want to keep historical data)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM holdings")
        
        # Insert new data
        df.to_sql('holdings_temp', conn, if_exists='replace', index=False)
        
        cursor.execute('''
            INSERT INTO holdings (
                sedol, holdings, ticker, percentage, sub_industry, 
                country, security_type, depository, receipt_type, 
                market_value, shares
            )
            SELECT 
                "SEDOL", "HOLDINGS", "TICKER", "% OF FUNDS*", "SUB-INDUSTRY",
                "COUNTRY", "SECURITYDEPOSITORYRECEIPTTYPE", "SECURITYDEPOSITORYRECEIPTTYPE", "SECURITYDEPOSITORYRECEIPTTYPE",
                "MARKET VALUE", "SHARES"
            FROM holdings_temp
        ''')
        
        # Drop temporary table
        cursor.execute("DROP TABLE holdings_temp")
        
        conn.commit()
        conn.close()
        
        print(f"Successfully inserted {len(df)} holdings into database")
    
    def search_stock(self, query):
        """Search for a stock by ticker or company name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Search by ticker (exact match) or company name (partial match)
        cursor.execute('''
            SELECT * FROM holdings 
            WHERE ticker = ? OR holdings LIKE ?
            ORDER BY percentage DESC
        ''', (query.upper(), f'%{query}%'))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_all_holdings(self):
        """Get all holdings sorted by percentage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ticker, holdings, percentage, market_value 
            FROM holdings 
            ORDER BY percentage DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count unique stocks
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM holdings")
        unique_stocks = cursor.fetchone()[0]
        
        # Get latest date
        cursor.execute("SELECT MAX(date_added) FROM holdings")
        latest_scrape = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'unique_stocks': unique_stocks,
            'latest_scrape': latest_scrape
        }