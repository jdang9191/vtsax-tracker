"""
Configuration for multiple index funds
Each fund needs its Vanguard URL for downloading holdings
"""

SUPPORTED_FUNDS = {
    'VTSAX': {
        'name': 'Vanguard Total Stock Market Index Fund Admiral',
        'url': 'https://advisors.vanguard.com/investments/products/vtsax/vanguard-total-stock-market-index-fund-admiral-shares',
        'description': 'Total US Stock Market',
        'expense_ratio': 0.04,
        'holdings_count': 3500  # approximate
    },
    'VOO': {
        'name': 'Vanguard S&P 500 ETF',
        'url': 'https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf',
        'description': 'S&P 500 Index',
        'expense_ratio': 0.03,
        'holdings_count': 500
    },
    'VTI': {
        'name': 'Vanguard Total Stock Market ETF',
        'url': 'https://advisors.vanguard.com/investments/products/vti/vanguard-total-stock-market-etf',
        'description': 'Total US Stock Market ETF',
        'expense_ratio': 0.03,
        'holdings_count': 3500
    },
    'VUG': {
        'name': 'Vanguard Growth ETF',
        'url': 'https://advisors.vanguard.com/investments/products/vug/vanguard-growth-etf',
        'description': 'Large-Cap Growth',
        'expense_ratio': 0.04,
        'holdings_count': 250
    },
    'VTV': {
        'name': 'Vanguard Value ETF',
        'url': 'https://advisors.vanguard.com/investments/products/vtv/vanguard-value-etf',
        'description': 'Large-Cap Value',
        'expense_ratio': 0.04,
        'holdings_count': 350
    }
}

# Non-Vanguard funds would need different scraping logic
OTHER_FUNDS = {
    'SPY': {
        'name': 'SPDR S&P 500 ETF',
        'provider': 'State Street',
        'description': 'S&P 500 Index',
        'note': 'Would need different scraper'
    },
    'QQQ': {
        'name': 'Invesco QQQ Trust',
        'provider': 'Invesco',
        'description': 'Nasdaq-100 Index',
        'note': 'Would need different scraper'
    }
}