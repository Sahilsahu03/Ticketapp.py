import streamlit as st
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timezone

# Configuration and Setup
st.set_page_config(layout="wide")

# Constants and Configuration
URL_OPEN_TICKETS = "http://172.16.0.207/OTRS_system/Download11.php?process=xidops"
URL_NEW_DATA = "http://172.16.3.229/XID_OTRS2/11.php"
REQUIRED_COLUMNS_OPEN_TICKETS = ["username", "resolved", "Received_Timestamp"]
REQUIRED_COLUMNS_NEW_DATA = ["username", "created_at"]
FILTER_USERS = [
    "priya.tomar", "anjali.panchal", "anurag", "ashish", "Jhanvi", "Juhi.verma", 
    "Khushbu", "kripashankar", "manisha", "tariq", "Piyush", "sakshi.lohumi", 
    "Sanjeev Kumar", "utkarsh singh", "medha", "sumit j"
]

# Custom CSS
st.markdown(
    """
    <style>
    .header-section {
        background-color: #f8f9fa;
        padding: 1rem 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .custom-title {
        font-size: 32px;
        font-weight: bold;
        color: #4CAF50;
        margin: 0;
        padding: 0;
    }
    .stats-card {
        background-color: #f1f8e9;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stats-number {
        font-size: 36px;
        font-weight: bold;
        color: #4CAF50;
    }
    .stats-label {
        font-size: 14px;
        color: #555;
    }
    .table {
        font-size: 12px;
    }
    .block-container {
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Create a container for the header section
st.markdown('<div class="header-section">', unsafe_allow_html=True)

# Layout for title and fetch button
header_cols = st.columns([2, 1])

with header_cols[0]:
    st.markdown('<h1 class="custom-title">Open Tickets Viewer</h1>', unsafe_allow_html=True)
    st.markdown('<p>Track open tickets, duration and daily ticket counts</p>', unsafe_allow_html=True)

with header_cols[1]:
    st.write("")  # Add some vertical spacing
    fetch_data_button = st.button("Fetch Data", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

def fetch_and_process_data(url, required_columns):
    """Fetch and process data from the given URL."""
    response = requests.get(url)
    response.raise_for_status()
    csv_data = StringIO(response.text)
    df = pd.read_csv(csv_data, delimiter=',', quotechar='"', skip_blank_lines=True, on_bad_lines='skip')
    
    if df.shape[1] == 24:
        df = df.iloc[:, :23]
    
    if all(col in df.columns for col in required_columns):
        df_cleaned = df[required_columns].copy()
        if "resolved" in required_columns:
            df_cleaned['resolved'] = pd.to_numeric(df_cleaned['resolved'], errors='coerce')
        if "Received_Timestamp" in required_columns:
            df_cleaned['Received_Timestamp'] = pd.to_datetime(df_cleaned['Received_Timestamp'], errors='coerce')
            df_cleaned['Received_Timestamp'] = df_cleaned['Received_Timestamp'].dt.tz_localize(None)  # Remove timezone awareness
        if "created_at" in required_columns:
            df_cleaned['created_at'] = pd.to_datetime(df_cleaned['created_at'], errors='coerce').dt.date
        return df_cleaned
    else:
        raise ValueError("Required columns missing in dataset")

def calculate_open_duration(df):
    """Calculate how long each ticket has been open and categorize by hourly buckets."""
    open_tickets = df[df['resolved'].isin([0, 2])].copy()
    now = datetime.now()
    open_tickets['Hours Open'] = (now - open_tickets['Received_Timestamp']).dt.total_seconds() / 3600
    
    # Create hour categories (1h, 2h, ..., 10h, >10h)
    hour_categories = {}
    for i in range(1, 11):
        hour_categories[f"{i}h"] = [(i-1), i]
    hour_categories[">10h"] = [10, float('inf')]
    
    # Create a dictionary to store user counts by hour category
    user_hour_counts = {}
    
    # Count total open tickets per user
    open_ticket_counts = open_tickets.groupby('username').size().reset_index(name='Total Open Tickets')
    
    # Get unique usernames
    usernames = open_tickets['username'].unique()
    
    # Initialize results dictionary
    results = {}
    
    # For each username, count tickets in each hour category
    for username in usernames:
        user_tickets = open_tickets[open_tickets['username'] == username]
        user_data = {'username': username, 'Total Open Tickets': len(user_tickets)}
        
        # Count tickets in each hour category
        for category, (min_hour, max_hour) in hour_categories.items():
            count = len(user_tickets[(user_tickets['Hours Open'] > min_hour) & (user_tickets['Hours Open'] <= max_hour)])
            user_data[category] = count
        
        results[username] = user_data
    
    # Convert results to DataFrame
    columns = ['username', 'Total Open Tickets'] + [f"{i}h" for i in range(1, 11)] + ['>10h']
    result_df = pd.DataFrame([results[username] for username in results], columns=columns)
    
    return result_df, open_ticket_counts['Total Open Tickets'].sum()

def fetch_and_process_new_data():
    """Fetch today's data from the new source and count tickets per user."""
    df_new = fetch_and_process_data(URL_NEW_DATA, REQUIRED_COLUMNS_NEW_DATA)
    today = datetime.today().date()
    df_new = df_new[df_new['created_at'] == today]
    user_counts = df_new[df_new['username'].isin(FILTER_USERS)].groupby('username').size().reset_index(name='Ticket Count')
    total_today = user_counts['Ticket Count'].sum() if not user_counts.empty else 0
    return user_counts, total_today

# Main Application Logic
if fetch_data_button:
    try:
        with st.spinner("Fetching and processing data..."):
            # Fetch and process open tickets data
            df_cleaned = fetch_and_process_data(URL_OPEN_TICKETS, REQUIRED_COLUMNS_OPEN_TICKETS)
            open_duration_summary, total_open_tickets = calculate_open_duration(df_cleaned)
            
            # Fetch and process new data for today
            user_ticket_counts, total_today_tickets = fetch_and_process_new_data()
            
            # Display Summary Cards
            st.markdown("### Dashboard Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{total_open_tickets}</div>
                    <div class="stats-label">Total Open Tickets</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{total_today_tickets}</div>
                    <div class="stats-label">Tickets Closed Today</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Create tabs for different views
            tab1, tab2 = st.tabs(["Open Ticket Duration", "Closed Ticket Count"])
            
            with tab1:
                st.write("### Open Tickets by Duration (Hours)")
                st.table(open_duration_summary)
                
                # Export option for open tickets
                csv_open_duration = open_duration_summary.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Open Tickets Duration",
                    data=csv_open_duration,
                    file_name="open_tickets_duration.csv",
                    mime="text/csv"
                )
            
            with tab2:
                st.write("### Today's Ticket Count for Selected Users")
                st.table(user_ticket_counts)
                
                # Export option for today's tickets
                csv_user_counts = user_ticket_counts.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Today's Ticket Count",
                    data=csv_user_counts,
                    file_name="todays_ticket_count.csv",
                    mime="text/csv"
                )
                
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data: {e}")
    except ValueError as e:
        st.error(f"Data processing error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
else:
    # Display instructions when app first loads
    st.info("Click the 'Fetch Data' button above to load ticket information.")