import streamlit as st
import requests

st.title("📈 Stock Screening Assistant")

user_query = st.text_input("Enter your query:", placeholder="e.g., Show me undervalued tech stocks under $50 with dividends")

if st.button("Run Query") and user_query:
    with st.spinner("Parsing your request..."):
        parse_response = requests.post("http://backend:8000/parse", json={"query": user_query})
        intent = parse_response.json()["intent"]

    st.subheader("Parsed Filters")
    st.json(intent)

    with st.spinner("Screening stocks..."):
        screen_response = requests.post("http://backend:8000/screen", json={"filters": intent})
        results = screen_response.json()["results"]

    st.subheader("Top Picks")
    st.dataframe(results)

    with st.spinner("Fetching deeper insights..."):
        research_response = requests.post("http://backend:8000/research", json={"tickers": [r["ticker"] for r in results[:3]]})
        task_id = research_response.json()["task_id"]
        st.write(f"Started research task: {task_id}")