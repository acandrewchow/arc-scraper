#!/usr/bin/env python3
"""
Arc'teryx Stock Monitor - Background Scheduler
Runs periodically to check stock for all verified subscriptions and send notifications
Can be run as a standalone script or as a background service
"""

import json
import os
import sys
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

# Add app directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper import check_stock_status

load_dotenv()

# Use absolute path for subscriptions and state files
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SUBSCRIPTIONS_FILE = os.path.join(APP_DIR, "subscriptions.json")
STATE_DIR = os.path.join(APP_DIR, "state")


def get_state_file_path(product_url: str) -> str:
    """Generate a state file path based on the product URL."""
    url_hash = hashlib.md5(product_url.encode()).hexdigest()[:8]
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, f"state_{url_hash}.json")


def load_subscriptions() -> Dict:
    """Load subscriptions from JSON file."""
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_subscriptions(subscriptions: Dict):
    """Save subscriptions to JSON file."""
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=2)


def load_state(state_file: str) -> Dict:
    """Load the last known state for a product."""
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {'color_stock': {}, 'color_size_stock': {}, 'last_checked': None, 'has_sizes': None}


def save_state(state_file: str, color_stock: Optional[Dict[str, bool]] = None,
               color_size_stock: Optional[Dict[str, Dict[str, bool]]] = None,
               has_sizes: Optional[bool] = None,
               product_name: Optional[str] = None):
    """Save the current state."""
    state = {
        'last_checked': datetime.now().isoformat()
    }
    
    if product_name is not None:
        state['product_name'] = product_name
    
    if has_sizes is not None:
        state['has_sizes'] = has_sizes
    
    if color_stock is not None:
        state['color_stock'] = color_stock
    
    if color_size_stock is not None:
        state['color_size_stock'] = color_size_stock
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def send_stock_notification(email: str, product_name: str, product_url: str,
                           back_in_stock: List, out_of_stock: List):
    """Send stock notification email."""
    try:
        sender = os.getenv('SENDER_EMAIL')
        password = os.getenv('SENDER_PASSWORD')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        if not all([sender, password]):
            print(f"Error: Email credentials not configured", file=sys.stderr)
            return False
        
        body = f"Arc'teryx {product_name} - Stock Status Update\n\n"
        
        if back_in_stock:
            body += "🎉 BACK IN STOCK:\n"
            for item in back_in_stock:
                if isinstance(item, tuple) and len(item) == 2:
                    color, size = item
                    if size:
                        body += f"  ✅ {color} - Size {size}\n"
                    else:
                        body += f"  ✅ {color}\n"
            body += "\n"
        
        if out_of_stock:
            body += "❌ NOW OUT OF STOCK:\n"
            for item in out_of_stock:
                if isinstance(item, tuple) and len(item) == 2:
                    color, size = item
                    if size:
                        body += f"  ❌ {color} - Size {size}\n"
                    else:
                        body += f"  ❌ {color}\n"
        
        body += f"\nProduct URL: {product_url}\n"
        body += f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if back_in_stock:
            body += "\nHurry and get yours before it sells out again!\n"
        
        msg = MIMEText(body, 'plain')
        msg['From'] = sender
        msg['To'] = email
        msg['Subject'] = f"🎉 Arc'teryx {product_name} Stock Alert!"
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Notification sent to {email} for {product_name}")
        return True
    except Exception as e:
        print(f"❌ Error sending notification to {email}: {e}", file=sys.stderr)
        return False


