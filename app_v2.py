from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database_v2 import MultiFundDatabase
from funds_config import SUPPORTED_FUNDS
import sqlite3
from datetime import datetime
from free_tier_limiter import limiter, rate_limit, conditional_cache, ServiceDegrader
from safe_cache import cache, CacheFallback, get_with_fallback

app = Flask(__name__)
CORS(app)
db = MultiFundDatabase()
degrader = ServiceDegrader()
static_fallback = CacheFallback()

# ===== UI Routes =====

@app.route('/')
def index():
    """Main search page"""
    return render_template('index_v2.html')

@app.route('/funds')
def funds_page():
    """Page showing all available funds"""
    return render_template('funds.html')

# ===== API Routes =====

@app.route('/api/search', methods=['GET'])
@rate_limit('api_requests')
@conditional_cache('api_requests')
def api_search():
    """Search for holdings across all funds"""
    query = request.args.get('q', '').strip()
    fund = request.args.get('fund', '').strip()  # Optional: filter by specific fund
    
    if not query:
        return jsonify({'error': 'Missing search query parameter "q"'}), 400
    
    # Check cache first
    cache_key = f"search:{query.lower()}:{fund}" if fund else f"search:{query.lower()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
    # Get service level for degradation
    service_level = limiter.get_service_level()
    
    # Query database
    @rate_limit('database_queries')
    def query_db():
        if fund:
            return db.search_stock_in_fund(query, fund)
        else:
            return db.search_stock(query)
    
    results = query_db()
    
    if results:
        # Group results by fund
        funds_data = {}
        for result in results:
            if fund:  # Single fund search
                fund_symbol = fund
                ticker = result[3]
                company_name = result[2]
                percentage = float(result[4])
                market_value = float(result[10])
                shares = int(result[11])
            else:  # Multi-fund search
                # Columns: id, fund_symbol, sedol, holdings, ticker, percentage, sector, country, ... market_value, shares, last_updated, fund_name
                fund_symbol = result[1]
                fund_name = result[14]   # fund_name from join (last column)
                ticker = result[4]
                company_name = result[3]
                percentage = float(result[5])
                market_value = float(result[11])
                shares = int(result[12])
            
            if fund_symbol not in funds_data:
                funds_data[fund_symbol] = {
                    'fund_symbol': fund_symbol,
                    'fund_name': fund_name if not fund else SUPPORTED_FUNDS.get(fund, {}).get('name', fund),
                    'holdings': []
                }
            
            funds_data[fund_symbol]['holdings'].append({
                'ticker': ticker,
                'company_name': company_name,
                'percentage': percentage,
                'market_value': market_value,
                'shares': shares
            })
        
        response_data = {
            'found': True,
            'query': query,
            'funds': list(funds_data.values()),
            'total_funds': len(funds_data)
        }
        
        # Apply degradation if needed
        if service_level != 'normal':
            response_data = degrader.degrade_response(response_data, service_level)
            response_data['service_level'] = service_level
        
        # Cache the response
        cache_ttl = 300 if service_level == 'normal' else 3600
        cache.set(cache_key, response_data, cache_ttl)
        
        return jsonify(response_data)
    else:
        return jsonify({
            'found': False,
            'query': query,
            'message': f'No holdings found for "{query}"'
        })

@app.route('/api/funds', methods=['GET'])
def api_get_funds():
    """Get list of all available funds"""
    funds = db.get_all_funds()
    
    formatted_funds = []
    for fund in funds:
        formatted_funds.append({
            'fund_symbol': fund[0],
            'fund_name': fund[1],
            'description': fund[2],
            'expense_ratio': fund[3],
            'last_updated': fund[4],
            'holdings_count': fund[5]
        })
    
    return jsonify({
        'funds': formatted_funds,
        'supported_funds': SUPPORTED_FUNDS
    })

@app.route('/api/holdings/<fund_symbol>/top', methods=['GET'])
@rate_limit('api_requests')
def api_fund_top_holdings(fund_symbol):
    """Get top holdings for a specific fund"""
    try:
        limit = int(request.args.get('limit', 10))
        limit = min(limit, 100)
        limit = max(limit, 1)
    except ValueError:
        return jsonify({'error': 'Invalid limit parameter'}), 400
    
    holdings = db.get_all_holdings(fund_symbol)[:limit]
    
    formatted_holdings = []
    for idx, holding in enumerate(holdings):
        formatted_holdings.append({
            'ticker': holding[0],
            'company_name': holding[1],
            'percentage': float(holding[2]),
            'market_value': float(holding[3]),
            'rank': idx + 1
        })
    
    fund_info = SUPPORTED_FUNDS.get(fund_symbol, {})
    
    return jsonify({
        'fund_symbol': fund_symbol,
        'fund_name': fund_info.get('name', fund_symbol),
        'count': len(formatted_holdings),
        'holdings': formatted_holdings
    })

@app.route('/api/stock/<ticker>/funds', methods=['GET'])
def api_stock_in_funds(ticker):
    """Get all funds that contain a specific stock"""
    funds = db.get_funds_containing_stock(ticker)
    
    if funds:
        formatted_funds = []
        for fund in funds:
            formatted_funds.append({
                'fund_symbol': fund[0],
                'fund_name': fund[1],
                'percentage': float(fund[2]),
                'shares': int(fund[3]),
                'market_value': float(fund[4])
            })
        
        return jsonify({
            'found': True,
            'ticker': ticker.upper(),
            'funds': formatted_funds,
            'total_funds': len(formatted_funds)
        })
    else:
        return jsonify({
            'found': False,
            'ticker': ticker.upper(),
            'message': f'{ticker.upper()} not found in any tracked funds'
        })

@app.route('/api/stats', methods=['GET'])
def api_get_statistics():
    """Get database statistics"""
    stats = db.get_stats()
    
    return jsonify({
        'total_holdings': stats['unique_stocks'],
        'total_funds': stats['total_funds'],
        'last_updated': stats['latest_update'],
        'fund_details': [
            {
                'fund_symbol': fund[0],
                'fund_name': fund[1],
                'holdings_count': fund[2]
            } for fund in stats['fund_stats']
        ]
    })

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Multi-Fund Holdings API'})

@app.route('/api/usage', methods=['GET'])
def api_usage_stats():
    """Get usage statistics for free tier monitoring"""
    return jsonify({
        'limits': limiter.get_all_usage_stats(),
        'cache': cache.get_usage_stats(),
        'service_level': limiter.get_service_level(),
        'warnings': _get_usage_warnings()
    })

def _get_usage_warnings():
    """Get any usage warnings"""
    warnings = []
    stats = limiter.get_all_usage_stats()
    
    for service, data in stats.items():
        if data['percentage'] > 80:
            warnings.append({
                'service': service,
                'message': f"{service} at {data['percentage']:.1f}% of limit",
                'severity': 'critical' if data['percentage'] > 90 else 'warning'
            })
    
    return warnings

# Error handlers
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint not found'}), 404
    return render_template('index_v2.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('index_v2.html'), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Multi-Fund Holdings Tracker")
    print("="*50)
    print("\nWeb UI available at: http://localhost:8080")
    print("\nAPI Endpoints:")
    print("  GET /api/search?q=<query>&fund=<optional>")
    print("  GET /api/funds")
    print("  GET /api/holdings/<fund>/top?limit=<n>")
    print("  GET /api/stock/<ticker>/funds")
    print("  GET /api/stats")
    print("  GET /api/health")
    print("  GET /api/usage")
    print("\n" + "="*50 + "\n")
    
    app.run(debug=True, port=8080, host='127.0.0.1')