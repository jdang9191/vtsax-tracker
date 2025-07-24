// VTSAX Holdings Tracker JavaScript

// API base URL - adjust if running on different port
const API_BASE = '/api';

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// Format percentage
function formatPercentage(value) {
    return value.toFixed(2) + '%';
}

// Load stats on page load
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        document.getElementById('total-holdings').textContent = data.total_holdings.toLocaleString();
        document.getElementById('total-value').textContent = formatCurrency(data.total_market_value);
        
        // Update last updated in footer
        if (data.last_updated) {
            const date = new Date(data.last_updated);
            document.getElementById('last-updated').textContent = date.toLocaleDateString();
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load top holdings
async function loadTopHoldings() {
    try {
        const response = await fetch(`${API_BASE}/holdings/top?limit=10`);
        const data = await response.json();
        
        const tbody = document.getElementById('top-holdings-table');
        tbody.innerHTML = '';
        
        data.holdings.forEach(holding => {
            const row = `
                <tr>
                    <td>${holding.rank}</td>
                    <td><strong>${holding.ticker}</strong></td>
                    <td>${holding.company_name}</td>
                    <td>${formatPercentage(holding.percentage)}</td>
                    <td>${formatCurrency(holding.market_value)}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
        
        // Update top holding stat
        if (data.holdings.length > 0) {
            const topHolding = data.holdings[0];
            document.getElementById('top-holding').innerHTML = 
                `<strong>${topHolding.ticker}</strong> (${formatPercentage(topHolding.percentage)})`;
        }
    } catch (error) {
        console.error('Error loading top holdings:', error);
    }
}

// Search function
async function performSearch(query) {
    const resultsDiv = document.getElementById('search-results');
    const loadingDiv = document.getElementById('loading');
    
    // Show loading
    loadingDiv.classList.remove('d-none');
    resultsDiv.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        loadingDiv.classList.add('d-none');
        
        if (data.found) {
            // Display results
            data.results.forEach(result => {
                const resultCard = `
                    <div class="card result-card owned mb-3 fade-in">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-md-8">
                                    <h4 class="card-title">
                                        <span class="text-success">✓</span>
                                        ${result.ticker} - ${result.company_name}
                                    </h4>
                                    <p class="mb-0">
                                        Yes! You own this stock through VTSAX
                                    </p>
                                </div>
                                <div class="col-md-4 text-md-end">
                                    <div class="h5 mb-0 text-vanguard">${formatPercentage(result.percentage)}</div>
                                    <small class="text-muted">of fund</small>
                                    <div class="mt-2">
                                        <small class="text-muted">
                                            ${result.shares.toLocaleString()} shares<br>
                                            ${formatCurrency(result.market_value)}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                resultsDiv.innerHTML += resultCard;
            });
        } else {
            // Not found
            const notFoundCard = `
                <div class="card result-card not-owned mb-3 fade-in">
                    <div class="card-body">
                        <h4 class="card-title">
                            <span class="text-warning">✗</span>
                            "${query}" not found in VTSAX
                        </h4>
                        <p class="mb-0">
                            This stock is not part of the Vanguard Total Stock Market Index Fund
                        </p>
                    </div>
                </div>
            `;
            resultsDiv.innerHTML = notFoundCard;
        }
    } catch (error) {
        loadingDiv.classList.add('d-none');
        resultsDiv.innerHTML = `
            <div class="alert alert-danger" role="alert">
                Error searching for holdings. Please try again.
            </div>
        `;
        console.error('Search error:', error);
    }
}

// Load usage stats
async function loadUsageStats() {
    try {
        const response = await fetch(`${API_BASE}/usage`);
        const data = await response.json();
        
        // Display warnings if any
        if (data.warnings && data.warnings.length > 0) {
            const warningDiv = document.createElement('div');
            warningDiv.className = 'alert alert-warning alert-dismissible fade show';
            warningDiv.innerHTML = `
                <strong>Usage Warning:</strong> 
                ${data.warnings.map(w => w.message).join(', ')}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container').prepend(warningDiv);
        }
        
        // Log to console for monitoring
        console.log('Usage Stats:', data);
    } catch (error) {
        console.error('Error loading usage stats:', error);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadStats();
    loadTopHoldings();
    loadUsageStats();  // Monitor usage
    
    // Search form handler
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const searchInput = document.getElementById('search-input');
            const query = searchInput.value.trim();
            
            if (query) {
                await performSearch(query);
            }
        });
    }
    
    // Quick search links
    document.querySelectorAll('.quick-search').forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const query = e.target.textContent;
            document.getElementById('search-input').value = query;
            await performSearch(query);
        });
    });
    
    // Auto-focus search input
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.focus();
    }
});