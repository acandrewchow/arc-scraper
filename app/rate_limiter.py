"""
Rate limiting utilities to prevent abuse of subscription system
"""
import os
from typing import Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase package is required. Install with: pip install supabase")


def get_supabase_client():
    """Get Supabase client. Raises error if not configured."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
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

MAX_SUBSCRIPTIONS_PER_EMAIL = int(os.getenv('MAX_SUBSCRIPTIONS_PER_EMAIL', '50'))
MAX_ATTEMPTS_PER_EMAIL_PER_HOUR = int(os.getenv('MAX_ATTEMPTS_PER_EMAIL_PER_HOUR', '10'))
MAX_ATTEMPTS_PER_SESSION_PER_HOUR = int(os.getenv('MAX_ATTEMPTS_PER_SESSION_PER_HOUR', '20'))
RATE_LIMIT_WINDOW_HOURS = int(os.getenv('RATE_LIMIT_WINDOW_HOURS', '1'))


def get_session_id() -> str:
    """
    Get a unique session identifier.
    """
    try:
        import streamlit as st
        if 'session_id' not in st.session_state:
            import secrets
            st.session_state.session_id = secrets.token_hex(16)
        return st.session_state.session_id
    except:
        # Fallback if Streamlit is not available
        import secrets
        return secrets.token_hex(16)


def record_rate_limit_attempt(email: str, session_id: str, success: bool = False):
    """
    Record a rate limit attempt in the database.
    
    We track email and session_id for rate limiting.
    """
    supabase = get_supabase_client()
    
    try:
        attempt_data = {
            'email': email.lower().strip(),
            'session_id': session_id,
            'success': success,
            'attempted_at': datetime.now().isoformat()
        }
        
        supabase.table('rate_limit_attempts').insert(attempt_data).execute()
    except Exception as e:
        # Log error but don't fail - rate limiting should be best effort
        print(f"Error recording rate limit attempt: {e}")


def cleanup_old_attempts():
    """Clean up rate limit attempts older than the window."""
    supabase = get_supabase_client()
    
    try:
        cutoff_time = (datetime.now() - timedelta(hours=RATE_LIMIT_WINDOW_HOURS + 1)).isoformat()
        supabase.table('rate_limit_attempts').delete().lt('attempted_at', cutoff_time).execute()
    except Exception as e:
        print(f"Error cleaning up old rate limit attempts: {e}")


def count_email_subscriptions(email: str) -> int:
    """Count how many verified subscriptions an email has."""
    try:
        from db import load_subscriptions
        subscriptions = load_subscriptions()
        email_lower = email.lower().strip()
        count = sum(1 for sub in subscriptions.values() 
                   if sub.get('email', '').lower().strip() == email_lower 
                   and sub.get('verified', False))
        return count
    except Exception as e:
        print(f"Error counting email subscriptions: {e}")
        return 0


def count_email_attempts(email: str, window_hours: int = RATE_LIMIT_WINDOW_HOURS) -> int:
    """Count subscription attempts for an email in the time window."""
    supabase = get_supabase_client()
    
    try:
        cutoff_time = (datetime.now() - timedelta(hours=window_hours)).isoformat()
        response = supabase.table('rate_limit_attempts')\
            .select('id')\
            .eq('email', email.lower().strip())\
            .gte('attempted_at', cutoff_time)\
            .execute()
        
        return len(response.data) if response.data else 0
    except Exception as e:
        print(f"Error counting email attempts: {e}")
        return 0


def count_session_attempts(session_id: str, window_hours: int = RATE_LIMIT_WINDOW_HOURS) -> int:
    """Count subscription attempts for a session in the time window."""
    supabase = get_supabase_client()
    
    try:
        cutoff_time = (datetime.now() - timedelta(hours=window_hours)).isoformat()
        response = supabase.table('rate_limit_attempts')\
            .select('id')\
            .eq('session_id', session_id)\
            .gte('attempted_at', cutoff_time)\
            .execute()
        
        return len(response.data) if response.data else 0
    except Exception as e:
        print(f"Error counting session attempts: {e}")
        return 0


def check_rate_limit(email: str, session_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if a subscription attempt should be allowed.
    Returns (allowed, error_message).
    
    Checks:
    1. Max subscriptions per email
    2. Max attempts per email per hour
    3. Max attempts per session per hour
    """
    if not session_id:
        session_id = get_session_id()
    
    email = email.lower().strip()
    
    # Check 1: Max subscriptions per email
    current_subscriptions = count_email_subscriptions(email)
    if current_subscriptions >= MAX_SUBSCRIPTIONS_PER_EMAIL:
        return False, f"You have reached the maximum of {MAX_SUBSCRIPTIONS_PER_EMAIL} subscriptions per email address. Please unsubscribe from some products before adding new ones."
    
    # Check 2: Max attempts per email per hour
    email_attempts = count_email_attempts(email)
    if email_attempts >= MAX_ATTEMPTS_PER_EMAIL_PER_HOUR:
        return False, f"Too many subscription attempts. Please wait before trying again. (Limit: {MAX_ATTEMPTS_PER_EMAIL_PER_HOUR} attempts per hour)"
    
    # Check 3: Max attempts per session per hour
    session_attempts = count_session_attempts(session_id)
    if session_attempts >= MAX_ATTEMPTS_PER_SESSION_PER_HOUR:
        return False, f"Too many subscription attempts from this session. Please wait before trying again. (Limit: {MAX_ATTEMPTS_PER_SESSION_PER_HOUR} attempts per hour)"
    
    return True, None
