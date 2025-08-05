from langchain.tools import BaseTool
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

logger = logging.getLogger(__name__)

class EmailCompositionInput(BaseModel):
    price_changes: str = Field(..., description="JSON string containing price change data")
    product_changes: str = Field(..., description="JSON string containing product addition/removal data")
    email_subject_prefix: str = Field("Price Monitor Alert", description="Prefix for the email subject")
    email_template: Optional[str] = Field(None, description="HTML template for email (if None, default is used)")

class EmailCompositionTool(BaseTool):
    name: str = "email_composition_tool"
    description: str = "Compose email notifications for product and price changes"
    args_schema: Type[BaseModel] = EmailCompositionInput
    
    def _run(
        self, 
        price_changes: str, 
        product_changes: str, 
        email_subject_prefix: str = "Price Monitor Alert",
        email_template: Optional[str] = None
    ) -> str:
        try:
            price_data = json.loads(price_changes)
            product_data = json.loads(product_changes)
            
            # Extract relevant information
            price_changes_list = price_data.get("price_changes", [])
            new_products = product_data.get("new_products", [])
            removed_products = product_data.get("removed_products", [])
            
            # Determine if there's anything to notify about
            has_price_changes = len(price_changes_list) > 0
            has_new_products = len(new_products) > 0
            has_removed_products = len(removed_products) > 0
            
            if not (has_price_changes or has_new_products or has_removed_products):
                return json.dumps({
                    "email_required": False,
                    "reason": "No significant changes detected"
                })
            
            # Compose the subject
            subject_parts = []
            if has_price_changes:
                subject_parts.append(f"{len(price_changes_list)} price changes")
            if has_new_products:
                subject_parts.append(f"{len(new_products)} new products")
            if has_removed_products:
                subject_parts.append(f"{len(removed_products)} removed products")
            
            subject = f"{email_subject_prefix}: {', '.join(subject_parts)}"
            
            # Generate email content
            if email_template:
                # Use provided template
                html_content = email_template
                # Replace placeholders
                html_content = html_content.replace("{{PRICE_CHANGES_COUNT}}", str(len(price_changes_list)))
                html_content = html_content.replace("{{NEW_PRODUCTS_COUNT}}", str(len(new_products)))
                html_content = html_content.replace("{{REMOVED_PRODUCTS_COUNT}}", str(len(removed_products)))
            else:
                # Use default template
                html_content = self._generate_default_template(price_changes_list, new_products, removed_products)
            
            # Generate plain text version
            text_content = self._generate_text_content(price_changes_list, new_products, removed_products)
            
            result = {
                "email_required": True,
                "subject": subject,
                "html_content": html_content,
                "text_content": text_content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Email composition error: {e}")
            return json.dumps({
                "email_required": False,
                "error": f"Email composition failed: {str(e)}"
            })
    
    def _generate_default_template(
        self, 
        price_changes: List[Dict[str, Any]], 
        new_products: List[Dict[str, Any]], 
        removed_products: List[Dict[str, Any]]
    ) -> str:
        """Generate a default HTML email template"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #f8f9fa; padding: 10px; border-bottom: 1px solid #ddd; }
                .section { margin-bottom: 20px; }
                .price-up { color: #dc3545; }
                .price-down { color: #28a745; }
                table { border-collapse: collapse; width: 100%; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Price Monitoring Update</h2>
                    <p>Generated on: """ + datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC") + """</p>
                </div>
        """
        
        # Price changes section
        if price_changes:
            html += """
                <div class="section">
                    <h3>Price Changes</h3>
                    <table>
                        <tr>
                            <th>Product</th>
                            <th>Old Price</th>
                            <th>New Price</th>
                            <th>Change</th>
                        </tr>
            """
            
            for change in price_changes:
                price_class = "price-up" if change.get("change_type") == "increase" else "price-down"
                percent_change = change.get("percent_change", 0)
                change_symbol = "+" if percent_change > 0 else ""
                
                html += f"""
                        <tr>
                            <td>{change.get("product_name", "Unknown")}</td>
                            <td>${change.get("previous_price", 0):.2f}</td>
                            <td>${change.get("current_price", 0):.2f}</td>
                            <td class="{price_class}">{change_symbol}{percent_change}%</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        # New products section
        if new_products:
            html += """
                <div class="section">
                    <h3>New Products</h3>
                    <table>
                        <tr>
                            <th>Product</th>
                            <th>Price</th>
                        </tr>
            """
            
            for product in new_products:
                html += f"""
                        <tr>
                            <td>{product.get("name", "Unknown")}</td>
                            <td>${product.get("price", 0):.2f}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        # Removed products section
        if removed_products:
            html += """
                <div class="section">
                    <h3>Removed Products</h3>
                    <table>
                        <tr>
                            <th>Product</th>
                            <th>Last Price</th>
                        </tr>
            """
            
            for product in removed_products:
                html += f"""
                        <tr>
                            <td>{product.get("name", "Unknown")}</td>
                            <td>${product.get("last_price", 0):.2f}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        html += """
                <div class="footer">
                    <p>This is an automated notification from your Price Monitoring System.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_content(
        self, 
        price_changes: List[Dict[str, Any]], 
        new_products: List[Dict[str, Any]], 
        removed_products: List[Dict[str, Any]]
    ) -> str:
        """Generate plain text email content"""
        text = "PRICE MONITORING UPDATE\n"
        text += f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        # Price changes section
        if price_changes:
            text += f"PRICE CHANGES ({len(price_changes)})\n"
            text += "-" * 50 + "\n"
            
            for change in price_changes:
                product_name = change.get("product_name", "Unknown")
                old_price = change.get("previous_price", 0)
                new_price = change.get("current_price", 0)
                percent_change = change.get("percent_change", 0)
                change_symbol = "+" if percent_change > 0 else ""
                
                text += f"{product_name}\n"
                text += f"  Old price: ${old_price:.2f}\n"
                text += f"  New price: ${new_price:.2f}\n"
                text += f"  Change: {change_symbol}{percent_change}%\n\n"
        
        # New products section
        if new_products:
            text += f"\nNEW PRODUCTS ({len(new_products)})\n"
            text += "-" * 50 + "\n"
            
            for product in new_products:
                text += f"{product.get('name', 'Unknown')}: ${product.get('price', 0):.2f}\n"
        
        # Removed products section
        if removed_products:
            text += f"\nREMOVED PRODUCTS ({len(removed_products)})\n"
            text += "-" * 50 + "\n"
            
            for product in removed_products:
                text += f"{product.get('name', 'Unknown')} (Last price: ${product.get('last_price', 0):.2f})\n"
        
        text += "\nThis is an automated notification from your Price Monitoring System."
        
        return text

class PriorityAssessmentInput(BaseModel):
    price_changes: str = Field(..., description="JSON string containing price change data")
    product_changes: str = Field(..., description="JSON string containing product addition/removal data")
    price_threshold: float = Field(5.0, description="Percentage change threshold for high priority")
    new_product_priority: str = Field("medium", description="Priority level for new products (low, medium, high)")

class PriorityAssessmentTool(BaseTool):
    name: str = "priority_assessment_tool"
    description: str = "Assess notification priority based on the significance of changes"
    args_schema: Type[BaseModel] = PriorityAssessmentInput
    
    def _run(
        self, 
        price_changes: str, 
        product_changes: str,
        price_threshold: float = 5.0,
        new_product_priority: str = "medium"
    ) -> str:
        try:
            price_data = json.loads(price_changes)
            product_data = json.loads(product_changes)
            
            # Extract relevant information
            price_changes_list = price_data.get("price_changes", [])
            new_products = product_data.get("new_products", [])
            removed_products = product_data.get("removed_products", [])
            
            # Initialize priority assessment
            has_high_priority = False
            has_medium_priority = False
            high_priority_reasons = []
            medium_priority_reasons = []
            
            # Assess price changes
            significant_price_changes = []
            for change in price_changes_list:
                percent_change = abs(change.get("percent_change", 0))
                
                if percent_change >= price_threshold:
                    significant_price_changes.append(change)
                    
                    # Very significant price changes (>20% or configured threshold * 2)
                    if percent_change >= max(20.0, price_threshold * 2):
                        has_high_priority = True
                        high_priority_reasons.append(
                            f"Significant price change of {percent_change:.1f}% for {change.get('product_name')}"
                        )
            
            # If there are significant price changes but not high priority
            if significant_price_changes and not has_high_priority:
                has_medium_priority = True
                medium_priority_reasons.append(
                    f"Price changes above threshold for {len(significant_price_changes)} products"
                )
            
            # Assess new products
            if new_products:
                if new_product_priority.lower() == "high":
                    has_high_priority = True
                    high_priority_reasons.append(f"New products added ({len(new_products)})")
                elif new_product_priority.lower() == "medium":
                    has_medium_priority = True
                    medium_priority_reasons.append(f"New products added ({len(new_products)})")
            
            # Assess removed products (usually medium priority)
            if removed_products:
                has_medium_priority = True
                medium_priority_reasons.append(f"Products removed ({len(removed_products)})")
                
                # If many products removed, this might be high priority
                if len(removed_products) >= 5:  # Arbitrary threshold for "many"
                    has_high_priority = True
                    high_priority_reasons.append(f"Significant number of products removed ({len(removed_products)})")
            
            # Determine overall priority
            if has_high_priority:
                priority = "high"
                reasons = high_priority_reasons
            elif has_medium_priority:
                priority = "medium"
                reasons = medium_priority_reasons
            else:
                priority = "low"
                reasons = ["Minor changes only"]
            
            result = {
                "priority": priority,
                "reasons": reasons,
                "has_significant_changes": has_high_priority or has_medium_priority,
                "significant_price_changes_count": len(significant_price_changes),
                "new_products_count": len(new_products),
                "removed_products_count": len(removed_products),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Priority assessment error: {e}")
            return json.dumps({
                "priority": "medium",  # Default to medium on error
                "error": f"Priority assessment failed: {str(e)}"
            })

# Instantiate the tools
email_composition_tool = EmailCompositionTool()
priority_assessment_tool = PriorityAssessmentTool()