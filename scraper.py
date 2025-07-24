"""
Multi-fund scraper for Vanguard index funds
Supports VTSAX, VOO, VTI, and other Vanguard funds
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pandas as pd
import time
import os
import glob
from datetime import datetime
import sys

from funds_config import SUPPORTED_FUNDS
from database import MultiFundDatabase

def setup_driver(download_dir):
    """Set up Chrome driver with download directory"""
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Add options to avoid detection
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scrape_fund(fund_symbol, fund_config, download_dir):
    """Scrape holdings for a single fund"""
    print(f"\n{'='*50}")
    print(f"Scraping {fund_symbol}: {fund_config['name']}")
    print(f"{'='*50}")
    
    driver = setup_driver(download_dir)
    
    try:
        # Navigate to fund page
        url = fund_config['url'] + '#literatureandinsights'
        print(f"Opening {url}")
        driver.get(url)
        
        wait = WebDriverWait(driver, 30)
        
        print("Waiting for page to fully load...")
        time.sleep(15)
        
        # Try to find and click export button
        print("Looking for export button...")
        try:
            export_element = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[normalize-space(text())='Export full holdings']")
            ))
            driver.execute_script('arguments[0].scrollIntoView(true);', export_element)
            driver.execute_script('arguments[0].click();', export_element)
            print("Clicked export button!")
            
            # Wait for download
            print("Waiting for download to complete...")
            time.sleep(10)
            
            # Find the downloaded file
            csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
            if csv_files:
                latest_csv = max(csv_files, key=os.path.getctime)
                print(f"Found CSV file: {latest_csv}")
                
                # Process the CSV
                success = process_csv(latest_csv, fund_symbol, fund_config)
                
                # Clean up - rename processed file
                if success:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_filename = os.path.join(download_dir, f"processed_{fund_symbol}_{timestamp}.csv")
                    os.rename(latest_csv, new_filename)
                    print(f"Renamed to: {new_filename}")
                
                return success
            else:
                print(f"No CSV file found for {fund_symbol}")
                return False
                
        except Exception as e:
            print(f"Error clicking export button for {fund_symbol}: {e}")
            driver.save_screenshot(f"error_{fund_symbol}.png")
            return False
            
    finally:
        driver.quit()

def process_csv(csv_path, fund_symbol, fund_config):
    """Process the downloaded CSV file"""
    try:
        # Read file line by line to find where data starts
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        header_row_idx = None
        for idx, line in enumerate(lines):
            if 'SEDOL' in line and 'TICKER' in line:
                header_row_idx = idx
                break
        
        if header_row_idx is not None:
            # Re-read with correct header
            df = pd.read_csv(csv_path, skiprows=header_row_idx)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Handle VOO format (has empty first column)
            if df.columns[0] == '' or pd.isna(df.columns[0]):
                # Drop the empty first column
                df = df.iloc[:, 1:]
                # Reset column names
                df.columns = df.columns.str.strip()
            
            # Debug: print column names
            print(f"Columns found: {df.columns.tolist()}")
            
            # Clean and prepare data
            # Handle different column name formats
            pct_col = '% OF FUNDS*' if '% OF FUNDS*' in df.columns else '% OF FUND*' if '% OF FUND*' in df.columns else None
            mkt_val_col = 'MARKET VALUE' if 'MARKET VALUE' in df.columns else 'MARKET VALUE*' if 'MARKET VALUE*' in df.columns else None
            
            if pct_col:
                df['% OF FUNDS*'] = df[pct_col].str.rstrip('%')
                df['% OF FUNDS*'] = df['% OF FUNDS*'].str.replace('<', '')
                df['% OF FUNDS*'] = pd.to_numeric(df['% OF FUNDS*'], errors='coerce')
            
            if mkt_val_col:
                # Rename the column to standard name
                if mkt_val_col != 'MARKET VALUE':
                    df['MARKET VALUE'] = df[mkt_val_col]
                df['MARKET VALUE'] = df['MARKET VALUE'].str.replace('$', '').str.replace(',', '')
                df['MARKET VALUE'] = pd.to_numeric(df['MARKET VALUE'], errors='coerce')
            
            df['SHARES'] = df['SHARES'].str.replace(',', '')
            df['SHARES'] = pd.to_numeric(df['SHARES'], errors='coerce').fillna(0).astype('int64')
            
            # Remove empty rows
            df = df.dropna(subset=['TICKER', 'HOLDINGS'])
            df = df[df['TICKER'].str.strip() != '']
            
            print(f"Processed {len(df)} holdings for {fund_symbol}")
            
            # Store in database
            db = MultiFundDatabase()
            
            # Add fund info
            db.add_fund(fund_symbol, fund_config['name'], 
                       fund_config['description'], 
                       fund_config.get('expense_ratio'))
            
            # Insert holdings
            db.insert_holdings(df, fund_symbol)
            
            return True
        else:
            print(f"Could not find data in CSV for {fund_symbol}")
            return False
            
    except Exception as e:
        print(f"Error processing CSV for {fund_symbol}: {e}")
        return False

def main():
    """Main function to scrape multiple funds"""
    download_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get fund list from command line or use defaults
    if len(sys.argv) > 1:
        funds_to_scrape = sys.argv[1:] 
    else:
        # Default to VTSAX and VOO for testing
        funds_to_scrape = ['VTSAX', 'VOO']
    
    print(f"Planning to scrape: {', '.join(funds_to_scrape)}")
    
    # Validate funds
    valid_funds = []
    for fund in funds_to_scrape:
        if fund in SUPPORTED_FUNDS:
            valid_funds.append(fund)
        else:
            print(f"Warning: {fund} not in supported funds list")
    
    if not valid_funds:
        print("No valid funds to scrape!")
        return
    
    # Scrape each fund
    results = {}
    for fund_symbol in valid_funds:
        fund_config = SUPPORTED_FUNDS[fund_symbol]
        success = scrape_fund(fund_symbol, fund_config, download_dir)
        results[fund_symbol] = success
        
        # Wait between funds to be polite
        if fund_symbol != valid_funds[-1]:
            print(f"\nWaiting 30 seconds before next fund...")
            time.sleep(30)
    
    # Summary
    print(f"\n{'='*50}")
    print("SCRAPING SUMMARY")
    print(f"{'='*50}")
    for fund, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"{fund}: {status}")
    
    # Show database stats
    db = MultiFundDatabase()
    stats = db.get_stats()
    print(f"\nDatabase now contains:")
    print(f"- {stats['total_funds']} funds")
    print(f"- {stats['unique_stocks']} unique stocks")
    
    for fund_stat in stats['fund_stats']:
        print(f"- {fund_stat[0]}: {fund_stat[2]} holdings")

if __name__ == '__main__':
    main()