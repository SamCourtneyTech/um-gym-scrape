#!/usr/bin/env python3
"""Generate busyness charts from gym.db and save as PNG."""

import sqlite3
import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

DB   = Path(__file__).parent / "gym.db"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

ACCENT = "#00BFFF"
BAND   = "#00BFFF"
BG     = "#0d1117"
GRID   = "#21262d"
TEXT   = "#e6edf3"
DIM    = "#8b949e"

OPEN_HOUR  = 6
CLOSE_HOUR = 24  # midnight

# Reference date just for x-axis time formatting
_REF = datetime.date(2000, 1, 1)


def style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT, labelsize=7.5)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v)}%"))
    ax.set_ylim(0, 100)
    ax.set_xlim(
        datetime.datetime.combine(_REF, datetime.time(OPEN_HOUR, 0)),
        datetime.datetime.combine(_REF, datetime.time(CLOSE_HOUR % 24, 0))
        if CLOSE_HOUR < 24
        else datetime.datetime.combine(_REF + datetime.timedelta(days=1), datetime.time(0, 0)),
    )
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-I%p"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)


def plot_day(conn, ax, weekday):
    rows = conn.execute(
        """
        SELECT
            hour,
            CAST(strftime('%M', ts) AS INTEGER) / 5 AS bucket,
            AVG(percentage),
            MIN(percentage),
            MAX(percentage),
            COUNT(*) as n
        FROM readings
        WHERE weekday = ? AND hour >= ? AND hour < ?
        GROUP BY hour, bucket
        ORDER BY hour, bucket
        """,
        (weekday, OPEN_HOUR, CLOSE_HOUR),
    ).fetchall()

    if rows:
        xs  = [datetime.datetime.combine(_REF, datetime.time(r[0], r[1] * 5)) for r in rows]
        avg = [r[2] for r in rows]
        lo  = [r[3] for r in rows]
        hi  = [r[4] for r in rows]
        ax.fill_between(xs, lo, hi, color=BAND, alpha=0.15)
        ax.plot(xs, avg, color=ACCENT, linewidth=1.5)
    else:
        ax.text(0.5, 0.5, "No data yet", transform=ax.transAxes,
                ha="center", va="center", color=DIM, fontsize=8)

    ax.set_title(DAYS[weekday], color=TEXT, fontsize=9, pad=5)


def main():
    if not DB.exists():
        return

    conn = sqlite3.connect(DB)

    fig, axes = plt.subplots(
        4, 2,
        figsize=(12, 14),
        facecolor=BG,
        gridspec_kw={"hspace": 0.65, "wspace": 0.25},
    )
    axs = axes.flatten()

    for weekday in range(7):
        style_ax(axs[weekday])
        plot_day(conn, axs[weekday], weekday)

    # Hide the unused 8th panel
    axs[7].set_visible(False)

    fig.suptitle("Herbert Wellness Center — Average Busyness by Day",
                 color=TEXT, fontsize=12, y=0.995)

    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    fig.text(0.99, 0.001, f"Updated {now_str}", ha="right", fontsize=7, color=DIM)

    out = Path(__file__).parent / "charts.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    conn.close()
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
