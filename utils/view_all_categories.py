import os
import json
import glob
from datetime import datetime

def load_latest_analyses():
    """Load the latest analysis file for each category"""
    categories = {}
    
    # Find all analysis files
    analysis_files = glob.glob('data/lego_*_analysis_*.json')
    
    for file_path in analysis_files:
        # Extract category name from filename
        filename = os.path.basename(file_path)
        parts = filename.split('_')
        
        # Skip if filename doesn't match expected pattern
        if len(parts) < 4:
            continue
            
        # Extract category (could be multiple words)
        category_parts = []
        for part in parts[1:-2]:  # Skip 'lego_' prefix and '_analysis_timestamp.json' suffix
            if not part.startswith('20'):  # Not part of the timestamp
                category_parts.append(part)
        
        category = ' '.join(category_parts).capitalize()
        
        # Extract timestamp from filename
        timestamp_str = parts[-1].replace('.json', '')
        try:
            timestamp = datetime.strptime(f"{parts[-2]}_{timestamp_str}", "%Y%m%d_%H%M%S")
        except ValueError:
            # If timestamp parsing fails, use file modification time
            timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # If this category hasn't been seen yet or this file is newer
        if category not in categories or timestamp > categories[category]['timestamp']:
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    categories[category] = {
                        'data': data,
                        'timestamp': timestamp,
                        'file_path': file_path
                    }
                except json.JSONDecodeError:
                    print(f"Error parsing {file_path}")
    
    return categories

def generate_summary_report():
    """Generate a summary report of all categories"""
    categories = load_latest_analyses()
    
    if not categories:
        print("No analysis data found. Please run the monitoring process first.")
        return
    
    print("\n========== LEGO PRICE MONITORING SUMMARY ==========")
    print(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Categories monitored: {len(categories)}")
    print("=" * 50)
    
    total_price_changes = 0
    total_new_products = 0
    total_removed_products = 0
    
    for category, info in sorted(categories.items()):
        data = info['data']
        timestamp = info['timestamp']
        
        price_changes = data.get('price_changes', [])
        new_products = data.get('new_products', [])
        removed_products = data.get('removed_products', [])
        
        print(f"\n>> CATEGORY: {category}")
        print(f"   Last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Price changes: {len(price_changes)}")
        print(f"   New products: {len(new_products)}")
        print(f"   Removed products: {len(removed_products)}")
        
        total_price_changes += len(price_changes)
        total_new_products += len(new_products)
        total_removed_products += len(removed_products)
        
        # Show some details of the most significant changes
        if price_changes:
            # Sort by absolute percentage change
            sorted_changes = sorted(price_changes, key=lambda x: abs(x.get('percent_change', 0)), reverse=True)
            top_changes = sorted_changes[:3]  # Show top 3
            
            print("\n   Top price changes:")
            for change in top_changes:
                product_name = change.get('product_name', 'Unknown')
                old_price = change.get('previous_price', 0)
                new_price = change.get('current_price', 0)
                percent = change.get('percent_change', 0)
                direction = "↑" if percent > 0 else "↓"
                
                print(f"   - {product_name}: {old_price:.2f} → {new_price:.2f} ({direction}{abs(percent):.1f}%)")
        
        if new_products:
            print("\n   New products:")
            for product in new_products[:3]:  # Show top 3
                name = product.get('name', 'Unknown')
                price = product.get('price', 0)
                print(f"   - {name}: {price:.2f}")
    
    print("\n" + "=" * 50)
    print("OVERALL SUMMARY:")
    print(f"Total price changes: {total_price_changes}")
    print(f"Total new products: {total_new_products}")
    print(f"Total removed products: {total_removed_products}")
    print("=" * 50)

if __name__ == "__main__":
    generate_summary_report()