import streamlit as st
import requests
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import pandas as pd
import time
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Stock Screening Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
    <style>
        .block-container {
            max-width: 1000px;
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
    </style>""",
    unsafe_allow_html=True
)

# Constants
BACKEND_URL = "http://localhost:8000"  # Update if hosted elsewhere


# --- Helper Functions ---
def send_query_to_backend(query_text):
    try:
        logger.info(f"Sending query to backend: {f"{BACKEND_URL}/query"}")
        response = requests.post(f"{BACKEND_URL}/query", json={"query": query_text}) 
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Backend error: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def render_aggrid_table(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=False)
    gb.configure_side_bar()
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(autoSizeStrategy={'type': 'fitCellContents', 'skipHeader': False})
    grid_options = gb.build()

    AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        theme='streamlit',
        height=200,
        width=None,
        update_mode='MODEL_CHANGED',
        allowSorting=True,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
    )


# --- Main App UI ---
st.title("📈 Stock Screening Assistant")

# Initialize session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# Input section
with st.form(key='user_input_form', clear_on_submit=True):
    user_input = st.text_input("Enter your stock screening request: Show me 3 undervalued tech stocks under $250 with dividends", key="input_text")
    col1, col2 = st.columns([0.78, 0.22])
    with col1:
        submit_button = col1.form_submit_button("Send")
    with col2:
        # Placeholder for the spinner
        spinner_placeholder = st.empty()

# Handle form submission
if submit_button and user_input.strip():
    start_time = time.time()  # Start timing before sending request
    with spinner_placeholder:
        with st.spinner("Processing your query..."):
            screen_response = send_query_to_backend(user_input)
    end_time = time.time()  # End timing after receiving response
    elapsed_time = round(end_time - start_time, 2)  # Rounded to 2 decimals

    # Insert at the beginning to show latest query first
    st.session_state['chat_history'].insert(0, {
        "query": user_input,
        "screen_response": screen_response,
        "timestamp": start_time,
        "elapsed_time": elapsed_time
    })

# Display chat history
for idx, chat in enumerate(st.session_state['chat_history']):
    try:
        st.markdown(f"**Query:** {chat['query']}")
        # Show elapsed time if available
        logger.info(f"Chat {idx} timestamp: {chat['timestamp']}, elapsed time: {chat['elapsed_time']}")
        if 'elapsed_time' in chat:
            st.markdown(f"(*Elapsed Time: {chat['elapsed_time']} seconds*)")

        response = chat['screen_response']
        # logger.info(f"Response from backend {response}")

        if response.get('clarification_needed'):
            st.warning(response.get('error', 'Clarification required.'))
            # parsed = response.get('parsed', {})
            # if parsed:
            #     st.json(parsed, expanded=False)
            st.info("Please send a new request with clear sector and filters.")

        elif 'error' in response:
            st.error(response['error'])

        elif 'results' in response:
            intent = response.get('intent', {})
            results = response.get('results', [])
            explanation = response.get('explanation', '')
            safe_explanation = re.sub(r'(?<!\$)\$(?!\$)', r'\$', explanation)

            # if intent:
            #     st.markdown("**Parsed Intent:**")
            #     st.json(intent, expanded=False)

            if explanation:
                st.markdown("**Explanation:**")
                st.markdown(safe_explanation)

            if results:
                df = pd.DataFrame(results)
                df.rename(columns={
                    'peRatio': 'P/E Ratio',
                    'pbRatio': 'P/B Ratio',
                    'dividendYield': 'Dividend Yield',
                    'debtToEquity': 'Debt to Equity',
                    'revenueGrowth': 'Revenue Growth',
                    'freeCashFlowYield': 'Free Cash Flow Yield',
                    'price': 'Price',
                    'sector': 'Sector',
                    'marketCap': 'Market Cap',
                    'symbol': 'Symbol',
                    'name': 'Company Name',
                }, inplace=True)

                # Define which columns should be shown as percentages
                pct_columns = ['Revenue Growth', 'Free Cash Flow Yield']
                pct_columns2 = ['Dividend Yield']

                for col in df.columns:
                    if col in pct_columns:
                        # Convert decimal to percentage string with one decimal place
                        df[col] = df[col].apply(lambda x: f"{x * 100:.1f}%" if pd.notna(x) and isinstance(x, (int, float)) else "")
                    elif col in pct_columns2:
                        # Convert decimal to percentage string with one decimal place
                        df[col] = df[col].apply(lambda x: f"{x}%" if pd.notna(x) and isinstance(x, (int, float)) else "")
                    elif pd.api.types.is_float_dtype(df[col]):
                        # Round regular float columns to 2 decimals
                        df[col] = df[col].round(2)

                st.markdown("**Results:**")
                render_aggrid_table(df)
            else:
                st.info("No matching stocks found.")
        else:
            st.warning("Unexpected response structure.")
    except Exception as e:
        logger.exception(f"Error processing response: {e}")
        
# Footer
st.markdown("<br><hr><center>Made with ❤️ by Your Name</center>", unsafe_allow_html=True)