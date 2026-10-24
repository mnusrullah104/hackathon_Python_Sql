import sqlite3
from pathlib import Path
import pandas as pd

con = sqlite3.connect("db/hr.db")
out = Path("analytics/results")
out.mkdir(parents=True, exist_ok=True)

for f in sorted(Path("analytics").glob("q*.sql")):
    df = pd.read_sql(f.read_text(encoding="utf-8"), con)
    df.to_csv(out / (f.stem + ".csv"), index=False)
    print(f.name, "rows:", len(df))
    print(df.head(5).to_string(index=False))
    print()
con.close()