"""
Arc'teryx Stock Monitor - Streamlit Web App
DEPRECATED: This app has moved to https://arc-scraper-v2.vercel.app/
"""

import streamlit as st

# Page config
st.set_page_config(
    page_title="Arc'teryx Stock Monitor - Moved",
    page_icon="🏔️",
    layout="wide"
)

NEW_URL = "https://arc-scraper.vercel.app/"


def main():
    st.markdown(
        f"""
        <div style="
            background-color: #1a1a2e;
            border: 2px solid #e94560;
            border-radius: 12px;
            padding: 60px 40px;
            text-align: center;
            margin: 40px auto;
            max-width: 700px;
        ">
            <h1 style="color: #ffffff; margin-bottom: 10px; font-size: 2.5rem;">
                Arc'teryx Stock Monitor
            </h1>
            <h2 style="color: #e94560; margin-bottom: 30px; font-size: 1.5rem;">
                This app has moved!
            </h2>
            <p style="color: #cccccc; font-size: 1.1rem; margin-bottom: 30px;">
                We've migrated to a new, faster platform.<br>
                Please update your bookmarks.
            </p>
            <a href="{NEW_URL}" target="_self" style="
                display: inline-block;
                background-color: #e94560;
                color: #ffffff;
                padding: 16px 48px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 1.2rem;
                font-weight: bold;
            ">
                Go to the new site
            </a>
            <p style="color: #888888; font-size: 0.9rem; margin-top: 30px;">
                <a href="{NEW_URL}" style="color: #e94560;">{NEW_URL}</a>
            </p>
            <p style="color: #cccccc; font-size: 1rem; margin-top: 30px;">
                Cheers,<br>Chow
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- All previous UI code is commented out below ---

    # import json
    # import os
    # import sys
    # import hashlib
    # import secrets
    # from datetime import datetime
    # from typing import Dict, List, Optional
    # from urllib.parse import unquote
    # from dotenv import load_dotenv
    # import smtplib
    # from rate_limiter import MAX_SUBSCRIPTIONS_PER_EMAIL, MAX_ATTEMPTS_PER_EMAIL_PER_HOUR
    # from email.mime.text import MIMEText
    #
    # sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # load_dotenv()
    #
    # def get_env_var(key, default=None):
    #     try:
    #         if hasattr(st, 'secrets') and key in st.secrets:
    #             return st.secrets[key]
    #     except Exception:
    #         pass
    #     return os.getenv(key, default)
    #
    # from db import load_subscriptions, save_subscriptions, delete_subscription, get_popular_items, get_last_in_stock_times
    # from rate_limiter import check_rate_limit, record_rate_limit_attempt, get_session_id, cleanup_old_attempts
    #
    # def get_subscription_key(email, product_url):
    #     return hashlib.md5(f"{email}:{product_url}".encode()).hexdigest()
    #
    # def send_verification_email(email, token, product_url):
    #     ...
    #
    # def send_stock_notification(email, product_name, product_url, back_in_stock, out_of_stock):
    #     ...
    #
    # # Verification handling
    # try:
    #     if hasattr(st, 'query_params'):
    #         query_params = st.query_params
    #         token = query_params.get('token') if hasattr(query_params, 'get') else None
    #         if not token and 'token' in query_params:
    #             token = query_params['token']
    #     else:
    #         query_params = st.experimental_get_query_params()
    #         token_list = query_params.get('token', [])
    #         token = token_list[0] if token_list else None
    #
    #     if token:
    #         token = unquote(str(token))
    #         subscriptions = load_subscriptions()
    #         verified = False
    #         for sub_key, sub in subscriptions.items():
    #             sub_token = sub.get('token', '')
    #             if sub_token and sub_token == token:
    #                 sub['verified'] = True
    #                 save_subscriptions(subscriptions)
    #                 st.success("Email verified! You will now receive stock alerts.")
    #                 st.balloons()
    #                 verified = True
    #                 break
    #         if not verified:
    #             st.error("Invalid verification token.")
    #         else:
    #             return
    # except Exception as e:
    #     st.error(f"Error processing verification: {str(e)}")
    #
    # st.title("Arc'teryx Stock Monitor")
    # st.markdown("Get notified when Arc'teryx products come back in stock!")
    # st.info("How it works: Subscribe with your email below. ...")
    #
    # page = st.sidebar.selectbox("Navigation", ["Subscribe", "My Subscriptions", "Popular Items", "Tutorial"])
    #
    # if page == "Subscribe":
    #     st.header("Subscribe for Stock Alerts")
    #     email = st.text_input("Your Email", placeholder="your.email@example.com")
    #     product_url = st.text_input("Product URL", placeholder="https://arcteryx.com/ca/en/shop/...")
    #     if st.button("Subscribe", type="primary"):
    #         ...
    #
    # elif page == "My Subscriptions":
    #     st.header("My Subscriptions")
    #     ...
    #
    # elif page == "Popular Items":
    #     st.header("Popular Items")
    #     ...
    #
    # elif page == "Tutorial":
    #     st.header("How to Subscribe - Step by Step Tutorial")
    #     ...


if __name__ == "__main__":
    main()
