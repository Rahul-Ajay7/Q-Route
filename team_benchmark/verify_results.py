"""Post-run source/input provenance, route audits, and tiny exact optimality gaps."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from .problem import ROOT, Problem
from .audit import audit
from .exact import exact_small
from .run import save
from .layout import resolve_recorded_path
from .provenance import verify_source


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('directory',type=Path)
    a=ap.parse_args()
    manifest=json.loads((a.directory/'manifest.json').read_text(encoding='utf-8'))
    runs=json.loads((a.directory/'runs.json').read_text(encoding='utf-8'))
    source_verification = {}
    for name,expected in manifest['source_sha256'].items():
        current=resolve_recorded_path(name)
        source_verification[name]=verify_source(a.directory,name,expected,current)
    problems={}
    for name,expected in manifest['input_sha256'].items():
        path=resolve_recorded_path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected, f'Input changed: {name}'
        try:
            problems[path.name]=Problem.load(path,manifest['window_policy']=='hard')
        except (ValueError,KeyError,TypeError):
            pass
    checked=0
    for r in runs:
        if not r['feasible']:
            assert r['cost'] is None
            continue
        p=problems[r['case']]
        physical=audit(p,r['routes'])
        assert math.isclose(physical['cost'],r['cost'],rel_tol=1e-10,abs_tol=1e-7)
        for k,v in r['metrics'].items():
            assert math.isclose(physical[k],v,rel_tol=1e-10,abs_tol=1e-7), k
        costs=[h['cost'] for h in r['history']]
        assert all(y<=x+1e-7 for x,y in zip(costs,costs[1:]))
        assert r['cost']<=r['initial_cost']+1e-7
        checked+=1
    exact=[]
    for name,p in problems.items():
        if len(p.ids)>7 or len(p.vehicles)>3:
            continue
        oracle=exact_small(p)
        rows=[r for r in runs if r['case']==name and r['feasible']]
        gaps=[100*(r['cost']-oracle['cost'])/max(oracle['cost'],1e-9) for r in rows]
        assert all(g>=-1e-7 for g in gaps)
        exact.append(dict(case=name,optimal_cost=oracle['cost'],proven_optimal=oracle['proven_optimal'],
                          proven_infeasible=oracle['proven_infeasible'],
                          run_gap_percent=[dict(method=r['method'],seed=r['seed'],gap_percent=g)
                                           for r,g in zip(rows,gaps)]))
    result=dict(feasible_runs_audited=checked,failed_runs=len(runs)-checked,
                declared_source_hashes_verified=True,input_hashes_verified=True,exact_small_cases=exact,
                current_source_matches_manifest=all(v=='current' for v in source_verification.values()),
                source_verification=source_verification)
    save(a.directory/'audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='exact_small_cases'}))


if __name__=='__main__':
    main()
