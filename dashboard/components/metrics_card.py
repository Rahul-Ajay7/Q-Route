"""Metric card component."""

import streamlit as st


def metrics_card(label: str, value, delta=None) -> None:
    st.metric(label=label, value=value, delta=delta)
