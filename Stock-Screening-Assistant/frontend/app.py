import streamlit as st
import requests
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import pandas as pd
import time
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
        response = requests.post(f"{BACKEND_URL}/parse", json={"query": query_text})
        if response.status_code == 200:
            intent = response.json()
            logger.info(f"Streamlit - Parsed intent: {intent}")
            
            # Send intent to screening endpoint
            screen_response = requests.post(f"{BACKEND_URL}/screen", json=intent)
            logger.info(f"Streamlit - Screening results: {screen_response.json()}")
            if screen_response.status_code == 200:
                return screen_response.json()
            else:
                return {"error": f"Backend error: {screen_response.text}"}
        else:
            return {"error": "Failed to parse intent."}
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
    user_input = st.text_input("Enter your stock screening request:", key="input_text")
    col1, col2 = st.columns([0.78, 0.22])
    with col1:
        submit_button = col1.form_submit_button("Send")
    with col2:
        # Placeholder for the spinner
        spinner_placeholder = st.empty()

# Handle form submission
if submit_button and user_input.strip():
    with spinner_placeholder:
        with st.spinner("Retrieving stock data..."):
            screen_response = send_query_to_backend(user_input)

    # Insert at the beginning to show latest query first
    st.session_state['chat_history'].insert(0, {
        "query": user_input,
        "screen_response": screen_response,
        "timestamp": time.time()
    })

# Display chat history
for idx, chat in enumerate(st.session_state['chat_history']):
    # st.markdown("---")
    st.markdown(f"**Query:** {chat['query']}")

    if chat['screen_response']['error'] is not None:
        st.error(chat['screen_response']['error'])
    elif chat['screen_response'].get('success'):
        # logger.info(f"Streamlit - Displaying screen response: {chat['screen_response']}")
        results = chat['screen_response'].get('results', [])
        if results:
            df = results.copy()
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(df)
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

            # Format numbers
            for col in df.select_dtypes(include=['float']).columns:
                df[col] = df[col].round(2)

            st.markdown("**Results:**")
            render_aggrid_table(df)
        else:
            st.info("No matching stocks found.")
    else:
        st.warning("No results returned.")

# Footer
st.markdown("<br><hr><center>Made with ❤️ by Your Name</center>", unsafe_allow_html=True)