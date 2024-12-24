import bittensor as bt
from typing import List, Dict, Any
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
from common.data import DataEntity, DataLabel, DataSource
from apify_client import ApifyClient

class ApiDojoTwitterScraper:
    ACTOR_ID = "X.apidojo"
    
    def __init__(self):
        load_dotenv()
        self.client = ApifyClient(os.getenv('APIFY_API_TOKEN'))
            
    def scrape(self, labels: List[str]) -> List[DataEntity]:
        """Scrapes X posts for given hashtags"""
        results = []
        
        for label in labels:
            try:
                run_input = {
                    "searchTerms": [label],
                    "includeSearchTerms": True,
                    "maxItems": 5,  # Minimal test
                    "sort": "Latest",
                    "tweetLanguage": "en"
                }
                
                run = self.client.actor("apidojo/tweet-scraper").call(run_input=run_input)
                
                for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                    content = item['text'].encode('utf-8')
                    entity = DataEntity(
                        uri=f"twitter.com/status/{item['id']}",
                        content=content,
                        datetime=datetime.now(pytz.UTC),
                        source=DataSource.X,
                        content_size_bytes=len(content),
                        label=DataLabel(value=label)
                    )
                    results.append(entity)
                    
            except Exception as e:
                bt.logging.error(f"Error scraping {label}: {str(e)}")
                continue
                
        return results
