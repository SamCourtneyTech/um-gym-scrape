#!/usr/bin/env python3
"""Poll the Herbert Wellness Center busyness every ~3 min via cron."""

import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).parent / "gym.db"
API_URL = "https://jjyczft24vcqfkzngwy5xkl2gi.appsync-api.us-west-2.amazonaws.com/graphql"
API_KEY = "da2-mrm36auugfbptnau2b3mib4lzi"
SITE_URI = "jht42tw9feut"

QUERY = """
query GetSign($uri: String!) {
  GetSign(uri: $uri) {
    spaces {
      displayName
      percentage
      capacity
      noCounts
    }
  }
}
"""


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id          INTEGER PRIMARY KEY,
            ts          TEXT NOT NULL,
            weekday     INTEGER NOT NULL,
            hour        INTEGER NOT NULL,
            half_hour   INTEGER NOT NULL,
            percentage  INTEGER,
            capacity    INTEGER,
            space       TEXT
        )
    """)
    conn.commit()


def fetch():
    payload = json.dumps({"query": QUERY, "variables": {"uri": SITE_URI}}).encode()
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


OPEN_HOUR  = 6   # 6am
CLOSE_HOUR = 24  # midnight


def main():
    now = datetime.now()
    if not (OPEN_HOUR <= now.hour < CLOSE_HOUR):
        print(f"Gym closed at {now:%H:%M}, skipping.")
        return

    conn = sqlite3.connect(DB)
    init_db(conn)

    data = fetch()
    spaces = data["data"]["GetSign"]["spaces"]

    for space in spaces:
        if space["noCounts"]:
            continue
        conn.execute(
            "INSERT INTO readings (ts, weekday, hour, half_hour, percentage, capacity, space) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                now.isoformat(),
                now.weekday(),       # 0=Mon … 6=Sun
                now.hour,
                now.minute // 30,    # 0 = :00–:29, 1 = :30–:59
                space["percentage"],
                space["capacity"],
                space["displayName"],
            ),
        )
        print(f"{now:%Y-%m-%d %H:%M}  {space['displayName']}: {space['percentage']}%")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
