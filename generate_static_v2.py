#!/usr/bin/env python3
"""
Generate static JSON files for multi-fund fallback
"""

import json
import os
from database_v2 import MultiFundDatabase
from safe_cache import CacheFallback
from datetime import datetime

def generate_static_files():
    """Generate all static JSON files for fallback"""
    print("Generating static fallback files for multi-fund database...")
    
    db = MultiFundDatabase()
    fallback = CacheFallback('static/cache')
    
    # Create static directory
    os.makedirs('static/cache', exist_ok=True)
    
    # Get all funds
    all_funds = db.get_all_funds()
    print(f"Found {len(all_funds)} funds in database")
    
    # 1. Save fund list
    fund_list = []
    for fund in all_funds:
        fund_list.append({
            'fund_symbol': fund[0],
            'fund_name': fund[1],
            'description': fund[2],
            'expense_ratio': fund[3],
            'last_updated': fund[4],
            'holdings_count': fund[5]
        })
    
    with open('static/cache/funds.json', 'w') as f:
        json.dump(fund_list, f)
    print("✓ Generated funds.json")
    
    # 2. For each fund, generate holdings data
    all_tickers = set()  # Track all unique tickers
    
    for fund in all_funds:
        fund_symbol = fund[0]
        holdings = db.get_all_holdings(fund_symbol)
        
        holdings_list = []
        for holding in holdings:
            # Skip if any critical field is None
            if holding[0] is None or holding[1] is None:
                continue
            holdings_list.append({
                'ticker': holding[0],
                'company_name': holding[1],
                'percentage': holding[2],
                'market_value': holding[3]
            })
            all_tickers.add(holding[0])
        
        # Save fund-specific files
        with open(f'static/cache/{fund_symbol}_holdings.json', 'w') as f:
            json.dump(holdings_list, f)
        print(f"✓ Generated {fund_symbol}_holdings.json ({len(holdings_list)} holdings)")
        
        # Top 20 for this fund
        with open(f'static/cache/{fund_symbol}_top20.json', 'w') as f:
            json.dump(holdings_list[:20], f)
    
    # 3. Create cross-fund ticker index
    ticker_funds = {}  # ticker -> list of funds containing it
    
    for fund in all_funds:
        fund_symbol = fund[0]
        funds_with_stock = db.get_funds_containing_stock('')  # We'll build this manually
        
        holdings = db.get_all_holdings(fund_symbol)
        for holding in holdings:
            ticker = holding[0]
            if ticker and ticker not in ticker_funds:
                ticker_funds[ticker] = []
            
            if ticker:
                ticker_funds[ticker].append({
                    'fund_symbol': fund_symbol,
                    'fund_name': fund[1],
                    'percentage': holding[2]
                })
    
    with open('static/cache/ticker_funds_index.json', 'w') as f:
        json.dump(ticker_funds, f)
    print(f"✓ Generated ticker_funds_index.json ({len(ticker_funds)} unique tickers)")
    
    # 4. Popular tickers across all funds
    popular_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK.B']
    popular_data = {}
    
    for ticker in popular_tickers:
        if ticker in ticker_funds:
            popular_data[ticker] = ticker_funds[ticker]
    
    with open('static/cache/popular_multi.json', 'w') as f:
        json.dump(popular_data, f)
    print("✓ Generated popular_multi.json")
    
    # 5. Statistics
    stats = db.get_stats()
    stats_data = {
        'total_holdings': stats['unique_stocks'],
        'total_funds': stats['total_funds'],
        'last_updated': stats['latest_update'],
        'fund_details': [
            {
                'fund_symbol': fund[0],
                'fund_name': fund[1],
                'holdings_count': fund[2]
            } for fund in stats['fund_stats']
        ],
        'generated_at': str(datetime.now())
    }
    
    with open('static/cache/stats_multi.json', 'w') as f:
        json.dump(stats_data, f)
    print("✓ Generated stats_multi.json")
    
    # 6. Manifest
    manifest = {
        'generated_at': str(datetime.now()),
        'total_funds': len(all_funds),
        'total_unique_stocks': len(all_tickers),
        'files': [
            'funds.json',
            'ticker_funds_index.json',
            'popular_multi.json',
            'stats_multi.json'
        ] + [f'{fund[0]}_holdings.json' for fund in all_funds] + 
        [f'{fund[0]}_top20.json' for fund in all_funds]
    }
    
    with open('static/cache/manifest_v2.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    print("✓ Generated manifest_v2.json")
    
    print(f"\n✅ Successfully generated {len(manifest['files'])} static files")
    print("These files will be used as fallback when API limits are reached")

if __name__ == '__main__':
    generate_static_files()