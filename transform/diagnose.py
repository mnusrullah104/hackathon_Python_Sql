import sqlite3
import json
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 50)

con = sqlite3.connect("db/hr.db")

print("=== SHIFTS ===")
for (payload,) in con.execute("SELECT payload FROM raw_shifts"):
    print(json.loads(payload))

print("\n=== HISTORY BAD ROW ===")
bad = pd.read_sql(
    "SELECT emp_id FROM stg_employment_history "
    "WHERE valid_to IS NOT NULL AND valid_to < valid_from", con)
for emp in bad["emp_id"]:
    print(pd.read_sql(
        "SELECT * FROM stg_employment_history WHERE emp_id = ? ORDER BY valid_from",
        con, params=(emp,)))

print("\n=== PUNCH COUNT BY HOUR AND DEVICE ===")
p = pd.read_sql("SELECT device_id, punch_time FROM raw_punches", con)
p["hour"] = pd.to_datetime(p["punch_time"]).dt.hour
print(pd.crosstab(p["hour"], p["device_id"]))
con.close()