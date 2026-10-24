import sqlite3
import pandas as pd

pd.set_option("display.width", 200)
con = sqlite3.connect("db/hr.db")
p = pd.read_sql(
    "SELECT device_id, punch_ts_original FROM stg_punches "
    "WHERE device_id IN ('DEV-SITE-01', 'DEV-KOR-01', 'DEV-FSD-01')", con)
p["ts"] = pd.to_datetime(p["punch_ts_original"])
p["date"] = p["ts"].dt.normalize()
p["mins"] = p["ts"].dt.hour * 60 + p["ts"].dt.minute
w = p[(p["mins"] >= 240) & (p["mins"] < 510)]

g = w.groupby(["date", "device_id"])["mins"].agg(["median", "size"]).reset_index()
med = g.pivot(index="date", columns="device_id", values="median")
cnt = g.pivot(index="date", columns="device_id", values="size")
ref = med[["DEV-KOR-01", "DEV-FSD-01"]].mean(axis=1)
diff = med["DEV-SITE-01"] - ref
ok = (cnt >= 20).all(axis=1)
diff = diff[ok]

print("Weekly farq (SITE minus KOR/FSD), minutes mein:")
print(diff.resample("W").mean().round(0))

flag = diff[diff > 30]
print("Flagged days:", len(flag), "of", len(diff))
print("Pehla flagged din:", flag.index.min().date())
print("Aakhri flagged din:", flag.index.max().date())
first = flag.index.min()
print(diff[first - pd.Timedelta(days=5): first + pd.Timedelta(days=5)].round(0))
con.close()