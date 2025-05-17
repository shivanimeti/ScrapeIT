#utils
import os
import csv
import time
import re
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
OUTPUT_FILE = "search_results.csv"
CONTACT_OUTPUT_FILE = "contact_info.csv"
MAX_WORKERS = 10  # Increased from 5 to 10 for better parallelism
TIMEOUT = 10  # Reduced from 15 to 10 seconds for faster responses

def clean_url(url):
    """Clean and validate URL"""
    if not url:
        return None
    
    # Convert to string in case it's not
    url = str(url).strip()
    
    # Skip if it's clearly not a URL
    if len(url) < 3:
        return None
    
    # Add protocol if missing
    if not url.lower().startswith(('http://', 'https://')):
        if url.startswith('www.'):
            url = 'https://' + url
        elif '.' in url and ' ' not in url and '@' not in url:
            # If it looks like a domain, add https://
            url = 'https://' + url
        else:
            return None
    
    # Basic URL validation
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        
        # Return the URL with scheme and netloc
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except:
        return None

def initialize_driver(headless=True, disable_images=True):
    """Initialize Chrome WebDriver with optimized settings"""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,720")  # Smaller window size
    options.add_argument("--disable-extensions")  # Disable extensions
    options.add_argument("--disable-infobars")  # Disable infobars
    options.add_argument("--disable-notifications")  # Disable notifications
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Disable images for faster loading
    if disable_images:
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.media_stream": 2,
        }
        options.add_experimental_option("prefs", prefs)
    
    # Add additional performance optimizations
    options.add_argument("--disable-javascript")  # Disable JavaScript where possible
    options.add_argument("--disable-animations")  # Disable animations
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(TIMEOUT)  # Set page load timeout
    
    return driver

def search_duckduckgo(keyword, location, country, max_results=20):
    """
    Search DuckDuckGo for the given keyword in the specified location and country
    """
    # Try direct API search first (faster)
    results = _search_api(keyword, location, country, max_results)
    
    # If API search fails, try browser-based search
    if not results:
        results = _search_duckduckgo(keyword, location, country, max_results)
    
    # If DuckDuckGo fails, try Google
    if not results:
        results = _search_google(keyword, location, country, max_results)
    
    return results

def _search_api(keyword, location, country, max_results=20):
    """
    Search using a search API (faster than browser automation)
    """
    search_query = f"{keyword} {location} {country}"
    results = []
    
    try:
        # Using SerpAPI-like structure (you'll need to replace with your actual API key and endpoint)
        # This is a placeholder - you should implement with a real search API
        api_url = f"https://serpapi.com/search.json?q={quote_plus(search_query)}&api_key=YOUR_API_KEY"
        
        # For now, we'll simulate with a direct Google search using requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # This is a simplified approach and won't work reliably for production
        # For production, use a proper search API
        response = requests.get(f"https://www.google.com/search?q={quote_plus(search_query)}", headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results (this is simplified and may break with Google changes)
            for result in soup.select('div.g'):
                try:
                    title_element = result.select_one('h3')
                    link_element = result.select_one('a')
                    snippet_element = result.select_one('div.VwiC3b')
                    
                    if title_element and link_element:
                        title = title_element.text
                        url = link_element.get('href')
                        
                        # Clean URL (remove Google redirects)
                        if url.startswith('/url?q='):
                            url = url.split('/url?q=')[1].split('&')[0]
                        
                        description = snippet_element.text if snippet_element else "No description available"
                        
                        if url and clean_url(url):
                            results.append({
                                "title": title,
                                "url": clean_url(url),
                                "description": description,
                                "keyword": keyword,
                                "location": location,
                                "country": country
                            })
                            
                            if len(results) >= max_results:
                                break
                except Exception as e:
                    print(f"Error extracting API result: {e}")
                    continue
    
    except Exception as e:
        print(f"API search error: {e}")
    
    return results

def _search_duckduckgo(keyword, location, country, max_results=20):
    """
    Search DuckDuckGo for the given keyword in the specified location and country
    """
    driver = initialize_driver()
    if not driver:
        return []
    
    search_query = f"{keyword} {location} {country}"
    results = []
    
    try:
        # Navigate to DuckDuckGo
        driver.get("https://duckduckgo.com/")
        
        # Find search box and enter query
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.submit()
        
        # Wait for results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".result, .result__body, article"))
        )
        
        # Extract search results
        selectors = [
            ".result", 
            ".result__body", 
            "article", 
            ".nrn-react-div"
        ]
        
        result_elements = []
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                result_elements = elements
                break
        
        for element in result_elements[:max_results]:
            try:
                # Try different selectors for title and link
                title_selectors = [".result__title", "h2", "h3", ".result__a"]
                title_element = None
                for selector in title_selectors:
                    try:
                        title_element = element.find_element(By.CSS_SELECTOR, selector)
                        if title_element:
                            break
                    except:
                        continue
                
                if not title_element:
                    continue
                
                # Try to find link
                link_element = None
                try:
                    link_element = title_element.find_element(By.TAG_NAME, "a")
                except:
                    try:
                        link_element = element.find_element(By.TAG_NAME, "a")
                    except:
                        continue
                
                if not link_element:
                    continue
                
                # Try to find description
                description = "No description available"
                description_selectors = [".result__snippet", ".snippet", ".result__description"]
                for selector in description_selectors:
                    try:
                        description_element = element.find_element(By.CSS_SELECTOR, selector)
                        description = description_element.text
                        break
                    except:
                        continue
                
                title = title_element.text
                url = link_element.get_attribute("href")
                
                if url and clean_url(url):
                    results.append({
                        "title": title,
                        "url": clean_url(url),
                        "description": description,
                        "keyword": keyword,
                        "location": location,
                        "country": country
                    })
            except Exception as e:
                print(f"Error extracting result: {e}")
                continue
            
    except Exception as e:
        print(f"Error during DuckDuckGo search: {e}")
    finally:
        driver.quit()
        
    return results

