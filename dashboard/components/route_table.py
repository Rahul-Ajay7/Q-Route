"""Route table component."""

from __future__ import annotations

import streamlit as st


def route_table(routes) -> None:
    st.dataframe(routes)
