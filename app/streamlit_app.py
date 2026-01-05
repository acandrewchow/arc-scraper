"""
Arc'teryx Stock Monitor - Streamlit Web App
Allows users to check stock and subscribe for notifications
"""

import streamlit as st
import json
import os
import sys
import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import unquote
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

# Add app directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable from Streamlit secrets or os.getenv."""
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    # Fallback to environment variables (for local .env file)
    return os.getenv(key, default)

# Page config
st.set_page_config(
    page_title="Arc'teryx Stock Monitor",
    page_icon="🏔️",
    layout="wide"
)

# Import database functions (uses Supabase or falls back to JSON)
from db import load_subscriptions, save_subscriptions, delete_subscription, get_popular_items, get_last_in_stock_times


def get_subscription_key(email: str, product_url: str) -> str:
    """Generate a unique key for a subscription."""
    return hashlib.md5(f"{email}:{product_url}".encode()).hexdigest()


def send_verification_email(email: str, token: str, product_url: str):
    """Send verification email to user."""
    try:
        sender = get_env_var('SENDER_EMAIL')
        password = get_env_var('SENDER_PASSWORD')
        smtp_server = get_env_var('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(get_env_var('SMTP_PORT', '587'))
        
        if not all([sender, password]):
            return False
        
        # Get the base URL - try to detect from Streamlit config or use default
        base_url = get_env_var('APP_URL', 'http://localhost:8501')
        # Remove trailing slash if present
        base_url = base_url.rstrip('/')
        verify_url = f"{base_url}?token={token}"
        
        body = f"""
Thank you for subscribing to Arc'teryx stock alerts!

Please verify your email by clicking this link:
{verify_url}

Product: {product_url}

If you didn't subscribe, you can ignore this email.
        """
        
        msg = MIMEText(body, 'plain')
        msg['From'] = sender
        msg['To'] = email
        msg['Subject'] = "Verify your Arc'teryx Stock Alert Subscription"
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False


def send_stock_notification(email: str, product_name: str, product_url: str, 
                           back_in_stock: List, out_of_stock: List):
    """Send stock notification email."""
    try:
        sender = get_env_var('SENDER_EMAIL')
        password = get_env_var('SENDER_PASSWORD')
        smtp_server = get_env_var('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(get_env_var('SMTP_PORT', '587'))
        
        if not all([sender, password]):
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
        
        msg = MIMEText(body, 'plain')
        msg['From'] = sender
        msg['To'] = email
        msg['Subject'] = f"🎉 Arc'teryx {product_name} Stock Alert!"
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False


def main():
    # Handle verification first (before main UI)
    try:
        # Try new API first (Streamlit 1.28+)
        if hasattr(st, 'query_params'):
            query_params = st.query_params
            # In Streamlit 1.28+, query_params is a dict-like object
            # Access it directly or use .get()
            token = query_params.get('token') if hasattr(query_params, 'get') else None
            if not token and 'token' in query_params:
                # Try direct access
                token = query_params['token']
        else:
            # Fallback to experimental API (returns dict with list values)
            query_params = st.experimental_get_query_params()
            token_list = query_params.get('token', [])
            token = token_list[0] if token_list else None
        
        if token:
            # URL decode the token in case it's encoded
            token = unquote(str(token))
     
            subscriptions = load_subscriptions()
            verified = False
            
            # Try to find matching subscription
            for sub_key, sub in subscriptions.items():
                sub_token = sub.get('token', '')
                # Compare tokens (both decoded)
                if sub_token and sub_token == token:
                    sub['verified'] = True
                    save_subscriptions(subscriptions)
                    st.success("✅ Email verified! You will now receive stock alerts.")
                    st.balloons()
                    verified = True
                    break
            
            if not verified:
                # Show more helpful error message
                st.error(f"Invalid verification token.")
                st.info("💡 Tip: Make sure you're using the exact link from your verification email.")
            else:
                return  # Exit early after successful verification
    except Exception as e:
        st.error(f"Error processing verification: {str(e)}")
    
    st.title("🏔️ Arc'teryx Stock Monitor")
    st.markdown("Get notified when Arc'teryx products come back in stock!")
    
    # Info banner
    st.info("📧 **How it works:** Subscribe with your email below. We'll automatically check stock every 15 minutes and email you when items come back in stock!")
    
    # Sidebar for navigation
    page = st.sidebar.selectbox("Navigation", ["Subscribe", "My Subscriptions", "Popular Items"])
    
    if page == "Subscribe":
        st.header("Subscribe for Stock Alerts")
        
        email = st.text_input("Your Email", placeholder="your.email@example.com")
        product_url = st.text_input(
            "Product URL",
            placeholder="https://arcteryx.com/ca/en/shop/...",
            help="Enter the full URL of the Arc'teryx product page"
        )
        
        if st.button("Subscribe", type="primary"):
            if not email or '@' not in email:
                st.error("Please enter a valid email address")
            elif not product_url or 'arcteryx.com' not in product_url:
                st.error("Please enter a valid Arc'teryx product URL")
            else:
                subscriptions = load_subscriptions()
                sub_key = get_subscription_key(email, product_url)
                
                if sub_key in subscriptions:
                    sub = subscriptions[sub_key]
                    if sub.get('verified'):
                        st.warning("You are already subscribed to this product!")
                    else:
                        # Resend verification
                        if send_verification_email(email, sub['token'], product_url):
                            st.info("Verification email resent! Please check your inbox.")
                        else:
                            st.error("Failed to send verification email. Please check your email configuration.")
                else:
                    # Create new subscription
                    token = secrets.token_urlsafe(32)
                    subscriptions[sub_key] = {
                        'email': email,
                        'product_url': product_url,
                        'token': token,
                        'verified': False,
                        'created_at': datetime.now().isoformat()
                    }
                    save_subscriptions(subscriptions)
                    
                    if send_verification_email(email, token, product_url):
                        st.success("Subscription created! Please check your email to verify your subscription.")
                    else:
                        st.error("Failed to send verification email. Please check your email configuration.")
    
    elif page == "My Subscriptions":
        st.header("My Subscriptions")
        
        email = st.text_input("Enter your email to view subscriptions", placeholder="your.email@example.com")
        
        if email and '@' in email:
            subscriptions = load_subscriptions()
            # Include the subscription ID (key) with each subscription
            user_subs = [(sub_id, sub) for sub_id, sub in subscriptions.items() if sub['email'] == email]
            
            if not user_subs:
                st.info("No subscriptions found for this email.")
            else:
                for sub_id, sub in user_subs:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.write(f"**Product:** {sub['product_url']}")
                        col2.write(f"**Status:** {'✅ Verified' if sub.get('verified') else '⏳ Pending'}")
                        if sub.get('verified'):
                            unsubscribe_token = sub['token']
                            if col3.button("Unsubscribe", key=f"unsub_{sub['token']}"):
                                try:
                                    delete_subscription(sub_id)
                                    st.success("Unsubscribed successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error unsubscribing: {e}")
                        st.divider()
    
    elif page == "Popular Items":
        st.header("🔥 Popular Items")
        st.markdown("See the most subscribed products and when each size/color last came back in stock.")
        
        try:
            popular_items = get_popular_items(limit=50)
            
            if not popular_items:
                st.info("No popular items yet. Subscribe to products to see them here!")
            else:
                st.metric("Total Popular Products", len(popular_items))
                
                for item in popular_items:
                    with st.expander(f"🏔️ {item['product_name']} ({item['subscription_count']} subscribers)", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.write(f"**Product URL:** {item['product_url']}")
                            if item.get('last_checked'):
                                try:
                                    last_checked_str = item['last_checked']
                                    # Handle different timestamp formats
                                    if last_checked_str.endswith('Z'):
                                        last_checked_str = last_checked_str.replace('Z', '+00:00')
                                    last_checked = datetime.fromisoformat(last_checked_str)
                                    st.caption(f"Last checked: {last_checked.strftime('%Y-%m-%d %H:%M:%S')}")
                                except Exception:
                                    st.caption(f"Last checked: {item['last_checked']}")
                        
                        with col2:
                            st.metric("Subscribers", item['subscription_count'])
                        
                        # Get last in-stock times
                        try:
                            last_times = get_last_in_stock_times(item['product_url'])
                            
                            if last_times:
                                st.subheader("Last In-Stock Times")
                                
                                if item.get('has_sizes'):
                                    # Display as table with sizes
                                    for color, size_times in last_times.items():
                                        st.write(f"**{color}**")
                                        if size_times:
                                            # Create a table for this color
                                            table_data = []
                                            for size, timestamp in sorted(size_times.items(), key=lambda x: x[1] if x[1] else '', reverse=True):
                                                if timestamp:
                                                    try:
                                                        timestamp_str = timestamp.replace('Z', '+00:00') if timestamp.endswith('Z') else timestamp
                                                        dt = datetime.fromisoformat(timestamp_str)
                                                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                                                    except Exception:
                                                        time_str = str(timestamp)
                                                    table_data.append({
                                                        'Size': size if size else 'N/A',
                                                        'Last In Stock': time_str
                                                    })
                                            
                                            if table_data:
                                                st.table(table_data)
                                            else:
                                                st.caption("No stock history available")
                                        st.divider()
                                else:
                                    # Display without sizes
                                    table_data = []
                                    for color, size_times in last_times.items():
                                        if size_times:
                                            # Get the most recent time for this color
                                            timestamps = [ts for ts in size_times.values() if ts]
                                            if timestamps:
                                                latest = max(timestamps)
                                                try:
                                                    latest_str = latest.replace('Z', '+00:00') if latest.endswith('Z') else latest
                                                    dt = datetime.fromisoformat(latest_str)
                                                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                                                except Exception:
                                                    time_str = str(latest)
                                                table_data.append({
                                                    'Color': color,
                                                    'Last In Stock': time_str
                                                })
                                    
                                    if table_data:
                                        st.table(table_data)
                                    else:
                                        st.caption("No stock history available")
                            else:
                                st.info("No stock history available for this product yet.")
                        except Exception as e:
                            st.error(f"Error loading stock history: {e}")
                        
                        st.divider()
        
        except Exception as e:
            st.error(f"Error loading popular items: {e}")
            st.info("Make sure the stock_history table has been created in your Supabase database.")


if __name__ == "__main__":
    main()