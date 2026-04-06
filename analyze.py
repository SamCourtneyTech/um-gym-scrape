#!/usr/bin/env python3
"""Show gym busyness: current, historical averages, and next-few-hours prediction."""

import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).parent / "gym.db"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

MIN_SAMPLES = 3  # need at least this many readings to show a band


def slot_label(hour, half):
    minute = "00" if half == 0 else "30"
    return f"{hour:02d}:{minute}"


def get_band(conn, weekday, hour, half_hour, space):
    rows = conn.execute(
        """
        SELECT percentage FROM readings
        WHERE weekday=? AND hour=? AND half_hour=? AND space=?
        ORDER BY ts DESC LIMIT 60
        """,
        (weekday, hour, half_hour, space),
    ).fetchall()
    if len(rows) < MIN_SAMPLES:
        return None
    vals = [r[0] for r in rows]
    avg = sum(vals) / len(vals)
    lo = min(vals)
    hi = max(vals)
    return lo, round(avg), hi, len(vals)


def latest_reading(conn, space):
    row = conn.execute(
        "SELECT ts, percentage FROM readings WHERE space=? ORDER BY ts DESC LIMIT 1",
        (space,),
    ).fetchone()
    return row


def spaces(conn):
    return [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT space FROM readings ORDER BY space"
        ).fetchall()
    ]


def main():
    if not DB.exists():
        print("No data yet. Run collect.py first (or wait for cron to kick in).")
        return

    conn = sqlite3.connect(DB)
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    half = now.minute // 30

    for space in spaces(conn):
        print(f"\n=== {space} ===")

        latest = latest_reading(conn, space)
        if latest:
            ts_str, pct = latest
            ts = datetime.fromisoformat(ts_str)
            age = round((now - ts).total_seconds() / 60)
            print(f"Right now:  {pct}%  (reading {age} min ago)")
        else:
            print("Right now:  no data")

        band = get_band(conn, weekday, hour, half, space)
        slot = f"{DAYS[weekday]} {slot_label(hour, half)}"
        if band:
            lo, avg, hi, n = band
            print(f"Usual at {slot}:  {lo}–{hi}%  (avg {avg}%, n={n})")
        else:
            print(f"Usual at {slot}:  not enough data yet")

        # next 4 half-hour slots
        print("\nPredicted next 2 hours:")
        h, m = hour, half
        for _ in range(4):
            m += 1
            if m == 2:
                m = 0
                h = (h + 1) % 24
            b = get_band(conn, weekday, h, m, space)
            label = slot_label(h, m)
            if b:
                lo, avg, hi, n = b
                print(f"  {DAYS[weekday]} {label}:  {lo}–{hi}%  (avg {avg}%)")
            else:
                print(f"  {DAYS[weekday]} {label}:  no data yet")

    conn.close()


if __name__ == "__main__":
    main()