def _search_google(keyword, location, country, max_results=20):
    """
    Fallback search using Google
    """
    driver = initialize_driver()
    if not driver:
        return []
    
    search_query = f"{keyword} {location} {country}"
    results = []
    
    try:
        # Navigate to Google
        search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
        driver.get(search_url)
        
        # Accept cookies if prompted
        try:
            accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]"))
            )
            accept_button.click()
            time.sleep(1)
        except:
            pass  # No cookie prompt or already accepted
        
        # Wait for results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g, .v5yQqb, .MjjYud"))
        )
        
        # Extract search results
        selectors = [
            "div.g", 
            ".v5yQqb", 
            ".MjjYud", 
            "//div[@class='g' or contains(@class, 'g ')]"
        ]
        
        result_elements = []
        for selector in selectors:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            if elements:
                result_elements = elements
                break
        
        for element in result_elements[:max_results]:
            try:
                title_selectors = ["h3", ".LC20lb"]
                title_element = None
                for selector in title_selectors:
                    try:
                        title_element = element.find_element(By.CSS_SELECTOR, selector)
                        if title_element:
                            break
                    except:
                        continue
                
                if not title_element:
                    continue
                
                link_selectors = ["a", ".yuRUbf a"]
                link_element = None
                for selector in link_selectors:
                    try:
                        link_element = element.find_element(By.CSS_SELECTOR, selector)
                        if link_element:
                            break
                    except:
                        continue
                
                if not link_element:
                    continue
                
                description_selectors = ["div.VwiC3b", ".lEBKkf", ".s3v9rd"]
                description = "No description available"
                for selector in description_selectors:
                    try:
                        description_element = element.find_element(By.CSS_SELECTOR, selector)
                        description = description_element.text
                        break
                    except:
                        continue
                
                title = title_element.text
                url = link_element.get_attribute("href")
                
                if url and clean_url(url):
                    results.append({
                        "title": title,
                        "url": clean_url(url),
                        "description": description,
                        "keyword": keyword,
                        "location": location,
                        "country": country
                    })
            except Exception as e:
                print(f"Error extracting Google result: {e}")
                continue
                
    except Exception as e:
        print(f"Error during Google search: {e}")
    finally:
        driver.quit()
    
    return results

def extract_contact_info(url):
    """
    Extract email and phone number from a webpage
    """
    contact_info = {"url": url, "email": "", "phone": ""}
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # First try with requests (faster)
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text()
        
        # Find emails using regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text_content)
        
        # Filter out common false positives
        filtered_emails = []
        for email in emails:
            # Skip emails with common false positive domains
            if not any(fp in email.lower() for fp in ['@example.', '@domain.', '@email.', '@test.']):
                filtered_emails.append(email)
        
        if filtered_emails:
            contact_info["email"] = ", ".join(set(filtered_emails))
        
        # Find phone numbers using regex
        phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text_content)
        if phones:
            contact_info["phone"] = ", ".join(set(phones))
        
        # If no contact info found, try to find contact page and scrape it
        if not contact_info["email"] and not contact_info["phone"]:
            # Look for contact page links
            contact_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                link_text = link.text.lower()
                
                if 'contact' in link_text or 'kontakt' in link_text or 'about' in link_text:
                    # Handle relative URLs
                    if href.startswith('/'):
                        parsed_url = urlparse(url)
                        contact_url = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                    elif href.startswith('http'):
                        contact_url = href
                    else:
                        contact_url = f"{url.rstrip('/')}/{href.lstrip('/')}"
                    
                    contact_links.append(contact_url)
            
            # Visit contact pages and extract info - limit to just 1 page for speed
            for contact_url in contact_links[:1]:  # Reduced from 2 to 1
                try:
                    contact_response = requests.get(contact_url, headers=headers, timeout=TIMEOUT/2)  # Reduced timeout
                    contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                    contact_text = contact_soup.get_text()
                    
                    # Extract emails
                    contact_emails = re.findall(email_pattern, contact_text)
                    filtered_contact_emails = [e for e in contact_emails if not any(fp in e.lower() for fp in ['@example.', '@domain.', '@email.', '@test.'])]
                    
                    if filtered_contact_emails:
                        if contact_info["email"]:
                            contact_info["email"] += ", " + ", ".join(set(filtered_contact_emails) - set(contact_info["email"].split(", ")))
                        else:
                            contact_info["email"] = ", ".join(set(filtered_contact_emails))
                    
                    # Extract phones
                    contact_phones = re.findall(phone_pattern, contact_text)
                    if contact_phones:
                        if contact_info["phone"]:
                            contact_info["phone"] += ", " + ", ".join(set(contact_phones) - set(contact_info["phone"].split(", ")))
                        else:
                            contact_info["phone"] = ", ".join(set(contact_phones))
                    
                    # If we found both email and phone, we can stop
                    if contact_info["email"] and contact_info["phone"]:
                        break
                        
                except Exception as e:
                    continue
            
    except Exception as e:
        pass
    
    return contact_info

