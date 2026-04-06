#!/usr/bin/env python3
"""Generate busyness charts from gym.db and save as PNGs."""

import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DB = Path(__file__).parent / "gym.db"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

ACCENT = "#00BFFF"
BAND   = "#00BFFF"
BG     = "#0d1117"
GRID   = "#21262d"
TEXT   = "#e6edf3"


def style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v)}%"))
    ax.set_ylim(0, 100)
    ax.grid(True, color=GRID, linewidth=0.6)


def plot_today(conn, ax):
    today = date.today()
    weekday = today.weekday()

    # Today's actual readings
    rows = conn.execute(
        "SELECT ts, percentage FROM readings WHERE date(ts)=? ORDER BY ts",
        (today.isoformat(),),
    ).fetchall()

    # Historical average for this weekday, bucketed by half-hour
    hist = conn.execute(
        """
        SELECT hour, half_hour, AVG(percentage), MIN(percentage), MAX(percentage)
        FROM readings
        WHERE weekday=? AND date(ts) != ?
        GROUP BY hour, half_hour
        ORDER BY hour, half_hour
        """,
        (weekday, today.isoformat()),
    ).fetchall()

    # Historical band
    if hist:
        hx = [datetime.combine(today, __import__('datetime').time(r[0], r[1] * 30)) for r in hist]
        havg = [r[2] for r in hist]
        hlo  = [r[3] for r in hist]
        hhi  = [r[4] for r in hist]
        ax.fill_between(hx, hlo, hhi, color=BAND, alpha=0.15, label=f"Typical {DAYS[weekday]}")
        ax.plot(hx, havg, color=BAND, linewidth=1, linestyle="--", alpha=0.5)

    # Today's line
    if rows:
        tx = [datetime.fromisoformat(r[0]) for r in rows]
        ty = [r[1] for r in rows]
        ax.plot(tx, ty, color=ACCENT, linewidth=2, label="Today")
        ax.scatter(tx, ty, color=ACCENT, s=18, zorder=5)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-I%p"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_title(f"{DAYS[weekday]} — Fitness Room", fontsize=11, pad=8)
    ax.set_xlabel("Time", labelpad=6)
    ax.set_ylabel("Occupancy", labelpad=6)
    if hist or rows:
        ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=8)


def plot_monthly(conn, ax):
    rows = conn.execute(
        """
        SELECT strftime('%m', ts) as month, AVG(percentage), MIN(percentage), MAX(percentage)
        FROM readings
        GROUP BY month
        ORDER BY month
        """,
    ).fetchall()

    xs    = [int(r[0]) - 1 for r in rows]   # 0-indexed month
    avgs  = [r[1] for r in rows]
    los   = [r[2] for r in rows]
    his   = [r[3] for r in rows]

    if rows:
        ax.bar(xs, avgs, color=ACCENT, alpha=0.7, width=0.6, zorder=3)
        ax.errorbar(xs, avgs,
                    yerr=[
                        [a - l for a, l in zip(avgs, los)],
                        [h - a for h, a in zip(his, avgs)],
                    ],
                    fmt="none", color=TEXT, capsize=4, linewidth=1, zorder=4)

    ax.set_xticks(range(12))
    ax.set_xticklabels(MONTHS)
    ax.set_title("Monthly Average Occupancy", fontsize=11, pad=8)
    ax.set_xlabel("Month", labelpad=6)
    ax.set_ylabel("Avg Occupancy", labelpad=6)


def main():
    if not DB.exists():
        return

    conn = sqlite3.connect(DB)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 8),
        facecolor=BG,
        gridspec_kw={"hspace": 0.55},
    )

    plot_today(conn, ax1)
    plot_monthly(conn, ax2)
    style_ax(ax1)
    style_ax(ax2)

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    fig.text(0.99, 0.01, f"Updated {now_str}", ha="right", fontsize=7,
             color="#8b949e")

    out = Path(__file__).parent / "charts.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    conn.close()
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
