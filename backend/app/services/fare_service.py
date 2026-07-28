import os
import csv
import logging
from pydantic import BaseModel
from typing import Dict

logger = logging.getLogger(__name__)

class FareAttributes(BaseModel):
    fare_id: str
    price: float
    currency_type: str

class FareService:
    def __init__(self):
        self.dataset_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "DataSet", "real_data"
        )
        self.fare_attributes: Dict[str, FareAttributes] = {}
        self._load_fares()

    def _load_fares(self):
        attr_path = os.path.join(self.dataset_dir, "fare_attributes.txt")
        if not os.path.exists(attr_path):
            logger.warning(f"Fare attributes file not found at {attr_path}")
            return
            
        try:
            with open(attr_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.fare_attributes[row["fare_id"]] = FareAttributes(
                        fare_id=row["fare_id"],
                        price=float(row["price"]),
                        currency_type=row["currency_type"]
                    )
            logger.info(f"Loaded {len(self.fare_attributes)} fare attributes.")
        except Exception as e:
            logger.error(f"Failed to load fare attributes: {e}")

    def calculate_fare(self, route_id: str, distance_km: float) -> float:
        target_price = 10.0
        if distance_km > 15:
            target_price = 30.0
        elif distance_km > 10:
            target_price = 25.0
        elif distance_km > 5:
            target_price = 20.0
        elif distance_km > 2:
            target_price = 15.0

        if not self.fare_attributes:
            return float(target_price)
            
        closest_fare = None
        min_diff = float('inf')
        for fare_id, attr in self.fare_attributes.items():
            diff = abs(attr.price - target_price)
            if diff < min_diff:
                min_diff = diff
                closest_fare = attr
                
        if closest_fare:
            return closest_fare.price
            
        return float(target_price)

fare_service = FareService()
