import time
from scraper.communicator import Communicator
from scraper.common import Common
from bs4 import BeautifulSoup
from selenium.common.exceptions import JavascriptException
from scraper.parser import Parser

class Scroller:

    def __init__(self, driver) -> None:
        self.driver = driver
    
    def __init_parser(self):
        self.parser = Parser(self.driver)


    def start_parsing(self):
        self.__init_parser() # init parser object on fly

        self.parser.main(self.__allResultsLinks)
        

    
    def scroll(self):
        """In case search results are not available"""

        # Wait longer for the page to load and try multiple times
        scrollAbleElement = None
        max_attempts = 10
        attempt = 0
        
        while scrollAbleElement is None and attempt < max_attempts:
            attempt += 1
            Communicator.show_message(f"Looking for search results... (attempt {attempt}/{max_attempts})")
            
            scrollAbleElement = self.driver.execute_script(
                """return document.querySelector("[role='feed']")"""
            )
            
            if scrollAbleElement is None:
                # Try alternative selectors
                alternative_selectors = [
                    "[data-value='Search results']",
                    ".m6QErb",
                    ".Nv2PK"
                ]
                
                for selector in alternative_selectors:
                    scrollAbleElement = self.driver.execute_script(
                        f"return document.querySelector('{selector}')"
                    )
                    if scrollAbleElement:
                        Communicator.show_message(f"Found results using alternative selector: {selector}")
                        break
                
                if scrollAbleElement is None:
                    time.sleep(2)  # Wait 2 seconds before next attempt
        
        if scrollAbleElement is None:
            # Additional debugging information
            page_title = self.driver.title
            current_url = self.driver.current_url
            Communicator.show_message(f"Debug info - Page title: {page_title}")
            Communicator.show_message(f"Debug info - Current URL: {current_url}")
            
            # Check if page contains any results-related text
            page_source = self.driver.page_source.lower()
            if "no results" in page_source or "no places" in page_source:
                Communicator.show_message("Google Maps returned no results for this search query.")
            else:
                Communicator.show_message("Could not find search results container. Google Maps may have changed its structure.")
            
            Communicator.show_message(message="We are sorry but, No results found for your search query on googel maps....")

        else:
            Communicator.show_message(message="Starting scrolling")

            last_height = 0

            while True:
                if Common.close_thread_is_set():
                    self.driver.quit()
                    return

                """again finding element to avoid StaleElementReferenceException"""
                scrollAbleElement = self.driver.execute_script(
                """return document.querySelector("[role='feed']")"""
            )
                self.driver.execute_script(
                    "arguments[0].scrollTo(0, arguments[0].scrollHeight);",
                    scrollAbleElement,
                )
                time.sleep(2)


                # get new scroll height and compare with last scroll height.
                new_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight", scrollAbleElement
                )
                if new_height == last_height:
                    """checking if we have reached end of the list"""

                    script = f"""
                    const endingElement = document.querySelector(".PbZDve ");
                    return endingElement;
                    """

                    endAlertElement = self.driver.execute_script(
                        script)  # to know that we are at end of list or not

                    if endAlertElement is None:
                        """if it returns empty list its mean we are not at the end of list"""
                        try:  # sometimes google maps load results when a result is clicked
                            self.driver.execute_script(
                                "array=document.getElementsByClassName('hfpxzc');array[array.length-1].click();"
                            )
                        except JavascriptException:
                            pass
                    else:

                        break
                else:
                    last_height = new_height
                    allResultsListSoup = BeautifulSoup(
                    scrollAbleElement.get_attribute('outerHTML'), 'html.parser')

                    allResultsAnchorTags = allResultsListSoup.find_all(
                        'a', class_='hfpxzc')

                    """all the links of results"""
                    self.__allResultsLinks = [anchorTag.get(
                        'href') for anchorTag in allResultsAnchorTags]
                    
                    Communicator.show_message(f"Total locations scrolled: {len(self.__allResultsLinks)}")

            self.start_parsing()


                    