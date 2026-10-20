"""Convert the supplied Solomon text files into the shared JSON schema.

No network/download. Units: one coordinate unit = synthetic km, one time unit
= minute; travel minutes = Euclidean distance. Traffic variants are synthetic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from .problem import ROOT


def convert(path, traffic=False):
    vehicle = None
    customers = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            values = [float(v) for v in re.split(r"[\s,;]+", line.strip()) if v]
        except ValueError:
            continue
        if len(values) == 2 and vehicle is None and not customers:
            vehicle = values
        elif len(values) == 7:
            i,x,y,d,r,due,s = values
            customers.append(dict(id=int(i),x=x,y=y,demand=d,ready_time=r,due_time=due,service_time=s))
    if vehicle is None or len(customers) < 2 or customers[0]["id"] != 0:
        raise ValueError(f"Not a Solomon instance: {path}")
    xy = np.array([[c["x"],c["y"]] for c in customers])
    matrix = np.linalg.norm(xy[:,None]-xy[None,:],axis=2)
    result = dict(id=path.stem+("_traffic" if traffic else "_freeflow"),
                  depot=customers[0],customers=customers[1:],
                  vehicles=[dict(id=f"V{i+1}",capacity=vehicle[1],start_depot=0,end_depot=0)
                            for i in range(int(vehicle[0]))],
                  base_travel_time_matrix=matrix.tolist(),
                  units=dict(distance="synthetic_km",time="minutes",demand="units"),
                  source=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              traffic="synthetic corridor" if traffic else "none"))
    if traffic:
        threshold = float(np.median(xy[:,0]))
        result["traffic_events"] = [dict(time=100,end_time=400,**{"from":a["id"],"to":b["id"]},multiplier=2)
                                    for a in customers for b in customers
                                    if a["id"] != b["id"] and a["x"] <= threshold < b["x"]]
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,default=ROOT/"members/Parikshit/data/solomon")
    ap.add_argument("--output",type=Path,default=ROOT/"data/comparison/solomon")
    a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    for path in sorted(a.source.glob("*.txt")):
        for traffic in (False,True):
            d=convert(path,traffic)
            target=a.output/(d["id"]+".json")
            if target.resolve()==path.resolve():
                raise ValueError("Cannot overwrite source")
            target.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
            print(target)


if __name__ == "__main__":
    main()
