"""
Database utilities using Supabase
Requires Supabase to be configured
"""
import os
from typing import Dict, List, Optional
from datetime import datetime

# Import Supabase
try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase package is required. Install with: pip install supabase")


def get_supabase_client():
    """Get Supabase client. Raises error if not configured."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    # Try Streamlit secrets if available
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            url = url or st.secrets.get('SUPABASE_URL')
            key = key or st.secrets.get('SUPABASE_KEY')
    except:
        pass
    
    if not url or not key:
        raise ValueError(
            "Supabase not configured. Please set SUPABASE_URL and SUPABASE_KEY "
            "as environment variables or in Streamlit secrets."
        )
    
    return create_client(url, key)


def load_subscriptions() -> Dict:
    """Load subscriptions from Supabase."""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('subscriptions').select('*').execute()
        subscriptions = {}
        for row in response.data:
            subscriptions[row['id']] = {
                'email': row['email'],
                'product_url': row['product_url'],
                'token': row['token'],
                'verified': row.get('verified', False),
                'created_at': row.get('created_at'),
                'last_notified': row.get('last_notified')
            }
        return subscriptions
    except Exception as e:
        raise Exception(f"Error loading subscriptions from Supabase: {e}")


def save_subscriptions(subscriptions: Dict):
    """Save subscriptions to Supabase."""
    supabase = get_supabase_client()
    
    try:
        # Upsert all subscriptions
        for sub_id, sub_data in subscriptions.items():
            supabase.table('subscriptions').upsert({
                'id': sub_id,
                'email': sub_data['email'],
                'product_url': sub_data['product_url'],
                'token': sub_data['token'],
                'verified': sub_data.get('verified', False),
                'created_at': sub_data.get('created_at'),
                'last_notified': sub_data.get('last_notified')
            }).execute()
    except Exception as e:
        raise Exception(f"Error saving subscriptions to Supabase: {e}")


def load_state(product_url: str) -> Dict:
    """Load the last known stock state for a product from Supabase."""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('stock_state').select('*').eq('product_url', product_url).execute()
        
        if response.data and len(response.data) > 0:
            row = response.data[0]
            return {
                'color_stock': row.get('color_stock') or {},
                'color_size_stock': row.get('color_size_stock') or {},
                'last_checked': row.get('last_checked'),
                'has_sizes': row.get('has_sizes'),
                'product_name': row.get('product_name')
            }
        else:
            return {'color_stock': {}, 'color_size_stock': {}, 'last_checked': None, 'has_sizes': None}
    except Exception as e:
        raise Exception(f"Error loading state from Supabase: {e}")


def save_state(product_url: str, color_stock: Dict = None, color_size_stock: Dict = None,
               has_sizes: bool = None, product_name: str = None):
    """Save the current stock state to Supabase."""
    supabase = get_supabase_client()
    
    state_data = {
        'product_url': product_url,
        'last_checked': datetime.now().isoformat()
    }
    
    if product_name is not None:
        state_data['product_name'] = product_name
    
    if has_sizes is not None:
        state_data['has_sizes'] = has_sizes
    
    if color_stock is not None:
        state_data['color_stock'] = color_stock
    
    if color_size_stock is not None:
        state_data['color_size_stock'] = color_size_stock
    
    try:
        supabase.table('stock_state').upsert(state_data).execute()
    except Exception as e:
        raise Exception(f"Error saving state to Supabase: {e}")


def save_stock_history(product_url: str, product_name: str, color: str, size: Optional[str] = None):
    """Record when an item comes back in stock."""
    supabase = get_supabase_client()
    
    try:
        history_data = {
            'product_url': product_url,
            'product_name': product_name,
            'color': color,
            'size': size,
            'came_back_in_stock_at': datetime.now().isoformat()
        }
        supabase.table('stock_history').insert(history_data).execute()
    except Exception as e:
        raise Exception(f"Error saving stock history to Supabase: {e}")


def get_popular_items(limit: int = 20) -> List[Dict]:
    """
    Get popular items based on number of subscriptions.
    Returns list of products with subscription counts.
    """
    supabase = get_supabase_client()
    
    try:
        # Get subscription counts per product
        subscriptions = load_subscriptions()
        product_counts = {}
        for sub in subscriptions.values():
            if sub.get('verified', False):
                product_url = sub['product_url']
                product_counts[product_url] = product_counts.get(product_url, 0) + 1
        
        # Get product details from stock_state
        popular_items = []
        for product_url, sub_count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
            response = supabase.table('stock_state').select('*').eq('product_url', product_url).execute()
            if response.data and len(response.data) > 0:
                row = response.data[0]
                popular_items.append({
                    'product_url': product_url,
                    'product_name': row.get('product_name', 'Unknown Product'),
                    'subscription_count': sub_count,
                    'has_sizes': row.get('has_sizes', False),
                    'last_checked': row.get('last_checked')
                })
        
        return popular_items
    except Exception as e:
        raise Exception(f"Error getting popular items from Supabase: {e}")


def get_last_in_stock_times(product_url: str) -> Dict:
    """
    Get the last time each color/size combination came back in stock.
    Returns a dict with structure:
    {
        'color_name': {
            'size_name': 'timestamp',
            None: 'timestamp'  # for products without sizes
        }
    }
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('stock_history')\
            .select('color, size, came_back_in_stock_at')\
            .eq('product_url', product_url)\
            .order('came_back_in_stock_at', desc=True)\
            .execute()
        
        last_times = {}
        seen_combinations = set()
        for row in response.data:
            color = row['color']
            size = row.get('size')
            timestamp = row['came_back_in_stock_at']
            
            # Create a unique key for this color/size combination
            combination_key = (color, size)
            
            # Since results are ordered by timestamp DESC, first occurrence is most recent
            if combination_key not in seen_combinations:
                seen_combinations.add(combination_key)
                
                if color not in last_times:
                    last_times[color] = {}
                
                last_times[color][size] = timestamp
        
        return last_times
    except Exception as e:
        raise Exception(f"Error getting last in-stock times from Supabase: {e}")

