from typing import Dict, List
import json
from pathlib import Path
import bittensor as bt
from common.data import DataLabel
from scraping.config.model import ScraperConfig, LabelScrapingConfig

class DynamicConfigHandler:
    def __init__(self):
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
                        "max_data_entities": 75
                    }]
                },
                {
                    "scraper_id": "Reddit.custom",
                    "cadence_seconds": 60,
                    "labels_to_scrape": [{
                        "label_choices": weighted_labels["reddit"],
                        "max_data_entities": 100
                    }]
                }
            ]
        }
        
        with open(self.scraping_config_path, 'w') as f:
            json.dump(new_config, f, indent=4)
