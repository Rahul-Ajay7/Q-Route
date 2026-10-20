"""The results viewer must show real data and handle construction failures."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_results_viewer_and_failed_construction_case():
    root=Path(__file__).resolve().parents[1]
    app=AppTest.from_file(str(root/'dashboard/app.py'),default_timeout=30).run()
    assert not app.exception
    assert len(app.dataframe)==1
    assert 'Cost (INR)' in app.dataframe[0].value.columns
    app.sidebar.selectbox[1].select('TC15.json').run()
    assert not app.exception
    assert any('complete feasible starting plan' in message.value for message in app.info)
