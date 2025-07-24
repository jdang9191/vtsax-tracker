#!/usr/bin/env python3
"""
Generate static JSON files for fallback when limits are reached
Run this after scraping to pre-generate static data
"""

import json
import os
from database import HoldingsDatabase
from safe_cache import CacheFallback

def generate_static_files():
    """Generate all static JSON files for fallback"""
    print("Generating static fallback files...")
    
    db = HoldingsDatabase()
    fallback = CacheFallback('static/cache')
    
    # Create static directory
    os.makedirs('static/cache', exist_ok=True)
    
    # Get all holdings data
    all_holdings = db.get_all_holdings()
    
    # Convert to list of dicts, skip any with None values
    holdings_list = []
    for holding in all_holdings:
        # Skip if any critical field is None
        if holding[0] is None or holding[1] is None:
            continue
        holdings_list.append({
            'ticker': holding[0],
            'company_name': holding[1],
            'percentage': holding[2],
            'market_value': holding[3]
        })
    
    print(f"Processing {len(holdings_list)} holdings...")
    
    # 1. Save complete holdings list
    with open('static/cache/all_holdings.json', 'w') as f:
        json.dump(holdings_list, f)
    print("✓ Generated all_holdings.json")
    
    # 2. Save top 100 holdings
    top_100 = holdings_list[:100]
    with open('static/cache/top_100.json', 'w') as f:
        json.dump(top_100, f)
    print("✓ Generated top_100.json")
    
    # 3. Save top 20 holdings (for homepage)
    top_20 = holdings_list[:20]
    with open('static/cache/top_20.json', 'w') as f:
        json.dump(top_20, f)
    print("✓ Generated top_20.json")
    
    # 4. Create ticker index for fast lookup
    ticker_index = {h['ticker']: h for h in holdings_list}
    with open('static/cache/ticker_index.json', 'w') as f:
        json.dump(ticker_index, f)
    print("✓ Generated ticker_index.json")
    
    # 5. Create company name index
    company_index = {h['company_name'].lower(): h for h in holdings_list}
    with open('static/cache/company_index.json', 'w') as f:
        json.dump(company_index, f)
    print("✓ Generated company_index.json")
    
    # 6. Create search index (both ticker and company)
    search_index = {}
    for h in holdings_list:
        # Index by ticker (store as single result)
        ticker_lower = h['ticker'].lower()
        search_index[ticker_lower] = h
        
        # Index by company name words (store as list of results)
        company_words = h['company_name'].lower().split()
        for word in company_words:
            if len(word) > 2:  # Skip short words
                # Add suffix to distinguish from tickers
                word_key = f"word:{word}"
                if word_key not in search_index:
                    search_index[word_key] = []
                search_index[word_key].append(h)
    
    with open('static/cache/search_index.json', 'w') as f:
        json.dump(search_index, f)
    print("✓ Generated search_index.json")
    
    # 7. Generate popular searches
    popular_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK.B']
    popular_searches = {}
    for ticker in popular_tickers:
        if ticker in ticker_index:
            popular_searches[ticker] = ticker_index[ticker]
    
    with open('static/cache/popular_searches.json', 'w') as f:
        json.dump(popular_searches, f)
    print("✓ Generated popular_searches.json")
    
    # 8. Generate statistics
    stats_data = {
        'total_holdings': len(holdings_list),
        'last_updated': str(datetime.now()),  # You can update this with actual scrape date
        'top_holding': holdings_list[0] if holdings_list else None,
        'generated_at': str(datetime.now())
    }
    
    with open('static/cache/stats.json', 'w') as f:
        json.dump(stats_data, f)
    print("✓ Generated stats.json")
    
    # 9. Create a manifest file
    manifest = {
        'generated_at': str(datetime.now()),
        'total_holdings': len(holdings_list),
        'files': [
            'all_holdings.json',
            'top_100.json',
            'top_20.json',
            'ticker_index.json',
            'company_index.json',
            'search_index.json',
            'popular_searches.json',
            'stats.json'
        ]
    }
    
    with open('static/cache/manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    print("✓ Generated manifest.json")
    
    print(f"\n✅ Successfully generated {len(manifest['files'])} static files")
    print("These files will be used as fallback when API limits are reached")


if __name__ == '__main__':
    from datetime import datetime
    generate_static_files()