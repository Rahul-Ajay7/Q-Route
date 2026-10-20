"""Print the structure of a JSON case so an adapter can be written.
usage: python experiments/inspect_json_case.py path/to/TC01.json
Paste the output back into the chat. Long lists are summarised, so it stays short."""
import json
import sys


def show(x, indent=0, key="(root)", max_items=3):
    pad = "  " * indent
    if isinstance(x, dict):
        print(f"{pad}{key}: object with {len(x)} keys")
        for k, v in list(x.items())[:40]:
            show(v, indent + 1, k, max_items)
    elif isinstance(x, list):
        kinds = sorted({type(v).__name__ for v in x})
        print(f"{pad}{key}: list of {len(x)} ({', '.join(kinds) or 'empty'})")
        for i, v in enumerate(x[:max_items]):
            show(v, indent + 1, f"[{i}]", max_items)
        if len(x) > max_items:
            print(f"{pad}  ... {len(x) - max_items} more")
    else:
        s = repr(x)
        print(f"{pad}{key}: {type(x).__name__} = {s[:60]}")


if len(sys.argv) < 2:
    sys.exit(__doc__)
show(json.load(open(sys.argv[1])))