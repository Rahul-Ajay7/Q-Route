"""Download real Solomon instances into data/solomon/.

usage: python scripts/fetch_solomon.py R101 C101 RC101 R102 ...
Source: GitHub mirror of Solomon's original text files (iRB-Lab/py-ga-VRPTW).
Fallback: https://www.sintef.no/projectweb/top/vrptw/100-customers/
"""
import os
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/iRB-Lab/py-ga-VRPTW/master/data/text/{n}.txt"
names = sys.argv[1:] or ["R101", "C101", "RC101"]
os.makedirs("data/solomon", exist_ok=True)
for name in names:
    dest = f"data/solomon/{name}.txt"
    try:
        data = urllib.request.urlopen(URL.format(n=name), timeout=20).read()
        if b"CUSTOMER" not in data.upper():
            raise ValueError("unexpected content")
        open(dest, "wb").write(data)
        print("ok  ", dest)
    except Exception as e:
        print("fail", name, "-", type(e).__name__, e)