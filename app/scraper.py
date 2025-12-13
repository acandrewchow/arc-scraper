"""
Arc'teryx Stock Scraper - Core scraping functions
Extracted for reuse in CLI and web applications
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import sys
import time
from typing import Optional, Dict, List, Tuple


def setup_driver(headless: bool = True):
    """Setup and return a Chrome driver."""
    chrome_options = Options()
    
    # Explicitly set Chrome binary path on Mac
    chrome_binary_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_binary_path):
        chrome_options.binary_location = chrome_binary_path
    
    if headless:
        chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.page_load_strategy = 'eager'
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(3)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}", file=sys.stderr, flush=True)
        return None


def get_all_colors(driver) -> List[str]:
    """Extract all available color options from the page."""
    colors = []
    filter_words = {'select', 'choose', 'size', 'quantity', 'size0', 'size1', 'size2', 'size3', 'size4', 'size5', 'size6'}
    
    try:
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "fieldset.qa--colour-selector")))
            color_items = driver.find_elements(By.CSS_SELECTOR, "fieldset.qa--colour-selector ol li[aria-label]")
        except TimeoutException:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "ol")))
            color_items = driver.find_elements(By.CSS_SELECTOR, "ol li[aria-label]")
        
        seen_colors = set()
        for item in color_items:
            aria_label = item.get_attribute('aria-label')
            if aria_label and aria_label.strip():
                color_name = aria_label.strip()
                color_lower = color_name.lower()
                if not any(word in color_lower for word in filter_words):
                    if color_name not in seen_colors:
                        seen_colors.add(color_name)
                        colors.append(color_name)
    except TimeoutException:
        pass
    except Exception as e:
        print(f"Error getting colors: {e}", file=sys.stderr)
    
    return colors


def get_all_sizes(driver) -> List[str]:
    """Extract all available size options from the page."""
    sizes = []
    base_sizes = {'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '2X', '2XL', '3X', '3XL'}
    size_order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '2X', '2XL', '3X', '3XL']
    size_variations = {'R', 'T', 'S'}
    
    def is_valid_size(size_str: str) -> bool:
        size_upper = size_str.upper().strip()
        if size_upper in base_sizes:
            return True
        if '-' in size_upper:
            parts = size_upper.split('-')
            if len(parts) == 2:
                base, variation = parts[0].strip(), parts[1].strip()
                return base in base_sizes and variation in size_variations
        return False
    
    def get_size_sort_key(size_str: str) -> int:
        size_upper = size_str.upper().strip()
        base = size_upper.split('-')[0] if '-' in size_upper else size_upper
        base_index = size_order.index(base) if base in size_order else 999
        if '-' in size_upper:
            variation = size_upper.split('-')[1].strip()
            variation_offset = {'R': 0, 'T': 100, 'S': 200}.get(variation, 300)
            return base_index * 1000 + variation_offset
        return base_index * 1000
    
    try:
        wait = WebDriverWait(driver, 5)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ol.qa--size-list, ol[data-testid='size-list']")))
        
        size_buttons = driver.find_elements(By.CSS_SELECTOR, "ol.qa--size-list button[data-size-value], ol[data-testid='size-list'] button[data-size-value]")
        
        seen_sizes = set()
        for button in size_buttons:
            size_value = button.get_attribute('data-size-value')
            if size_value and size_value.strip():
                size = size_value.strip()
                if is_valid_size(size) and size not in seen_sizes:
                    seen_sizes.add(size)
                    sizes.append(size)
        
        if not sizes:
            size_buttons = driver.find_elements(By.CSS_SELECTOR, "ol.qa--size-list button[role='radio'], ol[data-testid='size-list'] button[role='radio']")
            for button in size_buttons:
                text = button.text.strip()
                if is_valid_size(text) and text not in seen_sizes:
                    seen_sizes.add(text)
                    sizes.append(text)
        
        sizes = sorted(sizes, key=get_size_sort_key)
    except TimeoutException:
        pass
    except Exception as e:
        print(f"Error getting sizes: {e}", file=sys.stderr)
    
    return sizes


def check_color_stock_by_class(driver, color_name: str) -> Optional[bool]:
    """Check stock status by looking at the color option's class for 'no--stock'."""
    try:
        try:
            color_element = driver.find_element(By.XPATH, f"//fieldset[@class='qa--colour-selector' or contains(@class, 'qa--colour-selector')]//li[@aria-label='{color_name}']")
        except NoSuchElementException:
            color_element = driver.find_element(By.XPATH, f"//li[@aria-label='{color_name}']")
        
        element_class = color_element.get_attribute('class') or ''
        if 'no--stock' in element_class:
            return False
        
        try:
            child_buttons = color_element.find_elements(By.CSS_SELECTOR, "button, *[class*='no--stock']")
            for child in child_buttons:
                child_class = child.get_attribute('class') or ''
                if 'no--stock' in child_class:
                    return False
        except:
            pass
        
        return None
    except Exception:
        return None


