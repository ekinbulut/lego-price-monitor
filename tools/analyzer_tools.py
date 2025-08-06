from crewai.tools.base_tool import BaseTool
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PriceComparisonTool(BaseTool):
    name: str = "price_comparison_tool"
    description: str = "Compare current product prices with historical data to detect changes"
    
    def _run(self, current_data: str, historical_data: str, price_threshold: float = 0.0) -> str:
        try:
            current_products = json.loads(current_data)
            historical_products = json.loads(historical_data)
            
            # Create lookup dictionaries for faster comparison
            current_dict = {p.get("id"): p for p in current_products if p.get("id")}
            historical_dict = {p.get("id"): p for p in historical_products if p.get("id")}
            
            price_changes = []
            
            # Check each current product for price changes
            for product_id, current_product in current_dict.items():
                if product_id in historical_dict:
                    historical_product = historical_dict[product_id]
                    
                    current_price = self._get_price(current_product)
                    historical_price = self._get_price(historical_product)
                    
                    if current_price is not None and historical_price is not None:
                        # Calculate price change
                        absolute_change = current_price - historical_price
                        if historical_price > 0:
                            percent_change = (absolute_change / historical_price) * 100
                        else:
                            percent_change = 0 if absolute_change == 0 else float('inf')
                        
                        # Check if change exceeds threshold
                        if abs(percent_change) >= price_threshold:
                            price_changes.append({
                                "product_id": product_id,
                                "product_name": current_product.get("name", "Unknown"),
                                "current_price": current_price,
                                "previous_price": historical_price,
                                "absolute_change": absolute_change,
                                "percent_change": round(percent_change, 2),
                                "change_type": "increase" if absolute_change > 0 else "decrease"
                            })
            
            # Sort by percentage change (absolute value, descending)
            price_changes.sort(key=lambda x: abs(x.get("percent_change", 0)), reverse=True)
            
            result = {
                "price_changes": price_changes,
                "total_changes": len(price_changes),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Price comparison error: {e}")
            return json.dumps({"error": f"Price comparison failed: {str(e)}"})
    
    def _get_price(self, product: Dict[str, Any]) -> Optional[float]:
        """Extract price from product data safely"""
        price = product.get("price")
        if price is None:
            return None
        
        try:
            return float(price)
        except (ValueError, TypeError):
            return None

class ChangeDetectionTool(BaseTool):
    name: str = "change_detection_tool"
    description: str = "Detect new products, removed products, and other changes"
    
    def _run(self, current_data: str, historical_data: str) -> str:
        try:
            current_products = json.loads(current_data)
            historical_products = json.loads(historical_data)
            
            # Create sets of product IDs for quick comparison
            current_ids = {p.get("id") for p in current_products if p.get("id")}
            historical_ids = {p.get("id") for p in historical_products if p.get("id")}
            
            # Find new and removed products
            new_ids = current_ids - historical_ids
            removed_ids = historical_ids - current_ids
            
            # Create lookups for detailed information
            current_dict = {p.get("id"): p for p in current_products if p.get("id")}
            historical_dict = {p.get("id"): p for p in historical_products if p.get("id")}
            
            # Get detailed information about new products
            new_products = [
                {
                    "id": product_id,
                    "name": current_dict[product_id].get("name", "Unknown"),
                    "price": current_dict[product_id].get("price", 0),
                    "detected_at": datetime.utcnow().isoformat()
                }
                for product_id in new_ids
            ]
            
            # Get detailed information about removed products
            removed_products = [
                {
                    "id": product_id,
                    "name": historical_dict[product_id].get("name", "Unknown"),
                    "last_price": historical_dict[product_id].get("price", 0),
                    "removed_at": datetime.utcnow().isoformat(),
                    "last_seen": historical_dict[product_id].get("timestamp", "Unknown")
                }
                for product_id in removed_ids
            ]
            
            # Detect other changes (excluding price changes)
            other_changes = []
            for product_id in current_ids.intersection(historical_ids):
                current = current_dict[product_id]
                historical = historical_dict[product_id]
                
                changes = {}
                for key in set(current.keys()).union(historical.keys()):
                    # Skip price as it's handled separately
                    if key in ("price", "id", "timestamp"):
                        continue
                    
                    current_value = current.get(key)
                    historical_value = historical.get(key)
                    
                    if current_value != historical_value:
                        changes[key] = {
                            "from": historical_value,
                            "to": current_value
                        }
                
                if changes:
                    other_changes.append({
                        "id": product_id,
                        "name": current.get("name", "Unknown"),
                        "changes": changes
                    })
            
            result = {
                "new_products": new_products,
                "removed_products": removed_products,
                "other_changes": other_changes,
                "summary": {
                    "total_current_products": len(current_products),
                    "total_historical_products": len(historical_products),
                    "new_products_count": len(new_products),
                    "removed_products_count": len(removed_products),
                    "other_changes_count": len(other_changes)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Change detection error: {e}")
            return json.dumps({"error": f"Change detection failed: {str(e)}"})