def extract_contact_info_batch(urls):
    """
    Extract contact information from multiple URLs in parallel
    """
    results = []
    
    # Process in smaller batches to avoid overwhelming the system
    batch_size = 20  # Process 20 URLs at a time
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i+batch_size]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_url = {executor.submit(extract_contact_info, url): url for url in batch_urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    results.append(data)
                except Exception as e:
                    results.append({"url": url, "email": "", "phone": ""})
    
    return results

def write_search_results_to_csv(results, filename=OUTPUT_FILE):
    """
    Write search results to CSV file
    """
    if not results:
        print("No results to write.")
        return None
        
    fieldnames = ["keyword", "location", "country", "title", "url", "description"]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow({field: result.get(field, "") for field in fieldnames})
        print(f"Results saved to {filename}")
        return filename
    except Exception as e:
        print(f"Error writing CSV: {e}")
        return None

def write_contact_info_to_csv(contact_info_list, filename=CONTACT_OUTPUT_FILE):
    """
    Write contact information to CSV file
    """
    if not contact_info_list:
        print("No contact info to write.")
        return None
        
    fieldnames = ["url", "email", "phone"]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for info in contact_info_list:
                writer.writerow(info)
        print(f"Contact info saved to {filename}")
        return filename
    except Exception as e:
        print(f"Error writing contact CSV: {e}")
        return None

def read_urls_from_csv(file_obj):
    """
    Reads URLs from the uploaded CSV file object.
    Returns a list of URLs.
    """
    file_obj.seek(0)
    urls = []
    
    try:
        # Read the entire file content as text
        content = file_obj.read().decode('utf-8', errors='ignore')
        
        # First try to find URLs with http/https
        http_pattern = r'https?://[^\s,"\'\)\(]+'
        http_urls = re.findall(http_pattern, content)
        
        # Then try to find www. URLs
        www_pattern = r'www\.[^\s,"\'\)\(]+\.[a-zA-Z]{2,}'
        www_urls = re.findall(www_pattern, content)
        
        # Process found URLs
        for url in http_urls + ['https://' + u for u in www_urls]:
            clean = url.strip()
            if clean and clean not in urls:
                urls.append(clean)
        
        # If no URLs found, try CSV parsing as fallback
        if not urls:
            file_obj.seek(0)
            reader = csv.reader(file_obj)
            for row in reader:
                for cell in row:
                    if 'http' in cell or 'www.' in cell:
                        clean = cell.strip()
                        if clean and clean not in urls:
                            urls.append(clean)
        
        print(f"Found {len(urls)} URLs in the CSV file")
        
        # Debug output to help diagnose issues
        if not urls:
            print("DEBUG: No URLs found. File content sample:")
            print(content[:500] if len(content) > 500 else content)
        
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    
    return urls

def filter_search_results(results, shopify_only=False, fast_loading=False, active_only=False):
    """
    Filter search results based on criteria
    """
    filtered_results = []
    
    for result in results:
        url = result.get('url', '')
        if not url:
            continue
            
        include_result = True
        
        # Check if we need to apply any filters
        if shopify_only or fast_loading or active_only:
            try:
                # Make a HEAD request to check response quickly
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                start_time = time.time()
                response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
                load_time = time.time() - start_time
                
                # Check if it's a Shopify site
                if shopify_only:
                    is_shopify = False
                    # Check URL for Shopify indicators
                    if 'myshopify.com' in url:
                        is_shopify = True
                    # Check headers for Shopify indicators
                    elif response.headers.get('X-Shopify-Stage') or response.headers.get('X-ShopId'):
                        is_shopify = True
                    # If not found in HEAD, try GET for more thorough check
                    elif not is_shopify:
                        get_response = requests.get(url, headers=headers, timeout=5)
                        is_shopify = 'shopify' in get_response.text.lower() or 'cdn.shopify.com' in get_response.text
                    
                    if not is_shopify:
                        include_result = False
                
                # Check if it's fast loading
                if fast_loading and include_result:
                    if load_time > 5:  # More than 5 seconds
                        include_result = False
                
                # Check if it's active
                if active_only and include_result:
                    if response.status_code >= 400:  # 4xx or 5xx status codes
                        include_result = False
                
            except Exception as e:
                # If we can't check the site, exclude it if filters are applied
                include_result = False
        
        if include_result:
            filtered_results.append(result)
    
    return filtered_results
