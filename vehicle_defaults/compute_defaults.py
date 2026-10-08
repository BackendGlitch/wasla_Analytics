#!/usr/bin/env python3
"""Compute each vehicle's default destination (the one it queues to most)
from historical trips data on the Jemmal server, and export to Excel."""

import pandas as pd
from sqlalchemy import create_engine

DB_URL = "postgresql://wasla:Lost2409@localhost:15432/wasla_db"
OUT = "vehicle_default_destinations.xlsx"

# Normalize destination names: Tunis appears under several IDs
DEST_ALIASES = {
    "تونس": "تونس",
    "Tunis": "تونس",
}
# Arabic dir display order
DESTS = ["سوسة", "تونس", "سواسي", "المنستير", "قصر هلال", "طبلبة"]

engine = create_engine(DB_URL)

vehicles = pd.read_sql(
    "SELECT id, license_plate, capacity, phone_number, is_active, is_available, is_banned, "
    "base_price, created_at FROM vehicles ORDER BY license_plate", engine)

trips = pd.read_sql(
    "SELECT id, vehicle_id, license_plate, destination_id, destination_name, start_time "
    "FROM trips WHERE vehicle_id IS NOT NULL AND vehicle_id <> ''", engine)

engine.dispose()

trips["dest"] = trips["destination_name"].map(lambda n: DEST_ALIASES.get(str(n).strip(), str(n).strip()))
trips["start_date"] = pd.to_datetime(trips["start_time"]).dt.date

# aggregate per vehicle
agg = (trips.groupby(["vehicle_id", "dest"])
       .agg(trips_count=("id", "count"),
            last_trip=("start_date", "max"))
       .reset_index())

# total trips per vehicle + recent (last 30 days) weight
trips["recent"] = pd.to_datetime(trips["start_time"]) >= (pd.Timestamp.now() - pd.Timedelta(days=30))
recent = trips.groupby("vehicle_id")["recent"].sum().rename("recent_trips").reset_index()

ranked = (agg.sort_values(["vehicle_id", "trips_count", "last_trip"], ascending=[True, False, False])
          .groupby("vehicle_id").cumcount().rename("rank").to_frame().join(agg.sort_values(
              ["vehicle_id", "trips_count", "last_trip"], ascending=[True, False, False]))
          .reset_index(drop=True))

top = ranked[ranked["rank"] == 0].rename(columns={"dest": "default_destination"})
second = ranked[ranked["rank"] == 1][["vehicle_id", "dest", "trips_count"]].rename(
    columns={"dest": "second_destination", "trips_count": "second_trips"})

df = (vehicles.merge(top[["vehicle_id", "default_destination", "trips_count", "last_trip"]],
                     left_on="id", right_on="vehicle_id", how="left")
      .merge(recent, left_on="id", right_on="vehicle_id", how="left")
      .merge(second, left_on="id", right_on="vehicle_id", how="left")
      .drop(columns=["vehicle_id"]))
df["no_history"] = df["trips_count"].isna()

# confidence: share of trips to the top destination
tot = agg.groupby("vehicle_id")["trips_count"].sum().rename("total_trips").reset_index()
df = df.merge(tot, left_on="id", right_on="vehicle_id", how="left").drop(columns=["vehicle_id"])
df["share_pct"] = (df["trips_count"] / df["total_trips"] * 100).round(1)

# recent-only default (last 30 days) for freshness signal
recent_trips = trips[trips["recent"]]
if not recent_trips.empty:
    recent_agg = (recent_trips.groupby(["vehicle_id", "dest"]).size().rename("n").reset_index())
    recent_top = (recent_agg.sort_values(["vehicle_id", "n"], ascending=[True, False])
                  .groupby("vehicle_id").head(1)[["vehicle_id", "dest", "n"]]
                  .rename(columns={"dest": "recent_default", "n": "recent_default_trips"}))
    df = df.merge(recent_top, left_on="id", right_on="vehicle_id", how="left").drop(columns=["vehicle_id"])
else:
    df["recent_default"] = None
    df["recent_default_trips"] = 0

df["last_trip"] = pd.to_datetime(df["last_trip"]).dt.strftime("%Y-%m-%d")
df["recent_default_match"] = df["default_destination"] == df["recent_default"]
df["recent_default_match"] = df["recent_default_match"].fillna(False).replace({True: "yes", False: "no"})

cols = [
    "license_plate", "capacity", "phone_number", "is_active", "is_available", "is_banned",
    "default_destination", "trips_count", "share_pct", "total_trips", "recent_trips",
    "recent_default", "recent_default_match", "last_trip", "second_destination", "second_trips",
    "no_history",
]
df = df[cols].sort_values(["no_history", "default_destination", "trips_count"],
                          ascending=[True, True, False]).reset_index(drop=True)

# human-readable status
def status(r):
    if r["no_history"]:
        return "NO HISTORY (no trips found)"
    if r["recent_default_match"] == "yes":
        return "STABLE (default = last-30d)"
    return "DEFAULT vs recent differ"
df["status"] = df.apply(status, axis=1)

with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    df.to_excel(w, sheet_name="vehicles", index=False)
    summary = (df.groupby("default_destination", dropna=False)
                 .agg(vehicles=("license_plate", "count"),
                      with_history=("no_history", lambda s: (~s).sum()))
                 .reset_index().sort_values("vehicles", ascending=False))
    summary.to_excel(w, sheet_name="dest_summary", index=False)

print(f"vehicles: {len(df)} | with history: {int(df['no_history'].eq(False).sum())} | no history: {int(df['no_history'].sum())}")
print("saved:", OUT)
print(df[["license_plate", "default_destination", "trips_count", "share_pct", "status"]].head(20).to_string(index=False))