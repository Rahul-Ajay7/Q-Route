"""Export static scientific plots and a flat CSV from one completed suite."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .solvers import METHODS
from .report import comparisons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directory",type=Path)
    a=ap.parse_args()
    rows=json.loads((a.directory/'runs.json').read_text(encoding='utf-8'))
    flat=[]
    for r in rows:
        flat.append({**{k:r.get(k) for k in ('case','case_id','seed','method','status','feasible','cost',
                      'initial_cost','runtime_seconds','budget_overrun_seconds','construction_seconds','total_seconds')},
                     **r.get('metrics',{}),**r.get('stats',{})})
    keys=list(dict.fromkeys(k for r in flat for k in r))
    with (a.directory/'runs.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys)
        writer.writeheader()
        writer.writerows(flat)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    labels={'classical_sa':'Classical SA','tunnelling_sa':'Tunnelling SA','qubo_sb':'QUBO + SB','hybrid':'Hybrid'}
    values=[]
    for method in METHODS:
        case_values=[]
        for case in sorted({r['case'] for r in rows}):
            good=[r for r in rows if r['method']==method and r['case']==case and r['feasible']]
            if good:
                case_values.append(np.mean([100*(r['initial_cost']-r['cost'])/max(r['initial_cost'],1e-9) for r in good]))
        values.append(case_values)
    axes[0].boxplot(values,tick_labels=[labels[m] for m in METHODS],showmeans=True)
    axes[0].set_ylabel('Cost reduction from shared initial plan (%)')
    axes[0].set_title('Each observation = one case, averaged over seeds')
    axes[0].tick_params(axis='x',rotation=15)
    paired=[p for p in comparisons(rows) if p['vs'] in METHODS and p['cases']]
    for i,p in enumerate(paired):
        lo,hi=p['ci95']
        axes[1].errorbar(p['mean_percent'],i,xerr=[[p['mean_percent']-lo],[hi-p['mean_percent']]],
                         fmt='o',capsize=4,color='#247c4f' if lo>0 else '#9c4141')
    axes[1].axvline(0,color='black',linewidth=1)
    axes[1].set_yticks(range(len(paired)),[labels[p['vs']] for p in paired])
    axes[1].set_xlabel('Hybrid cost reduction vs comparator (%)\nCase-bootstrap 95% interval; positive favours hybrid')
    axes[1].set_title('Paired comparisons; no universal-win claim')
    for ax in axes:
        ax.grid(axis='x',alpha=.2)
    fig.savefig(a.directory/'comparison.png',dpi=180)
    fig.savefig(a.directory/'comparison.svg')
    plt.close(fig)
    print(a.directory/'comparison.png')


if __name__=='__main__':
    main()