def check_all_subscriptions():
    """Check stock for all verified subscriptions and send notifications."""
    subscriptions = load_subscriptions()
    
    # Filter to only verified, active subscriptions
    active_subs = {
        key: sub for key, sub in subscriptions.items()
        if sub.get('verified', False) and sub.get('active', True)
    }
    
    if not active_subs:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No active subscriptions to check")
        return
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking {len(active_subs)} active subscription(s)...")
    
    # Group subscriptions by product URL to avoid duplicate checks
    products = {}
    for sub_key, sub in active_subs.items():
        product_url = sub['product_url']
        if product_url not in products:
            products[product_url] = []
        products[product_url].append(sub)
    
    print(f"Found {len(products)} unique product(s) to check")
    
    # Check each product
    for product_url, subs in products.items():
        print(f"\n📦 Checking: {product_url}")
        print(f"   Subscribers: {len(subs)}")
        
        try:
            # Check current stock
            stock_data, has_sizes, product_name = check_stock_status(product_url, headless=True)
            
            if stock_data is None:
                print(f"   ⚠️  Could not check stock status")
                continue
            
            product_name = product_name or subs[0].get('product_name', 'Product')
            state_file = get_state_file_path(product_url)
            previous_state = load_state(state_file)
            
            # Determine stock changes
            back_in_stock = []
            out_of_stock = []
            
            if has_sizes:
                previous = previous_state.get('color_size_stock', {})
                for color, sizes_stock in stock_data.items():
                    prev_sizes = previous.get(color, {})
                    for size, is_in_stock in sizes_stock.items():
                        was_in_stock = prev_sizes.get(size)
                        if was_in_stock is not None:
                            if not was_in_stock and is_in_stock:
                                back_in_stock.append((color, size))
                            elif was_in_stock and not is_in_stock:
                                out_of_stock.append((color, size))
                
                # Save new state
                save_state(state_file, color_size_stock=stock_data, 
                          has_sizes=True, product_name=product_name)
            else:
                previous = previous_state.get('color_stock', {})
                for color, is_in_stock in stock_data.items():
                    was_in_stock = previous.get(color)
                    if was_in_stock is not None:
                        if not was_in_stock and is_in_stock:
                            back_in_stock.append((color, None))
                        elif was_in_stock and not is_in_stock:
                            out_of_stock.append((color, None))
                
                # Save new state
                save_state(state_file, color_stock=stock_data, 
                          has_sizes=False, product_name=product_name)
            
            # Send notifications if there are changes
            if back_in_stock or out_of_stock:
                print(f"   📧 Stock changes detected! Sending notifications...")
                for sub in subs:
                    send_stock_notification(
                        sub['email'],
                        product_name,
                        product_url,
                        back_in_stock,
                        out_of_stock
                    )
                    # Update last_notified timestamp
                    sub['last_notified'] = datetime.now().isoformat()
                    subscriptions[get_subscription_key(sub['email'], product_url)] = sub
                
                save_subscriptions(subscriptions)
                print(f"   ✅ Notifications sent to {len(subs)} subscriber(s)")
            else:
                print(f"   ℹ️  No stock changes detected")
            
        except Exception as e:
            print(f"   ❌ Error checking product: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            continue
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check complete!")


def get_subscription_key(email: str, product_url: str) -> str:
    """Generate a unique key for a subscription."""
    return hashlib.md5(f"{email}:{product_url}".encode()).hexdigest()


def run_continuous(interval_minutes: int = 15):
    """Run checks continuously at specified interval."""
    print(f"🚀 Starting continuous stock monitor (checking every {interval_minutes} minutes)")
    print(f"Press Ctrl+C to stop\n")
    
    try:
        while True:
            check_all_subscriptions()
            print(f"\n⏳ Waiting {interval_minutes} minutes until next check...\n")
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        print("\n\n👋 Stopping stock monitor. Goodbye!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Arc\'teryx Stock Monitor Scheduler')
    parser.add_argument('--once', action='store_true', 
                       help='Run once and exit (for cron jobs)')
    parser.add_argument('--interval', type=int, default=15,
                       help='Check interval in minutes (default: 15)')
    
    args = parser.parse_args()
    
    if args.once:
        # Run once (for cron jobs)
        check_all_subscriptions()
    else:
        # Run continuously
        run_continuous(args.interval)


if __name__ == "__main__":
    main()

