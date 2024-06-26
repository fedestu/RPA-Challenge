import re
from RPA.Browser.Selenium import Selenium
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import logging
import time
import requests

class NewsScraper:
    def __init__(self, base_url):
        self.browser = Selenium()
        self.base_url = base_url
        self.browser.open_available_browser(self.base_url)
        self.browser.maximize_browser_window()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.image_folder = self.create_daily_image_folder()

    def create_daily_image_folder(self):
        base_image_folder = "images"
        today = datetime.now().strftime("%Y-%m-%d")
        daily_image_folder = os.path.join(base_image_folder, today)
        if not os.path.exists(daily_image_folder):
            os.makedirs(daily_image_folder)
        return daily_image_folder
    
    def open_search_page(self, search_phrase):
        """Open the search page with the given search phrase."""
        try:
            logging.info(f"Opening search page for: {search_phrase}")
            search_url = f"{self.base_url}/search?q={search_phrase}&s=1"
            self.browser.go_to(search_url)

            if self.browser.find_elements("css:.search-results-module-no-results"):
                raise Exception(f"No results found for the search phrase '{search_phrase}'.")

        except Exception as e:
            logging.error(f"Failed to load search page: {e}")
            raise

    def close_browser(self):
        """Close all browser instances."""
        self.browser.close_all_browsers()

    def select_category(self, category_name):
        """Select a specific category from the search filters."""
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:                
                type_section = self.browser.find_element("xpath://p[contains(text(), 'Type')]/following-sibling::ps-toggler//ul")
                categories = self.browser.find_elements("xpath:.//label[contains(@class, 'checkbox-input-label')]", parent=type_section)

                if self.click_category_checkbox(categories, category_name):
                    self.browser.wait_until_element_is_visible("css:.search-results-module-filters-selected[data-showing='true']", timeout=30)
                    logging.info("Filter has been applied and page updated.")
                    time.sleep(2)
                    return

                raise Exception(f"Category '{category_name}' not found.")
            except Exception as e:
                logging.warning(f"Attempt {attempts + 1} failed: {e}")
                self.browser.reload_page()
                attempts += 1

        logging.error(f"Failed to select category '{category_name}' after {max_attempts} attempts.")
        raise Exception("Terminating due to category selection failure")

    def click_category_checkbox(self, categories, category_name):
        """Click the checkbox for the specified category if it is found."""
        for category in categories:
            if category_name in self.browser.get_text(category):
                checkbox = self.browser.find_element("xpath:.//input[@type='checkbox']", parent=category)
                if not self.browser.get_element_attribute(checkbox, 'checked'):
                    self.browser.click_element(checkbox)
                    logging.info(f"Category '{category_name}' clicked.")
                return True
        return False

    def sanitize_title(self, title):
        """Sanitize the title to create a valid filename."""
        sanitized = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        return sanitized[:50]

    def download_image(self, url, file_path):
        """Download an image from the given URL and save it to the specified path."""
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
        else:
            raise Exception(f"Failed to download image from {url}")

    def collect_news_data(self, search_phrase, num_months):
        """Collect news data from the specified number of months ago until now."""
        # Calculate the start month based on the current date minus the number of months specified
        start_month = datetime.now().replace(day=1) - relativedelta(months=max(1, num_months) - 1)
        logging.info(f"Collecting news data from: {start_month.strftime('%Y-%m')} to present")
        results = []
        has_next_page = True
        max_iterations = 100
        current_iteration = 0

        while has_next_page and current_iteration < max_iterations:
            current_iteration += 1
            try:
                # Find all article elements on the page
                articles = self.browser.find_elements("css:ps-promo[data-content-type='article']")
                if not articles:
                    logging.info("No articles found, ending loop.")
                    break
            except Exception as e:
                logging.error(f"Error finding articles: {e}")
                break

            for article in articles:
                try:
                    # Find the timestamp element within the article
                    timestamp_element = self.browser.find_element("css:p.promo-timestamp", parent=article)
                    if not timestamp_element:
                        logging.warning("Timestamp not found for article, skipping...")
                        continue

                    # Get the date of the news article from the timestamp element
                    date_str = self.browser.get_element_attribute(timestamp_element, "data-timestamp")
                    news_date = datetime.fromtimestamp(int(date_str) / 1000)

                    # If the news date is earlier than the start month, return the results collected so far
                    if news_date < start_month:
                        return results

                    # Find and get text from title and description elements
                    title_element = self.browser.find_element("css:h3.promo-title a", parent=article)
                    description_element = self.browser.find_element("css:p.promo-description", parent=article)

                    title = self.browser.get_text(title_element)
                    description = self.browser.get_text(description_element)

                    # Find the image element and get its URL
                    image_element = self.browser.find_element("css:img", parent=article)
                    image_url = self.browser.get_element_attribute(image_element, "src")

                    # Sanitize the title to create a valid filename
                    sanitized_title = self.sanitize_title(title)
                    image_filename = f"{sanitized_title}.jpg"
                    image_path = os.path.join(self.image_folder, image_filename)

                    # Download the image and save it to the specified path
                    self.download_image(image_url, image_path)

                    # Count the occurrences of the search phrase in the title and description
                    search_count = title.count(search_phrase) + description.count(search_phrase)
                    # Check if the title or description contains monetary values
                    contains_money = bool(re.search(r"\$[\d,]+\.?\d*|\d+\s(dollars|USD)", title + description))

                    # Append the collected data to the results list
                    results.append({
                        "title": title,
                        "date": news_date.strftime('%Y-%m-%d'),
                        "description": description,
                        "picture_filename": image_filename,
                        "search_phrase_count": search_count,
                        "contains_money": contains_money
                    })
                except Exception as e:
                    logging.error(f"Error processing article: {e}")
                    continue

            try:
                # Find the next page button and click it if available
                next_button = self.browser.find_element("css:div.search-results-module-next-page a")
                if next_button and 'href' in self.browser.get_element_attribute(next_button, 'outerHTML'):
                    self.browser.click_element(next_button)
                else:
                    has_next_page = False
            except Exception as e:
                logging.error(f"Error navigating to next page: {e}")
                has_next_page = False

        return results
