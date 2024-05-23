from news_scraper import NewsScraper
from news_reporter import NewsReporter
import logging
from RPA.Robocorp.WorkItems import WorkItems

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    scraper = NewsScraper("https://www.latimes.com")
    reporter = NewsReporter("output")

    try:
        # Initialize Robocorp WorkItems to handle input data
        work_items = WorkItems()
        work_items.get_input_work_item()

        # Extract necessary information from the work item
        search_phrase = work_items.get_work_item_variable("search_phrase")
        category_name = work_items.get_work_item_variable("category_name")
        num_months = work_items.get_work_item_variable("num_months")

        # Open the search page
        scraper.open_search_page(search_phrase) 

        # Select category if necessary
        scraper.select_category(category_name)

        # Collect data
        news_data = scraper.collect_news_data(search_phrase, num_months)  

        # Create the report in Excel
        reporter.create_excel_report(news_data)

    except Exception as e:
        logging.error(f"Process terminated: {str(e)}")
        
    finally:
        scraper.close_browser()

if __name__ == "__main__":
    main()
