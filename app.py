from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import HoldingsDatabase
import sqlite3
from datetime import datetime
from free_tier_limiter import limiter, rate_limit, conditional_cache, ServiceDegrader
from safe_cache import cache, CacheFallback, get_with_fallback

app = Flask(__name__)
CORS(app)
db = HoldingsDatabase()
degrader = ServiceDegrader()
static_fallback = CacheFallback()

# ===== UI Routes =====

@app.route('/')
def index():
    """Main search page"""
    return render_template('index.html')

@app.route('/top-holdings')
def top_holdings_page():
    """Top holdings page"""
    # You can create this template later if needed
    return render_template('index.html')  # For now, redirect to main page

@app.route('/api-docs')
def api_docs():
    """API documentation page"""
    # For now, just redirect to main page
    # You can create a proper docs template later
    return render_template('index.html')

# ===== API Routes =====

@app.route('/api/search', methods=['GET'])
@rate_limit('api_requests')
@conditional_cache('api_requests')
def api_search():
    """Search for holdings by ticker or company name"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Missing search query parameter "q"'}), 400
    
    # Check cache first
    cache_key = f"search:{query.lower()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        print('cache')
        return jsonify(cached_result)
        
    
    # Get service level for degradation
    service_level = limiter.get_service_level()
    
    # Query database with rate limiting
    @rate_limit('database_queries')
    def query_db():
        print('database query')
        return db.search_stock(query)
    
    results = query_db()
    
    if results:
        formatted_results = []
        for idx, result in enumerate(results):
            formatted_results.append({
                'ticker': result[3],
                'company_name': result[2],
                'percentage': float(result[4]),
                'market_value': float(result[10]),
                'shares': int(result[11]),
                'rank': idx + 1
            })
        response_data = {
            'found': True,
            'query': query,
            'results': formatted_results
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

@app.route('/api/holdings/top', methods=['GET'])
def api_top_holdings():
    """Get top holdings by percentage"""
    try:
        limit = int(request.args.get('limit', 10))
        limit = min(limit, 100)
        limit = max(limit, 1)
    except ValueError:
        return jsonify({'error': 'Invalid limit parameter'}), 400
    
    holdings = db.get_all_holdings()[:limit]
    
    formatted_holdings = []
    for idx, holding in enumerate(holdings):
        formatted_holdings.append({
            'ticker': holding[0],
            'company_name': holding[1],
            'percentage': float(holding[2]),
            'market_value': float(holding[3]),
            'rank': idx + 1
        })
    
    return jsonify({
        'count': len(formatted_holdings),
        'holdings': formatted_holdings
    })

@app.route('/api/owns/<ticker>', methods=['GET'])
def api_check_ownership(ticker):
    """Check if you own a specific stock through VTSAX"""
    ticker = ticker.upper().strip()
    
    results = db.search_stock(ticker)
    
    exact_match = None
    for result in results:
        if result[3] == ticker:
            exact_match = result
            break
    
    if exact_match:
        percentage = float(exact_match[4])
        return jsonify({
            'owns': True,
            'ticker': ticker,
            'company_name': exact_match[2],
            'percentage': percentage,
            'market_value': float(exact_match[10]),
            'shares': int(exact_match[11]),
            'message': f'Yes, you own {exact_match[2]} through VTSAX ({percentage:.2f}% of fund)'
        })
    else:
        return jsonify({
            'owns': False,
            'ticker': ticker,
            'message': f'No, you do not own {ticker} through VTSAX'
        })

@app.route('/api/stats', methods=['GET'])
def api_get_statistics():
    """Get database statistics and metadata"""
    stats = db.get_stats()
    
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(market_value) FROM holdings")
    total_value = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(date_added) FROM holdings")
    last_updated = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_holdings': stats['unique_stocks'],
        'last_updated': last_updated,
        'total_market_value': float(total_value) if total_value else 0,
        'data_source': 'VTSAX',
        'fund_name': 'Vanguard Total Stock Market Index Fund Admiral Shares'
    })

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'VTSAX Holdings API'})

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
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('index.html'), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("VTSAX Holdings Tracker")
    print("="*50)
    print("\nWeb UI available at: http://localhost:5000")
    print("\nAPI Endpoints:")
    print("  GET /api/search?q=<query>")
    print("  GET /api/holdings/top?limit=<n>")
    print("  GET /api/owns/<ticker>")
    print("  GET /api/stats")
    print("  GET /api/health")
    print("\n" + "="*50 + "\n")
    
    app.run(debug=True, port=8080, host='127.0.0.1')