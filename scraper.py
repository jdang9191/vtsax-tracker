# https://advisors.vanguard.com/investments/products/vtsax/vanguard-total-stock-market-index-fund-admiral-shares#literatureandinsights
# every month autmate to click export full holdings button

#automate using selenium to click button and save file
# parse file using pandas

#updates monthly so do it every month

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
#handles installing and running right version of chrome driver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import pandas as pd
import time
import os

#chrome version number: 138.0.7204.158

# Set up download directory to current project folder
download_dir = os.path.dirname(os.path.abspath(__file__))
prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}

# Configure Chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("prefs", prefs)

# Add options to avoid detection
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Optional: Run in headless mode
# chrome_options.add_argument('--headless')

#opens website
driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=chrome_options
)

# Execute script to remove webdriver property
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
driver.get('https://advisors.vanguard.com/investments/products/vtsax/vanguard-total-stock-market-index-fund-admiral-shares#literatureandinsights')

wait = WebDriverWait(driver, 30)  # Increased timeout

print("Waiting for page to fully load...")
time.sleep(15)  # Increased wait time for page to load

# Try multiple methods to find the button
print("Looking for export button...")
try:
    # Method 1: Wait for button with exact text
    export_element = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//*[normalize-space(text())='Export full holdings']")
    ))
except:
    try:
        # Method 2: Try partial text match
        export_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Export')]")
    except:
        try:
            # Method 3: Try finding by class or other attributes
            export_element = driver.find_element(By.XPATH, "//button[contains(., 'Export')]")
        except:
            # Take a screenshot for debugging
            driver.save_screenshot("page_screenshot.png")
            print("Could not find export button. Screenshot saved as page_screenshot.png")
            print("Current URL:", driver.current_url)
            print("Page title:", driver.title)
            driver.quit()
            exit(1)
driver.execute_script('arguments[0].scrollIntoView(true);', export_element)
driver.execute_script('arguments[0].click();', export_element)

# Wait for download to complete
print("Waiting for download to complete...")
time.sleep(5)  # Give it time to start downloadingwa

# Find the downloaded CSV file
import glob
csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
if csv_files:
    # Get the most recent CSV file
    latest_csv = max(csv_files, key=os.path.getctime)
    print(f"Found CSV file: {latest_csv}")
    
    # Parse the CSV - first find where the data starts
    # The CSV has multiple header rows, so we need to find the actual data
    with open(latest_csv, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Find the row with column headers (contains 'SEDOL')
    header_row_idx = None
    for i, line in enumerate(lines):
        if 'SEDOL' in line and 'TICKER' in line:
            header_row_idx = i
            break
    
    if header_row_idx is not None:
        # Read the CSV starting from the header row
        df = pd.read_csv(latest_csv, skiprows=header_row_idx)
        
        # Clean column names (remove any extra spaces)
        df.columns = df.columns.str.strip()
        
        # Display info about the data
        print(f"\nLoaded {len(df)} holdings")
        print("\nColumns:", df.columns.tolist())
        print("\nFirst 5 holdings:")
        print(df.head())
        
        # Clean and prepare data for database
        # Remove % sign from percentage column (note the column name has 'FUNDS*')
        # Handle special cases like '<0.01%'
        df['% OF FUNDS*'] = df['% OF FUNDS*'].str.rstrip('%')
        df['% OF FUNDS*'] = df['% OF FUNDS*'].str.replace('<', '')  # Remove < symbol
        df['% OF FUNDS*'] = pd.to_numeric(df['% OF FUNDS*'], errors='coerce')
        
        # Clean market value (remove $ and commas)
        df['MARKET VALUE'] = df['MARKET VALUE'].str.replace('$', '').str.replace(',', '').astype(float)
        
        # Clean shares (remove commas and handle decimals)
        df['SHARES'] = df['SHARES'].str.replace(',', '')
        df['SHARES'] = pd.to_numeric(df['SHARES'], errors='coerce').fillna(0).astype('int64')
        
        # Remove any rows where ticker or holdings name is null/empty
        df = df.dropna(subset=['TICKER', 'HOLDINGS'])
        df = df[df['TICKER'].str.strip() != '']
        
        print(f"\nData cleaned and ready for database storage ({len(df)} valid holdings)")
        
        # Import and use the database
        from database import HoldingsDatabase
        db = HoldingsDatabase()
        db.insert_holdings(df)
        
        # Quick verification
        print("\n--- Verification ---")
        all_holdings = db.get_all_holdings()
        print(f"✓ Successfully stored {len(all_holdings)} holdings in database")
        print(f"✓ Top holding: {all_holdings[0][0]} ({all_holdings[0][1]}) - {all_holdings[0][2]:.2f}%")
        
else:
    print("No CSV file found in download directory")

# Close the browser
driver.quit()




