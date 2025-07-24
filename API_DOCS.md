# VTSAX Holdings API Documentation

## Overview
This API provides access to VTSAX (Vanguard Total Stock Market Index Fund) holdings data.

## Base URL
```
http://localhost:5000/api
```

## Endpoints

### 1. Search Holdings
Search for stocks by ticker symbol or company name.

**Endpoint:** `GET /api/search?q=<query>`

**Example Requests:**
```bash
# Search by ticker
curl "http://localhost:5000/api/search?q=AAPL"

# Search by company name
curl "http://localhost:5000/api/search?q=Tesla"
```

**Response:**
```json
{
  "found": true,
  "query": "AAPL",
  "results": [{
    "ticker": "AAPL",
    "company_name": "Apple Inc",
    "percentage": 5.13,
    "market_value": 98521000641.63,
    "shares": 480192039,
    "rank": 1
  }]
}
```

### 2. Get Top Holdings
Retrieve the top holdings by percentage.

**Endpoint:** `GET /api/holdings/top?limit=<number>`

**Parameters:**
- `limit` (optional): Number of holdings to return (default: 10, max: 100)

**Example Request:**
```bash
curl "http://localhost:5000/api/holdings/top?limit=5"
```

**Response:**
```json
{
  "count": 5,
  "holdings": [
    {
      "ticker": "MSFT",
      "company_name": "Microsoft Corp",
      "percentage": 6.19,
      "market_value": 118858709513.87,
      "rank": 1
    },
    ...
  ]
}
```

### 3. Check Stock Ownership
Check if a specific stock is owned through VTSAX.

**Endpoint:** `GET /api/owns/<ticker>`

**Example Request:**
```bash
curl "http://localhost:5000/api/owns/TSLA"
```

**Response (if owned):**
```json
{
  "owns": true,
  "ticker": "TSLA",
  "company_name": "Tesla Inc",
  "percentage": 1.46,
  "market_value": 27961535797.86,
  "shares": 88023471,
  "message": "Yes, you own Tesla Inc through VTSAX (1.46% of fund)"
}
```

**Response (if not owned):**
```json
{
  "owns": false,
  "ticker": "XYZ",
  "message": "No, you do not own XYZ through VTSAX"
}
```

### 4. Get Statistics
Get database statistics and metadata.

**Endpoint:** `GET /api/stats`

**Example Request:**
```bash
curl "http://localhost:5000/api/stats"
```

**Response:**
```json
{
  "total_holdings": 3524,
  "last_updated": "2024-01-24 10:30:00",
  "total_market_value": 1234567890123.45,
  "data_source": "VTSAX",
  "fund_name": "Vanguard Total Stock Market Index Fund Admiral Shares"
}
```

### 5. Health Check
Check if the API is running.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "VTSAX Holdings API"
}
```

## Error Responses

**400 Bad Request:**
```json
{
  "error": "Missing search query parameter \"q\""
}
```

**404 Not Found:**
```json
{
  "error": "Endpoint not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error"
}
```

## Usage Examples

### Python
```python
import requests

# Search for Apple
response = requests.get('http://localhost:5000/api/search?q=AAPL')
data = response.json()
print(f"Apple percentage: {data['results'][0]['percentage']}%")

# Get top 10 holdings
response = requests.get('http://localhost:5000/api/holdings/top')
holdings = response.json()['holdings']
for h in holdings:
    print(f"{h['ticker']}: {h['percentage']}%")
```

### JavaScript
```javascript
// Check if you own Tesla
fetch('http://localhost:5000/api/owns/TSLA')
  .then(response => response.json())
  .then(data => {
    if (data.owns) {
      console.log(`You own ${data.percentage}% of Tesla through VTSAX`);
    }
  });
```

## Running the API

1. Make sure you have data in your database (run `scraper.py` first)
2. Start the API server:
   ```bash
   python api.py
   ```
3. The API will be available at `http://localhost:5000`