import sqlite3
import pandas as pd

FAULTY_DEVICE = "DEV-SITE-01"
OFFSET_HOURS = 1
FAULTY_FROM = "2026-07-01"
FAULTY_TO = None
con = sqlite3.connect("db/hr.db")

p = pd.read_sql(
    "SELECT punch_id, device_id, device_user_id, punch_time FROM raw_punches", con)
raw_count = len(p)
for c in ["punch_id", "device_id", "device_user_id", "punch_time"]:
    p[c] = p[c].str.strip()
p["ts_original"] = pd.to_datetime(p["punch_time"], errors="coerce")

dm = pd.read_sql(
    "SELECT device_id, device_user_id, emp_id FROM stg_device_mapping", con)
print("Mapping mein duplicate keys:", dm.duplicated(["device_id", "device_user_id"]).sum())
dm = dm.drop_duplicates(["device_id", "device_user_id"])

p = p.merge(dm, on=["device_id", "device_user_id"], how="left")
p["ts"] = p["ts_original"]
if FAULTY_DEVICE:
    mask = p["device_id"] == FAULTY_DEVICE
    if FAULTY_FROM:
        mask = mask & (p["ts_original"] >= pd.Timestamp(FAULTY_FROM))
    if FAULTY_TO:
        mask = mask & (p["ts_original"] < pd.Timestamp(FAULTY_TO) + pd.Timedelta(days=1))
    p.loc[mask, "ts"] = p.loc[mask, "ts_original"] - pd.Timedelta(hours=OFFSET_HOURS)
    print("Clock fix lagaya:", FAULTY_DEVICE, "from", FAULTY_FROM, "to", FAULTY_TO,
          "punches:", int(mask.sum()))

unmapped = p[p["emp_id"].isna()].copy()
unmapped["reason"] = "no device mapping (contractor or visitor)"
mapped = p[p["emp_id"].notna()].copy()

mapped = mapped.sort_values(["emp_id", "ts", "punch_id"])
gap = mapped.groupby("emp_id")["ts"].diff().dt.total_seconds()
is_dup = gap <= 120
dups = mapped[is_dup].copy()
dups["reason"] = "duplicate punch within 2 minutes"
clean = mapped[~is_dup].copy()

fmt = "%Y-%m-%d %H:%M:%S"
clean_out = pd.DataFrame({
    "punch_id": clean["punch_id"],
    "emp_id": clean["emp_id"],
    "device_id": clean["device_id"],
    "punch_ts": clean["ts"].dt.strftime(fmt),
    "punch_ts_original": clean["ts_original"].dt.strftime(fmt),
})
clean_out.to_sql("stg_punches", con, if_exists="replace", index=False)

rej = pd.concat([unmapped, dups])
rej_out = pd.DataFrame({
    "punch_id": rej["punch_id"],
    "device_id": rej["device_id"],
    "device_user_id": rej["device_user_id"],
    "punch_time": rej["punch_time"],
    "reason": rej["reason"],
})
rej_out.to_sql("stg_rejected_punches", con, if_exists="replace", index=False)

print("Raw punches:", raw_count)
print("Clean (stg_punches):", len(clean_out))
print("Rejected:", len(rej_out))
print(rej_out["reason"].value_counts())
print("Reconciliation OK:", raw_count == len(clean_out) + len(rej_out))
con.close()