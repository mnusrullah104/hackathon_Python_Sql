import sqlite3
con = sqlite3.connect("db/hr.db")
tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
for t in tables:
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t} ({n} rows): {', '.join(cols)}")
con.close()