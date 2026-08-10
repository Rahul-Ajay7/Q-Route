"""Chart helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st


def line_chart(data, title: str) -> None:
    st.line_chart(data)


def matplotlib_figure():
    fig, ax = plt.subplots()
    return fig, ax
