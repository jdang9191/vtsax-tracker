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

#chrome version number: 138.0.7204.158

#opens website
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
driver.get('https://advisors.vanguard.com/investments/products/vtsax/vanguard-total-stock-market-index-fund-admiral-shares#literatureandinsights')

wait = WebDriverWait(driver, 15)

time.sleep(10) # wait for page to load and render button


export_element = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//*[normalize-space(text())='Export full holdings']")
))
driver.execute_script('arguments[0].scrollIntoView(true);', export_element)
driver.execute_script('arguments[0].click();', export_element)


#searches page for clickable button with same text
#export_button = None
#buttons = driver.find_elements(By.CLASS_NAME, "button--black")
#for button in buttons:
 #   if button.text.strip().lower() == "export full holdings":
  #      export_button = button
   #     break
#if export_button:
 #   driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
  #  export_button.click()
#else:
 #   print("export holdings button not found on the page")

