"""Compile a list of local modules using a pinned Lean installation and prebuilt Mathlib."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

base = Path(__file__).resolve().parent
repository = base.parents[2]
shared = repository / ".scratch/rh_20261120/source_build"
compiler = Path(os.environ.get("HANDOFF_LEAN", shared / "toolchain/bin/lean"))
packages = Path(os.environ.get("HANDOFF_PACKAGES", shared / "lean/.lake/packages"))
project_lib = os.environ.get("HANDOFF_PROJECT_LIB", str(shared / "lean/.lake/build/lib/lean"))
modules = sys.argv[1:] or ["Handoff", "RankSubstitute", "Transfer", "BindingCheck"]
with tempfile.TemporaryDirectory(prefix=".check-", dir=base) as stage:
    deps = [stage, *project_lib.split(os.pathsep), *(str(p) for p in sorted(packages.glob("*/.lake/build/lib/lean")))]
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(deps))
    subprocess.run([compiler, "--version"], check=True, env=env)
    for mod in modules:
        print(f"checking {mod}.lean", flush=True)
        subprocess.run([compiler, "-j", "1", "-o", Path(stage)/(mod+".olean"), base/(mod+".lean")],
                       env=env, cwd=base, check=True)
    print("All requested local modules accepted.", flush=True)
