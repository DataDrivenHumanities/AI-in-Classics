import numpy as np
import os
import re
import requests
import time
from pprint import pprint
from termcolor import colored, cprint
from tqdm import tqdm

# Import our utilities
sys_path = os.path.dirname(os.path.abspath(__file__))
if os.path.join(sys_path, 'src', 'utils') not in sys.path:
    import sys
    sys.path.append(sys_path)

try:
    from src.utils.logging_utils import setup_logger
    from src.utils.cache_utils import cache
    # Set up logging
    logger = setup_logger('cleanupXML')
except ImportError:
    # Fallback if modules aren't available
    import logging
    logger = logging.getLogger('cleanupXML')
    logging.basicConfig(level=logging.INFO)
    
    # Create a dummy cache if import fails
    class DummyCache:
        def has(self, key): return False
        def get(self, key, default=None): return default
        def set(self, key, value): pass
    cache = DummyCache()

def cleanup_XML(urn: str, save_raw_path: str = None, save_clean_path: str = None, use_cache: bool = True):
    """
    Parses XML and optionally saves it to a specified directory. Note that this works for First1KGreek Project only.

    Parameters:
        urn (str): URN of work for XML parsing.
        save_raw_path (str): Path to directory to save raw XML file. If None, no saving is done. Defaults to None.
        save_clean_path (str): Path to directory to save cleaned XML file. If None, no saving is done. Defaults to None.
        use_cache (bool): Whether to use caching for downloaded XML. Defaults to True.

    Return:
        str - Cleaned XML as a string.
    """
    logger.info(f"Starting XML cleanup for URN: {urn}")
    url_base = 'https://github.com/OpenGreekAndLatin/First1KGreek/blob/cdacf1f80ca7abef67f1cb9a0772556afa87c2b1/data/'
    urn_parts = np.asarray(a=re.split(string=urn, pattern=':|\.'))
    url = url_base + '/'.join(urn_parts[-3:-1]) + f'/{urn.split(":")[-1]}.xml'
    
    # Check if XML is in cache
    xml_text = None
    if use_cache and cache.has(url):
        logger.info(f"Using cached XML for {urn}")
        xml_text = cache.get(url)
    
    # If not in cache, download it
    if xml_text is None:
        logger.info(f"Downloading XML from {url}")
        try:
            response = requests.get(url=url)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses
            xml_text = response.text
            
            # Store in cache for future use
            if use_cache:
                cache.set(url, xml_text)
                logger.debug(f"XML for {urn} stored in cache")
        except requests.RequestException as e:
            logger.error(f"Error downloading XML: {str(e)}")
            raise
    # Save raw xml into a file path
    if save_raw_path and os.path.exists(path=save_raw_path):
        try:
            filename = f'{"".join(urn_parts[-3:])}.xml'
            filepath = os.path.join(save_raw_path, filename)
            logger.info(f"Saving raw XML to {filepath}")
            with open(file=filepath, mode='w') as file:
                file.write(xml_text)
        except Exception as e:
            logger.error(f"Error saving raw XML: {str(e)}")
    logger.info("Starting XML cleaning process")
    print("Cleaning XML data...")
    
    # Show progress indicator
    progress = tqdm(total=3, desc="Extracting elements", unit="element")
    
    # Declaring variables
    author = ""
    title = ""
    text = ""
    
    # Find title, author, and text in the XML file and add to variables
    if (xml_text.find("<author") != -1):
        start = xml_text.find("<author")
        end = xml_text.find("</author>") + 9 #to grab until after </author>. < only in case lang or something in title
        author = xml_text[start:end]
        logger.debug(f"Found author element: {author[:20]}...")
        progress.update(1)
    else:
        logger.warning("No author element found in XML")
        progress.update(1)
        
    if (xml_text.find("<title") != -1):
        start = xml_text.find("<title")
        end = xml_text.find("</title>") + 9 
        title = xml_text[start:end]
        logger.debug(f"Found title element: {title[:20]}...")
        progress.update(1)
    else:
        logger.warning("No title element found in XML")
        progress.update(1)
        
    if (xml_text.find("<text") != -1):
        start = xml_text.find("<text")
        end = xml_text.find("</text>") + 7 
        text = xml_text[start:end]
        logger.debug(f"Found text element: {len(text)} characters")
        progress.update(1)
    else:
        logger.warning("No text element found in XML")
        progress.update(1)
        
    progress.close()  
    # Create the new file content
    logger.info("Constructing cleaned XML content")
    xml_new_text = "<?xml version=\"1.0\" encoding=\"UTF-8\"?> \n "
    
    # Add TEI formatting
    xml_new_text += "<TEI xmlns=\"http://www.tei-c.org/ns/1.0\">\n"
    xml_new_text += "\t" + title + "\n \t" + author + "\n \t"  + text
    xml_new_text += "\n</TEI>"
    
    # Log content summary
    logger.info(f"Created new XML content with {len(xml_new_text)} characters")
    # Save new data into a new file path
    if save_clean_path and os.path.exists(path=save_clean_path):
        try:
            filename = f'{"".join(urn_parts[-3:])}_clean.xml'
            filepath = os.path.join(save_clean_path, filename)
            logger.info(f"Saving cleaned XML to {filepath}")
            
            with open(file=filepath, mode='w') as file:
                file.write(xml_new_text)
                
            logger.info(f"Successfully saved cleaned XML to {filepath}")
        except Exception as e:
            logger.error(f"Error saving cleaned XML: {str(e)}")
    
    logger.info("XML cleanup complete")
    return xml_new_text



if __name__ == '__main__':
    import time
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Clean up XML from First1KGreek Project')
    parser.add_argument('--urn', default='urn:cts:greekLit:ggm0001.ggm001.1st1K-grc1',
                        help='URN of the document to process')
    parser.add_argument('--raw-path', default='.', help='Directory to save raw XML')
    parser.add_argument('--clean-path', default='.', help='Directory to save cleaned XML')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    args = parser.parse_args()
    
    print(f"Processing URN: {args.urn}")
    start_time = time.time()
    
    try:
        xml_text = cleanup_XML(urn=args.urn, 
                           save_raw_path=args.raw_path, 
                           save_clean_path=args.clean_path,
                           use_cache=not args.no_cache)
        
        print("\nFirst 200 characters of cleaned XML:")
        print(xml_text[:200] + '...')
        print(f"\nTotal characters: {len(xml_text)}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"ERROR: {str(e)}")
    
    elapsed_time = time.time() - start_time
    print(f"\nProcess completed in {elapsed_time:.2f} seconds")