def check_size_stock_by_class(driver, size: str) -> Optional[bool]:
    """Check stock status by looking at the size button's class for 'no--stock'."""
    try:
        size_button = driver.find_element(By.XPATH, f"//ol[@class='qa--size-list' or @data-testid='size-list']//button[@data-size-value='{size}']")
        button_class = size_button.get_attribute('class') or ''
        if 'no--stock' in button_class:
            return False
        if not size_button.get_attribute('disabled'):
            return True
        return None
    except Exception:
        return None


def check_button_for_stock(driver) -> Optional[bool]:
    """Check the Add to Cart button text to determine stock status."""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label], button[type='submit'], button")
        for btn in buttons:
            aria_label = (btn.get_attribute('aria-label') or '').lower()
            if 'add to cart' in aria_label:
                if not btn.get_attribute('disabled'):
                    return True
            if 'notify me' in aria_label:
                return False
            
            text = btn.text.lower().strip()
            if 'add to cart' in text:
                if not btn.get_attribute('disabled'):
                    return True
            if 'notify me' in text:
                return False
        return None
    except Exception as e:
        return None


def click_color_option(driver, color_name: str) -> bool:
    """Click on a color option and wait for page to update."""
    try:
        try:
            color_element = driver.find_element(By.XPATH, f"//fieldset[@class='qa--colour-selector' or contains(@class, 'qa--colour-selector')]//li[@aria-label='{color_name}']")
        except NoSuchElementException:
            color_element = driver.find_element(By.XPATH, f"//li[@aria-label='{color_name}']")
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", color_element)
        time.sleep(0.3)
        color_element.click()
        time.sleep(1)
        return True
    except Exception:
        return False


def click_size_option(driver, size: str) -> bool:
    """Click on a size option and wait for page to update."""
    try:
        size_button = driver.find_element(By.XPATH, f"//ol[@class='qa--size-list' or @data-testid='size-list']//button[@data-size-value='{size}']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", size_button)
        time.sleep(0.2)
        size_button.click()
        time.sleep(0.8)
        return True
    except NoSuchElementException:
        try:
            size_button = driver.find_element(By.XPATH, f"//ol[@class='qa--size-list' or @data-testid='size-list']//button[role='radio' and text()='{size}']")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", size_button)
            time.sleep(0.2)
            size_button.click()
            time.sleep(0.8)
            return True
        except:
            return False
    except Exception:
        return False


def check_stock_colors_only(driver, colors: List[str]) -> Dict[str, bool]:
    """Check stock status for products with colors only."""
    colors_stock = {}
    
    # First pass: check all colors using class method
    for color in colors:
        stock_status = check_color_stock_by_class(driver, color)
        if stock_status is not None:
            colors_stock[color] = stock_status
    
    # Second pass: click and check remaining colors
    for color in colors:
        if color not in colors_stock:
            if click_color_option(driver, color):
                time.sleep(0.8)
                stock_status = check_button_for_stock(driver)
                colors_stock[color] = stock_status if stock_status is not None else False
            else:
                colors_stock[color] = False
    
    return colors_stock


def check_stock_with_sizes(driver, colors: List[str], sizes: List[str]) -> Dict[str, Dict[str, bool]]:
    """Check stock status for products with colors and sizes."""
    color_size_stock = {}
    
    for color in colors:
        if not click_color_option(driver, color):
            continue
        
        time.sleep(0.8)
        current_sizes = get_all_sizes(driver)
        
        if not current_sizes:
            stock_status = check_button_for_stock(driver)
            color_size_stock[color] = {'ALL': stock_status if stock_status is not None else False}
            continue
        
        color_size_stock[color] = {}
        for size in current_sizes:
            stock_status = check_size_stock_by_class(driver, size)
            if stock_status is None:
                if click_size_option(driver, size):
                    time.sleep(0.8)
                    stock_status = check_button_for_stock(driver)
            color_size_stock[color][size] = stock_status if stock_status is not None else False
    
    return color_size_stock


def check_stock_status(product_url: str, headless: bool = True) -> Tuple[Optional[Dict], Optional[bool], Optional[str]]:
    """
    Check stock status for a product.
    Returns (stock_data, has_sizes, product_name) or (None, None, None) on error.
    """
    driver = setup_driver(headless=headless)
    if not driver:
        return None, None, None
    
    try:
        driver.get(product_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        
        # Try to get product name from page
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text
        except:
            product_name = None
        
        colors = get_all_colors(driver)
        if not colors:
            return None, None, None
        
        sizes = get_all_sizes(driver)
        has_sizes = len(sizes) > 0
        
        if has_sizes:
            stock_data = check_stock_with_sizes(driver, colors, sizes)
        else:
            stock_data = check_stock_colors_only(driver, colors)
        
        return stock_data, has_sizes, product_name
        
    except Exception as e:
        print(f"Error checking stock: {e}", file=sys.stderr)
        return None, None, None
    finally:
        try:
            driver.quit()
        except:
            pass