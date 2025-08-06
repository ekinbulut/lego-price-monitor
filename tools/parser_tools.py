from crewai.tools.base_tool import BaseTool
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
import json
import re
from datetime import datetime

class DataNormalizationTool(BaseTool):
    name: str = "data_normalization_tool"
    description: str = "Clean and normalize raw product data to ensure consistency"
    
    def _run(self, raw_data: str, expected_fields: List[str] = None) -> str:
        if expected_fields is None:
            expected_fields = ["name", "price", "id", "image_url", "description"]
        try:
            # Parse JSON data
            products = json.loads(raw_data)
            normalized_products = []
            
            for product in products:
                normalized_product = {}
                
                # Ensure all expected fields exist
                for field in expected_fields:
                    normalized_product[field] = product.get(field, None)
                
                # Clean and normalize product name
                if normalized_product.get("name"):
                    normalized_product["name"] = self._clean_text(normalized_product["name"])
                
                # Ensure price is a float
                if normalized_product.get("price"):
                    if isinstance(normalized_product["price"], str):
                        normalized_product["price"] = self._extract_price(normalized_product["price"])
                
                # Generate a unique ID if missing
                if not normalized_product.get("id"):
                    normalized_product["id"] = self._generate_id(normalized_product)
                
                # Add timestamp for when this data was collected
                normalized_product["timestamp"] = datetime.utcnow().isoformat()
                
                normalized_products.append(normalized_product)
            
            return json.dumps(normalized_products, indent=2)
        
        except Exception as e:
            return json.dumps({"error": f"Normalization failed: {str(e)}"})
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text data"""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\-.,]', '', text)
        return text
    
    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from string"""
        if isinstance(price_str, (int, float)):
            return float(price_str)
        
        # Extract digits and decimal point
        price_match = re.search(r'(\d+(?:\.\d+)?)', price_str.replace(',', '.'))
        if price_match:
            return float(price_match.group(1))
        return 0.0
    
    def _generate_id(self, product: Dict[str, Any]) -> str:
        """Generate a unique ID based on product attributes"""
        import hashlib
        # Create a string from name and other available attributes
        id_base = product.get("name", "") + str(product.get("price", ""))
        # Create a hash for the ID
        return hashlib.md5(id_base.encode()).hexdigest()

class SchemaDetectionTool(BaseTool):
    name: str = "schema_detection_tool"
    description: str = "Detect and map product data to a consistent schema"
    
    def _run(self, raw_data: str, target_schema: Optional[str] = None) -> str:
        try:
            # Parse input data
            products = json.loads(raw_data)
            
            # If target schema is provided, use it
            if target_schema:
                schema = json.loads(target_schema)
            else:
                # Auto-detect schema from data
                schema = self._detect_schema(products)
            
            # Map data to the schema
            mapped_products = []
            for product in products:
                mapped_product = self._map_to_schema(product, schema)
                if mapped_product:  # Only add if mapping was successful
                    mapped_products.append(mapped_product)
            
            result = {
                "detected_schema": schema,
                "mapped_products": mapped_products,
                "products_count": len(mapped_products)
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Schema detection failed: {str(e)}"})
    
    def _detect_schema(self, products: List[Dict[str, Any]]) -> Dict[str, str]:
        """Automatically detect schema from the data"""
        if not products:
            return {}
        
        # Start with first product's fields
        schema = {}
        for key, value in products[0].items():
            schema[key] = type(value).__name__
        
        # Update with fields from other products
        for product in products[1:]:
            for key, value in product.items():
                if key not in schema:
                    schema[key] = type(value).__name__
        
        return schema
    
    def _map_to_schema(self, product: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
        """Map a product to the target schema"""
        mapped_product = {}
        
        for field, type_name in schema.items():
            # Get value from product or set to None if not present
            value = product.get(field)
            
            if value is not None:
                # Convert to the expected type if possible
                try:
                    if type_name == "str":
                        mapped_product[field] = str(value)
                    elif type_name == "int":
                        mapped_product[field] = int(float(value)) if value else 0
                    elif type_name == "float":
                        mapped_product[field] = float(value) if value else 0.0
                    elif type_name == "bool":
                        mapped_product[field] = bool(value)
                    elif type_name == "list":
                        mapped_product[field] = list(value) if isinstance(value, (list, tuple)) else [value]
                    elif type_name == "dict":
                        mapped_product[field] = dict(value) if isinstance(value, dict) else {}
                    else:
                        mapped_product[field] = value
                except (ValueError, TypeError):
                    mapped_product[field] = None
            else:
                mapped_product[field] = None
        
        return mapped_product