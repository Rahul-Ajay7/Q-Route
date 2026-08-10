"""Q-ORBIT Streamlit dashboard."""

import streamlit as st

st.set_page_config(page_title="Q-ORBIT Dashboard", layout="wide")

st.title("Q-ORBIT")
st.caption("Quantum-Optimized Route-Based Intelligent Transportation")

pages = {
    "Problem Setup": "pages/problem_setup.py",
    "Optimization": "pages/optimization.py",
    "Results": "pages/results.py",
    "Map View": "pages/map_view.py",
}

page = st.sidebar.radio("Navigation", list(pages.keys()))
module = pages[page].replace("/", ".").removesuffix(".py")
__import__(module)
