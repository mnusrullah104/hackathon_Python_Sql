import subprocess
import sys
from pathlib import Path

STEPS = [
    "transform/stage2a_core.py",
    "transform/stage2b_punches.py",
    "transform/stage2c_rest.py",
    "transform/stage3_attendance.py",
    "warehouse/build_warehouse.py",
    "analytics/run_queries.py",
    "quality/run_dq_checks.py",
]


if "--fresh" in sys.argv:
    db = Path("db/hr.db")
    if db.exists():
        db.unlink()
    STEPS.insert(0, "ingestion/load_raw.py")

for step in STEPS:
    print("=" * 60)
    print("RUNNING:", step)
    result = subprocess.run([sys.executable, step])
    if result.returncode != 0:
        print("FAILED:", step)
        sys.exit(1)

print("Pipeline complete")