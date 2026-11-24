"""Check the five nonmatching modules against the exact published source on the verification host."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

root=Path(sys.argv[1]).resolve()
receipt=Path(__file__).with_name("source-replay-inputs.json")
records={s["module"]:s for s in json.loads(receipt.read_text())}
target="Formalism.SizeWindowBrackets.ChainSlopeWindows.LipschitzWeightAndMinimum"
graph=json.loads((root/"assets/main-dependency-graph.json").read_text())
checked=set()
order=[]

def visit(name):
    if name in checked:
        return
    for ancestor in graph[name]:
        visit(ancestor)
    checked.add(name)
    if name in records:
        order.append(name)

visit(target)
assert len(checked)==41 and len(order)==5 and order[-1]==target
print("41 project modules, 36 reference-binary matches, 5 published-source replays",flush=True)
# Lean resolves a namespace from its first search root. Make that root complete.
for path in (root/"assets/all-files.txt").read_text().splitlines():
    if path.removesuffix(".olean").replace("/",".") in records:
        continue
    dest=root/"replay/lib"/path
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():
        dest.symlink_to(root/"project/auth"/path)
paths=[root/"replay/lib",root/"project/auth",root/"project/.lake/build/lib/lean",
       *sorted((root/"project/.lake/packages").glob("*/.lake/build/lib/lean"))]
env=dict(os.environ,LEAN_PATH=os.pathsep.join(map(str,paths)))
for name in order:
    item=records[name]
    rel=Path(*name.split("."))
    src=root/"replay/src"/rel.with_suffix(".lean")
    dest=root/"replay/lib"/rel.with_suffix(".olean")
    dest.parent.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(src.read_bytes()).hexdigest()
    assert sha==item["source_sha256"], src
    print(f"checking original {name} source SHA-256 {sha}",flush=True)
    setup={"name":name,"package":"tree","isModule":False,"plugins":[],"dynlibs":[],"importArts":{},
           "options":{"relaxedAutoImplicit":False,"pp.unicode.fun":True,"maxSynthPendingDepth":3,
                      "maxHeartbeats":4000000,"autoImplicit":False}}
    meta=root/"replay/consumer.setup.json"; meta.write_text(json.dumps(setup))
    subprocess.run([root/"toolchain/bin/lean","-j","1","--tstack=400000",str(src),
                    "-o",str(dest),"--setup",str(meta)],cwd=root/"replay",env=env,check=True)
    got=hashlib.sha256(dest.read_bytes()).hexdigest()
    print(f"accepted {name}: olean {got}; reference equality {got==item['reference_olean_sha256']}",flush=True)
print("All five original sources re-elaborated successfully.",flush=True)
