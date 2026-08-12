"""Phase 3 - Step 1: Prepare daily time series for forecasting.

Builds a continuous daily series (datelng → value, no missing days) of
booking VOLUME per station (and total). Ghost bookings are included for
volume — flow exists even for drafts (see Phase_2 conclusion).

Outputs output/series_{jemmal,monastir,total}.parquet + a JSON descriptor.
"""

import json
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FEAT, OUT, STATIONS


def build_series() -> dict:
    be = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    be["date"] = pd.to_datetime(be["created_at"]).dt.normalize()

    descriptor = {}
    for key, mask in (
        *[(st, be["station"].eq(st)) for st in STATIONS],
        ("total", pd.Series(True, index=be.index)),
    ):
        sub = be[mask]
        daily = sub.groupby("date")["id"].count()
        # reindex to continuous calendar days (fill missing with 0)
        idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
        s = daily.reindex(idx).fillna(0).astype(int)
        # Drop a trailing PARTIAL day: at extraction time the current calendar
        # day is incomplete (e.g. 16 bookings vs ~3,600 normal). Detect as last
        # value far below the preceding week's level.
        if len(s) >= 8:
            prev_week = s.iloc[-8:-1].mean()
            if s.iloc[-1] < 0.25 * prev_week:
                dropped = (str(s.index[-1].date()), int(s.iloc[-1]))
                s = s.iloc[:-1]
                print(f"  [drop partial day] {key}: {dropped[0]} had only {dropped[1]} bookings "
                      f"(<25% of prev week {prev_week:.0f})")
        s.name = "bookings"
        df = s.to_frame().reset_index(names="date")
        df.to_parquet(OUT / f"series_{key}.parquet", index=False)
        descriptor[key] = {
            "start": str(s.index.min().date()),
            "end": str(s.index.max().date()),
            "n_days": int(len(s)),
            "n_days_with_data": int((s > 0).sum()),
            "total": int(s.sum()),
            "mean": float(s.mean()),
            "std": float(s.std()),
            "max_day": str(s.idxmax().date()),
        }
        print(f"  {key:<10} days={len(s):>3}  with_data={(s>0).sum():>3}  total={s.sum():>10,}  mean={s.mean():7,.0f}")

    with open(OUT / "series_descriptor.json", "w") as f:
        json.dump(descriptor, f, indent=2)
    return descriptor


if __name__ == "__main__":
    print("Building daily series ...")
    build_series()
    print("-> output/series_{jemmal,monastir,total}.parquet")
