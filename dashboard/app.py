"""Read-only viewer for completed, recorded Q-ORBIT experiments."""
import json
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from team_benchmark.layout import resolve_recorded_path

st.set_page_config(page_title="Q-ORBIT results",layout="wide")
st.title("Q-ORBIT results")
st.caption("Recorded vehicle-routing experiments · synthetic INR operating costs")

folders=sorted(p for p in (ROOT/'results/comparison').iterdir()
               if p.is_dir() and (p/'runs.json').is_file() and (p/'manifest.json').is_file())
if not folders:
    st.info("No recorded experiments yet. Run the benchmark command in README.md.")
    st.stop()
names=[p.name for p in folders]
default=names.index('hybrid_v2_validation') if 'hybrid_v2_validation' in names else 0
experiment=st.sidebar.selectbox("Experiment",names,index=default)
folder=ROOT/'results/comparison'/experiment
try:
    rows=json.loads((folder/'runs.json').read_text(encoding='utf-8'))
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
except (OSError,ValueError) as exc:
    st.error(f"Could not read this experiment: {exc}")
    st.stop()
if not rows:
    st.info("This experiment has no recorded runs.")
    st.stop()

cases=sorted({r['case'] for r in rows})
case=st.sidebar.selectbox("Case",cases,index=cases.index('TC18.json') if 'TC18.json' in cases else 0)
seeds=sorted({r['seed'] for r in rows if r['case']==case})
seed=st.sidebar.selectbox("Search seed",seeds)
selected=[r for r in rows if r['case']==case and r['seed']==seed]
st.subheader(case)
st.caption(f"Optimization budget: {manifest['settings']['seconds']:g} s per method · {manifest['window_policy']} time windows")

labels={'classical_sa':'Classical SA','tunnelling_sa':'Tunnelling SA','qubo_sb':'QUBO + SB',
        'hybrid':'Hybrid v2','hybrid_v1_cached':'Old hybrid (cached)',
        'hybrid_no_qubo':'Hybrid without QUBO','hybrid_no_repair':'Hybrid without repair'}
table=pd.DataFrame([{'Method':labels.get(r['method'],r['method']),
                     'Status':r['status'],'Cost (INR)':r['cost'],
                     'Distance (km)':r.get('metrics',{}).get('distance'),
                     'Fuel (L)':r.get('metrics',{}).get('fuel_liters'),
                     'Lateness (min)':r.get('metrics',{}).get('lateness_minutes'),
                     'Optimization (s)':r['runtime_seconds']} for r in selected])
st.dataframe(table.round(3),hide_index=True,use_container_width=True)
st.download_button("Download this comparison",table.to_csv(index=False).encode('utf-8'),
                   file_name=f"{Path(case).stem}_seed{seed}.csv",mime='text/csv')
feasible=sorted((r for r in selected if r['feasible']),key=lambda r:r['cost'])
if not feasible:
    st.info("Shared construction did not find a complete feasible starting plan. Partial-route costs are excluded.")
    st.stop()
st.bar_chart(table.dropna(subset=['Cost (INR)']).set_index('Method')['Cost (INR)'])

method=st.selectbox("View a recorded route plan",[r['method'] for r in feasible],
                    format_func=lambda m:labels.get(m,m))
run=next(r for r in feasible if r['method']==method)
input_path=next((resolve_recorded_path(p) for p in manifest['input_sha256'] if Path(p).name==case),None)
if input_path and input_path.is_file():
    data=json.loads(input_path.read_text(encoding='utf-8-sig'))
    nodes={n['id']:n for n in [data['depot']]+data['customers']}
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'qorbit-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,5))
    depot=data['depot']['id']
    for i,route in enumerate(run['routes']):
        if not route:
            continue
        order=[depot]+route+[depot]
        ax.plot([nodes[c]['x'] for c in order],[nodes[c]['y'] for c in order],'-o',
                markersize=3,linewidth=1,label=str(data['vehicles'][i]['id']))
    ax.scatter(nodes[depot]['x'],nodes[depot]['y'],marker='*',s=150,c='black',label='Depot',zorder=5)
    ax.set(xlabel='Synthetic x coordinate',ylabel='Synthetic y coordinate',aspect='equal')
    ax.legend(fontsize=8,ncol=3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.caption(f"{len(data['customers'])} customers · {sum(bool(r) for r in run['routes'])} vehicles used · straight coordinate segments")
