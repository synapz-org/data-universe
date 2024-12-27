from typing import Dict, List, Tuple
import json
from pathlib import Path
import bittensor as bt
import asyncio
from common.data import DataLabel
from scraping.config.model import ScraperConfig, LabelScrapingConfig
from utils.backoff import ExponentialBackoff

class DynamicConfigHandler:
    def __init__(self):
        self.x_scraper = ApiDojoTwitterScraper()
        self.total_json_path = Path("dynamic_desirability/total.json")
        self.scraping_config_path = Path("scraping/config/scraping_config.json")
        
    def get_weighted_labels(self) -> Dict[str, List[str]]:
        """Gets high-value labels from total.json"""
        with open(self.total_json_path) as f:
            total = json.load(f)
            
        labels = {
            "reddit": [],
            "x": []
        }
        
        for source in total:
            if source["source_name"] == "reddit":
                labels["reddit"] = [label for label, weight in source["label_weights"].items() 
                                  if weight >= 0.7]
            elif source["source_name"] == "x":
                labels["x"] = [label for label, weight in source["label_weights"].items() 
                             if weight >= 0.7]
                
        return labels

    def get_trending_subreddits(self) -> List[str]:
        """Fetches trending subreddits and formats them as r/subreddit"""
        trending = []
        for submission in self.reddit.subreddit('popular').hot(limit=25):
            subreddit = f"r/{submission.subreddit.display_name}"
            trending.append(subreddit)
        return trending
        
    def update_scraping_config(self):
        """Updates scraping configuration with weighted labels"""
        weighted_labels = self.get_weighted_labels()
        
        new_config = {
            "scraper_configs": [
                {
                    "scraper_id": "X.apidojo",
                    "cadence_seconds": 300,
                    "labels_to_scrape": [{
                        "label_choices": weighted_labels["x"],
                        "max_data_entities": 25,  # Optimized batch size
                        "min_weight": 0.7  # Only fetch high-value content
                    }]
                }
            ]
        }
        
        with open(self.scraping_config_path, 'w') as f:
            json.dump(new_config, f, indent=4)

    def get_trending_hashtags(self) -> List[str]:
        """Fetches trending X hashtags using the ApiDojo actor"""
        try:
            with bt.dendrite(wallet=self.wallet) as dendrite:
                run_input = {
                    "maxItems": self.max_labels_per_source,
                    "searchMode": "trending"
                }
                run_config = RunConfig(
                    actor_id=ApiDojoTwitterScraper.ACTOR_ID,
                    debug_info="Fetch trending hashtags"
                )
                trending = []
                dataset = await self.runner.run(run_config, run_input)
                for item in dataset:
                    if 'hashtags' in item:
                        trending.extend([f"#{tag}" for tag in item['hashtags']])
                return trending[:self.max_labels_per_source]
        except Exception as e:
            bt.logging.error(f"Error fetching trending hashtags: {str(e)}")
            return []

    def balance_labels(self, high_value_labels: Dict[str, float], 
                      trending_reddit: List[str], 
                      trending_x: List[str]) -> Tuple[List[str], List[str]]:
        """Balances high-value and trending labels for optimal scoring"""
        reddit_labels = []
        x_labels = []
        
        # First add all high-value labels
        for label, weight in high_value_labels.items():
            if label.startswith('r/'):
                reddit_labels.append(label)
            elif label.startswith('#'):
                x_labels.append(label)
                
        # Fill remaining slots with trending content
        remaining_reddit = self.max_labels_per_source - len(reddit_labels)
        remaining_x = self.max_labels_per_source - len(x_labels)
        
        reddit_labels.extend([label for label in trending_reddit 
                            if label not in reddit_labels][:remaining_reddit])
        x_labels.extend([label for label in trending_x 
                        if label not in x_labels][:remaining_x])
                        
        return reddit_labels, x_labels

    async def run(self):
        backoff = ExponentialBackoff(initial=60, maximum=3600)
        while True:
            try:
                await self.update_config_with_retry()
            except Exception as e:
                delay = next(backoff)
                bt.logging.error(f"Error, retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)

    def validate_config(self, config: dict) -> bool:
        required_fields = ["scraper_configs"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        return True
