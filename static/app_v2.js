// Multi-Fund Holdings Tracker JavaScript

const API_BASE = '/api';

// Fund colors for consistent styling
const FUND_COLORS = {
    'VTSAX': '#1f77b4',
    'VOO': '#ff7f0e',
    'VTI': '#2ca02c',
    'VUG': '#d62728',
    'VTV': '#9467bd'
};

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
    return value.toFixed(3) + '%';
}

// Load available funds
async function loadFunds() {
    try {
        const response = await fetch(`${API_BASE}/funds`);
        const data = await response.json();
        
        // Display fund badges
        const badgesContainer = document.getElementById('fund-badges');
        badgesContainer.innerHTML = '';
        
        data.funds.forEach(fund => {
            const badge = document.createElement('span');
            badge.className = 'fund-badge';
            badge.style.backgroundColor = FUND_COLORS[fund.fund_symbol] || '#6c757d';
            badge.style.color = 'white';
            badge.textContent = fund.fund_symbol;
            badge.title = `${fund.fund_name} (${fund.holdings_count} holdings)`;
            badgesContainer.appendChild(badge);
        });
        
        // Display fund summary cards
        const summaryContainer = document.getElementById('fund-summary');
        summaryContainer.innerHTML = '';
        
        data.funds.forEach(fund => {
            const card = `
                <div class="col-md-4 mb-3">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${fund.fund_symbol}</h5>
                            <p class="card-text">${fund.fund_name}</p>
                            <div class="d-flex justify-content-between">
                                <small>${fund.holdings_count} holdings</small>
                                <small>ER: ${fund.expense_ratio || 'N/A'}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            summaryContainer.innerHTML += card;
        });
        
        // Load top holdings for each fund
        loadTopHoldingsByFund(data.funds);
        
    } catch (error) {
        console.error('Error loading funds:', error);
    }
}

// Load top holdings for each fund
async function loadTopHoldingsByFund(funds) {
    const accordionContainer = document.getElementById('fundAccordion');
    accordionContainer.innerHTML = '';
    
    for (const fund of funds) {
        try {
            const response = await fetch(`${API_BASE}/holdings/${fund.fund_symbol}/top?limit=10`);
            const data = await response.json();
            
            const accordionItem = `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading${fund.fund_symbol}">
                        <button class="accordion-button collapsed" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#collapse${fund.fund_symbol}">
                            ${fund.fund_symbol} - Top 10 Holdings
                        </button>
                    </h2>
                    <div id="collapse${fund.fund_symbol}" class="accordion-collapse collapse" 
                         data-bs-parent="#fundAccordion">
                        <div class="accordion-body">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Ticker</th>
                                        <th>Company</th>
                                        <th>% of Fund</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.holdings.map(h => `
                                        <tr>
                                            <td><strong>${h.ticker}</strong></td>
                                            <td>${h.company_name}</td>
                                            <td>${formatPercentage(h.percentage)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            
            accordionContainer.innerHTML += accordionItem;
            
        } catch (error) {
            console.error(`Error loading holdings for ${fund.fund_symbol}:`, error);
        }
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
            // Show summary
            const summaryCard = `
                <div class="alert alert-success">
                    <h5>✓ Found "${query}" in ${data.total_funds} fund${data.total_funds > 1 ? 's' : ''}</h5>
                </div>
            `;
            resultsDiv.innerHTML = summaryCard;
            
            // Display results by fund
            data.funds.forEach(fund => {
                const fundCard = `
                    <div class="card fund-result-card fund-${fund.fund_symbol} mb-3 fade-in">
                        <div class="card-body">
                            <h5 class="card-title">
                                <span class="badge" style="background-color: ${FUND_COLORS[fund.fund_symbol] || '#6c757d'}">
                                    ${fund.fund_symbol}
                                </span>
                                ${fund.fund_name}
                            </h5>
                            <div class="holdings-grid">
                                ${fund.holdings.map(holding => `
                                    <div class="holding-card">
                                        <strong>${holding.ticker}</strong>
                                        <br>${holding.company_name}
                                        <br><span class="text-primary">${formatPercentage(holding.percentage)}</span>
                                        <br><small class="text-muted">${holding.shares.toLocaleString()} shares</small>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                `;
                resultsDiv.innerHTML += fundCard;
            });
            
            // Also check which funds DON'T have this stock
            checkMissingFunds(query);
            
        } else {
            // Not found in any fund
            const notFoundCard = `
                <div class="card result-card not-owned mb-3 fade-in">
                    <div class="card-body">
                        <h4 class="card-title">
                            <span class="text-warning">✗</span>
                            "${query}" not found in any tracked funds
                        </h4>
                        <p class="mb-0">
                            This stock is not part of any index funds you're tracking
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

// Check which funds don't contain the stock
async function checkMissingFunds(ticker) {
    try {
        // Get list of funds that contain the stock
        const response = await fetch(`${API_BASE}/stock/${ticker}/funds`);
        const data = await response.json();
        
        if (data.found) {
            const fundsWithStock = data.funds.map(f => f.fund_symbol);
            
            // Get all available funds
            const allFundsResponse = await fetch(`${API_BASE}/funds`);
            const allFundsData = await allFundsResponse.json();
            
            const missingFunds = allFundsData.funds.filter(
                f => !fundsWithStock.includes(f.fund_symbol)
            );
            
            if (missingFunds.length > 0) {
                const missingCard = `
                    <div class="alert alert-info mt-3">
                        <strong>Not found in:</strong> 
                        ${missingFunds.map(f => f.fund_symbol).join(', ')}
                    </div>
                `;
                document.getElementById('search-results').innerHTML += missingCard;
            }
        }
    } catch (error) {
        console.error('Error checking missing funds:', error);
    }
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        // Update last updated in footer
        if (data.last_updated) {
            const date = new Date(data.last_updated);
            document.getElementById('last-updated').textContent = date.toLocaleDateString();
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadStats();
    loadFunds();
    
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