import sqlite3
import pandas as pd

con = sqlite3.connect("db/hr.db")
p = pd.read_sql("SELECT punch_id, device_id, device_user_id, punch_time FROM raw_punches", con)

print(p.head(10))
print("Null/empty punch_time:", (p["punch_time"].str.strip() == "").sum())
print("Punch time ki lambai (formats):", p["punch_time"].str.len().value_counts().to_dict())

p["ts"] = pd.to_datetime(p["punch_time"], errors="coerce")
print("Parse fail:", p["ts"].isna().sum())
print("Date range:", p["ts"].min(), "to", p["ts"].max())
print("Duplicate punch_id:", p["punch_id"].duplicated().sum())

dm = pd.read_sql("SELECT device_id, device_user_id, emp_id FROM stg_device_mapping", con)
m = p.merge(dm, on=["device_id", "device_user_id"], how="left")
print("Unmapped punches:", m["emp_id"].isna().sum())

p["hour"] = p["ts"].dt.hour + p["ts"].dt.minute / 60
print(p.groupby("device_id").agg(punches=("punch_id", "count"), avg_hour=("hour", "mean")).round(2))
con.close()