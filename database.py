import sqlite3
import pandas as pd
from datetime import datetime
import os

class MultiFundDatabase:
    def __init__(self, db_path="holdings.db"):
        self.db_path = db_path
        self.conn = None
        self.create_tables()
    
    def create_tables(self):
        """Create tables for multiple funds support"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create funds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funds (
                fund_symbol TEXT PRIMARY KEY,
                fund_name TEXT NOT NULL,
                description TEXT,
                expense_ratio REAL,
                last_updated TIMESTAMP
            )
        ''')
        
        # Create holdings table with fund_symbol
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_symbol TEXT NOT NULL,
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
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fund_symbol) REFERENCES funds(fund_symbol)
            )
        ''')
        
        # Create indexes for faster searches
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticker ON holdings(ticker)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fund ON holdings(fund_symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticker_fund ON holdings(ticker, fund_symbol)')
        
        conn.commit()
        conn.close()
    
    def add_fund(self, fund_symbol, fund_name, description=None, expense_ratio=None):
        """Add a new fund to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO funds (fund_symbol, fund_name, description, expense_ratio, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (fund_symbol, fund_name, description, expense_ratio, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def insert_holdings(self, df, fund_symbol):
        """Insert holdings data for a specific fund"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data for this fund only
        cursor.execute("DELETE FROM holdings WHERE fund_symbol = ?", (fund_symbol,))
        
        # Add fund_symbol column to dataframe
        df['fund_symbol'] = fund_symbol
        
        # Insert new data
        df.to_sql('holdings_temp', conn, if_exists='replace', index=False)
        
        cursor.execute('''
            INSERT INTO holdings (
                fund_symbol, sedol, holdings, ticker, percentage, sub_industry, 
                country, security_type, depository, receipt_type,
                market_value, shares
            )
            SELECT 
                fund_symbol, "SEDOL", "HOLDINGS", "TICKER", "% OF FUNDS*", "SUB-INDUSTRY",
                "COUNTRY", "SECURITYDEPOSITORYRECEIPTTYPE", "SECURITYDEPOSITORYRECEIPTTYPE", 
                "SECURITYDEPOSITORYRECEIPTTYPE", "MARKET VALUE", "SHARES"
            FROM holdings_temp
        ''')
        
        # Update fund last_updated
        cursor.execute('''
            UPDATE funds SET last_updated = ? WHERE fund_symbol = ?
        ''', (datetime.now(), fund_symbol))
        
        # Drop temporary table
        cursor.execute("DROP TABLE holdings_temp")
        
        conn.commit()
        conn.close()
        
        print(f"Successfully inserted {len(df)} holdings for {fund_symbol}")
    
    def search_stock(self, query):
        """Search for a stock across all funds"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Search by ticker or company name across all funds
        cursor.execute('''
            SELECT DISTINCT h.*, f.fund_name 
            FROM holdings h
            JOIN funds f ON h.fund_symbol = f.fund_symbol
            WHERE h.ticker = ? OR h.holdings LIKE ?
            ORDER BY h.percentage DESC
        ''', (query.upper(), f'%{query}%'))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def search_stock_in_fund(self, query, fund_symbol):
        """Search for a stock in a specific fund"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM holdings 
            WHERE fund_symbol = ? AND (ticker = ? OR holdings LIKE ?)
            ORDER BY percentage DESC
        ''', (fund_symbol, query.upper(), f'%{query}%'))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_funds_containing_stock(self, ticker):
        """Get all funds that contain a specific stock"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT h.fund_symbol, f.fund_name, h.percentage, h.shares, h.market_value
            FROM holdings h
            JOIN funds f ON h.fund_symbol = f.fund_symbol
            WHERE h.ticker = ?
            ORDER BY h.percentage DESC
        ''', (ticker.upper(),))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_all_funds(self):
        """Get list of all funds in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fund_symbol, fund_name, description, expense_ratio, last_updated,
                   (SELECT COUNT(*) FROM holdings WHERE fund_symbol = f.fund_symbol) as holdings_count
            FROM funds f
            ORDER BY fund_symbol
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_all_holdings(self, fund_symbol=None):
        """Get all holdings, optionally filtered by fund"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if fund_symbol:
            cursor.execute('''
                SELECT ticker, holdings, percentage, market_value 
                FROM holdings 
                WHERE fund_symbol = ?
                ORDER BY percentage DESC
            ''', (fund_symbol,))
        else:
            cursor.execute('''
                SELECT h.ticker, h.holdings, h.percentage, h.market_value, h.fund_symbol, f.fund_name
                FROM holdings h
                JOIN funds f ON h.fund_symbol = f.fund_symbol
                ORDER BY h.percentage DESC
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM holdings")
        unique_stocks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT fund_symbol) FROM holdings")
        total_funds = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(date_added) FROM holdings")
        latest_update = cursor.fetchone()[0]
        
        # Per-fund stats
        cursor.execute('''
            SELECT f.fund_symbol, f.fund_name, COUNT(h.ticker) as holdings_count
            FROM funds f
            LEFT JOIN holdings h ON f.fund_symbol = h.fund_symbol
            GROUP BY f.fund_symbol
        ''')
        fund_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'unique_stocks': unique_stocks,
            'total_funds': total_funds,
            'latest_update': latest_update,
            'fund_stats': fund_stats
        }
    
    def migrate_from_old_db(self, old_db_path="vtsax_holdings.db"):
        """Migrate data from old single-fund database"""
        if not os.path.exists(old_db_path):
            print(f"Old database {old_db_path} not found")
            return
        
        # Add VTSAX fund
        self.add_fund('VTSAX', 'Vanguard Total Stock Market Index Fund Admiral', 
                     'Total US Stock Market', 0.04)
        
        # Copy holdings
        old_conn = sqlite3.connect(old_db_path)
        new_conn = sqlite3.connect(self.db_path)
        
        # Read old data
        old_data = pd.read_sql_query("SELECT * FROM holdings", old_conn)
        
        # Add fund_symbol
        old_data['fund_symbol'] = 'VTSAX'
        
        # Insert into new database
        old_data.to_sql('holdings_migration', new_conn, if_exists='replace', index=False)
        
        cursor = new_conn.cursor()
        cursor.execute('''
            INSERT INTO holdings (
                fund_symbol, sedol, holdings, ticker, percentage, sub_industry,
                country, security_type, depository, receipt_type,
                market_value, shares, date_added
            )
            SELECT 
                fund_symbol, sedol, holdings, ticker, percentage, sub_industry,
                country, security_type, depository, receipt_type,
                market_value, shares, date_added
            FROM holdings_migration
        ''')
        
        cursor.execute("DROP TABLE holdings_migration")
        
        old_conn.close()
        new_conn.commit()
        new_conn.close()
        
        print("Migration completed successfully")