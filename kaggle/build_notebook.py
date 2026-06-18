#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera il Kaggle Notebook (.ipynb) standalone a partire dalla stessa analisi
della pipeline locale, ma autosufficiente (scarica i dati via yfinance).

Uso:  .venv/bin/python kaggle/build_notebook.py
Output: kaggle/notebook/sp500-long-term-analysis.ipynb
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "notebook" / "sp500-long-term-analysis.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": list(lines)}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src.strip("\n").splitlines(keepends=True)}


cells = []

cells.append(md(
    "# S&P 500 — Long-Term Analysis & Portfolio Recommendations\n",
    "\n",
    "**Author:** Lorenzo Di Giacomo · Data Analyst\n",
    "\n",
    "An investment-research style analysis of the S&P 500: what it is, how it has\n",
    "behaved across nearly a century, and what evidence-based conclusions we can draw\n",
    "for long-term portfolio decisions.\n",
    "\n",
    "The notebook is **fully reproducible and self-updating**: it pulls live data from\n",
    "Yahoo Finance every time it runs. Companion repo with an auto-updating presentation:\n",
    "see the GitHub link on my profile.\n",
))

cells.append(md("## 1. Setup & data\n",
                "We use the price index `^GSPC` (history since 1927), the total-return\n",
                "index `^SP500TR` (dividends reinvested, since 1988), and representative ETFs\n",
                "for an asset-class comparison (`SPY`, `AGG`, `GLD`, `BIL`)."))

cells.append(code(r'''
import sys, subprocess, warnings
warnings.filterwarnings("ignore")
try:
    import yfinance as yf
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yfinance"])
    import yfinance as yf

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# --- minimalist "Ink & Gold" style ---
INK, MUTED, GOLD = "#1f2328", "#8a8f98", "#b6892b"
GAIN, LOSS, GRID, PAPER = "#2f7d5b", "#b0413e", "#e7e3da", "#faf8f3"
plt.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "font.size": 12, "axes.edgecolor": MUTED, "axes.linewidth": 0.8,
    "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "figure.figsize": (10, 4.6),
})

def clean(ax):
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0); ax.grid(axis="y", color=GRID, lw=0.9); ax.set_axisbelow(True)

def load(ticker):
    df = yf.download(ticker, period="max", interval="1d",
                     progress=False, auto_adjust=True, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].dropna()

price = load("^GSPC")
tr    = load("^SP500TR")
assets = {"Equity (S&P 500)": load("SPY"), "Bonds": load("AGG"),
          "Gold": load("GLD"), "Cash": load("BIL")}
print(f"S&P 500 price: {len(price)} obs, {price.index.min().date()} -> {price.index.max().date()}")
''' ))

cells.append(md("## 2. The long-term picture\n",
                "Plotted on a **log scale**, equal vertical distances mean equal *percentage*\n",
                "moves — the natural way to read decades of compounding."))

cells.append(code(r'''
s = price.asfreq("B").ffill()
first, last = float(s.iloc[0]), float(s.iloc[-1])
years = (s.index[-1] - s.index[0]).days / 365.25
cagr = (last/first)**(1/years) - 1
vol  = s.pct_change().std() * np.sqrt(252)
dd   = (s / s.cummax() - 1.0)
print(f"From {s.index[0].date()} to {s.index[-1].date()}  ({years:.0f} years)")
print(f"$100 -> ${100*last/first:,.0f}   |   CAGR (price): {cagr*100:.1f}%")
print(f"Annualised volatility: {vol*100:.1f}%   |   Max drawdown: {dd.min()*100:.1f}% ({dd.idxmin().year})")

w = s.resample("W").last()
fig, ax = plt.subplots()
ax.plot(w.index, w.values, color=INK, lw=1.3)
ax.fill_between(w.index, w.values, w.min(), color=GOLD, alpha=0.06)
ax.set_yscale("log")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{int(v):,}"))
clean(ax); ax.spines["bottom"].set_color(MUTED)
ax.set_title("S&P 500 — index level (log scale)", color=MUTED, loc="left")
plt.show()
''' ))

cells.append(md("## 3. Returns year by year, and the risk\n",
                "Single years are unpredictable, but the majority close positive. The\n",
                "drawdown chart shows the other side of the coin: deep, recurring declines."))

cells.append(code(r'''
yearly = s.resample("YE").last().pct_change().dropna()
print(f"Positive years: {(yearly>0).mean()*100:.0f}%   |   "
      f"Best: {yearly.idxmax().year} (+{yearly.max()*100:.0f}%)   |   "
      f"Worst: {yearly.idxmin().year} ({yearly.min()*100:.0f}%)")

fig, ax = plt.subplots()
ax.bar(yearly.index.year, yearly.values*100,
       color=[GAIN if v>=0 else LOSS for v in yearly.values], width=0.8)
ax.axhline(0, color=MUTED, lw=0.8); clean(ax)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{v:.0f}%"))
ax.set_title("Calendar-year returns", color=MUTED, loc="left")
plt.show()
''' ))

cells.append(code(r'''
ddw = dd.resample("W").last()*100
fig, ax = plt.subplots()
ax.fill_between(ddw.index, ddw.values, 0, color=LOSS, alpha=0.18)
ax.plot(ddw.index, ddw.values, color=LOSS, lw=1.0)
ax.axhline(0, color=MUTED, lw=0.8); clean(ax)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{v:.0f}%"))
ax.set_title("Drawdown — decline from previous peak", color=MUTED, loc="left")
plt.show()
''' ))

cells.append(md("## 4. Dividends matter: price vs total return\n",
                "The price index ignores dividends. Reinvesting them changes the outcome\n",
                "dramatically over time."))

cells.append(code(r'''
df = pd.concat([price.asfreq("B").ffill(), tr.asfreq("B").ffill()],
               axis=1, keys=["Price", "Total return"]).dropna()
norm = df / df.iloc[0] * 100
yrs = (df.index[-1]-df.index[0]).days/365.25
p_cagr = (norm["Price"].iloc[-1]/100)**(1/yrs)-1
t_cagr = (norm["Total return"].iloc[-1]/100)**(1/yrs)-1
print(f"Since {df.index[0].year}:  $100 -> ${norm['Total return'].iloc[-1]:,.0f} (total return) "
      f"vs ${norm['Price'].iloc[-1]:,.0f} (price only)")
print(f"CAGR: {t_cagr*100:.1f}% total return  vs  {p_cagr*100:.1f}% price  "
      f"(+{(t_cagr-p_cagr)*100:.1f}%/yr from dividends)")

nw = norm.resample("W").last()
fig, ax = plt.subplots()
ax.plot(nw.index, nw["Total return"], color=GOLD, lw=1.8, label="With dividends reinvested")
ax.plot(nw.index, nw["Price"], color=INK, lw=1.3, label="Price only")
ax.fill_between(nw.index, nw["Price"], nw["Total return"], color=GOLD, alpha=0.10)
clean(ax); ax.legend(frameon=False, loc="upper left")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{int(v):,}"))
ax.set_title(f"Growth of 100 since {df.index[0].year} — the weight of dividends", color=MUTED, loc="left")
plt.show()
''' ))

cells.append(md("## 5. The key idea: time horizon\n",
                "The longer you stay invested, the higher the historical probability of\n",
                "ending in profit. This is the single most important driver of outcomes."))

cells.append(code(r'''
m = s.resample("ME").last()
rows = []
for label, n in [("1y",12),("5y",60),("10y",120),("15y",180),("20y",240)]:
    win = (m/m.shift(n)-1).dropna()
    rows.append((label, (win>0).mean()*100))
labels=[r[0] for r in rows]; vals=[r[1] for r in rows]
for l,v in rows: print(f"{l:>3}: {v:.0f}% of periods positive")

fig, ax = plt.subplots()
ax.barh(range(len(labels)), vals, color=GOLD, height=0.6)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels); ax.invert_yaxis()
ax.set_xlim(0,100)
for i,v in enumerate(vals): ax.text(v-2,i,f"{v:.0f}%",va="center",ha="right",color="white",fontweight="bold")
for sp in ("top","right","left","bottom"): ax.spines[sp].set_visible(False)
ax.tick_params(length=0); ax.set_xticks([])
ax.set_title("Historical probability of a positive return, by holding period", color=MUTED, loc="left")
plt.show()
''' ))

cells.append(md("## 6. Context: S&P 500 vs other asset classes\n",
                "Growth of $100 over the common period, with annualised return and volatility."))

cells.append(code(r'''
ac = {"Equity (S&P 500)": GOLD, "Bonds": "#3f6f8f", "Gold": "#7a8450", "Cash": "#aba499"}
adf = pd.concat({k: v.asfreq("B").ffill() for k,v in assets.items()}, axis=1).dropna()
anorm = adf/adf.iloc[0]*100
ay = (adf.index[-1]-adf.index[0]).days/365.25
summary = pd.DataFrame({
    "CAGR %": [( (anorm[c].iloc[-1]/100)**(1/ay)-1 )*100 for c in adf.columns],
    "Volatility %": [adf[c].pct_change().std()*np.sqrt(252)*100 for c in adf.columns],
}, index=adf.columns).round(1)
print(f"Common period since {adf.index[0].year}:")
print(summary.to_string())

anw = anorm.resample("W").last()
fig, ax = plt.subplots()
for c in adf.columns:
    ax.plot(anw.index, anw[c], color=ac[c], lw=2.1 if "Equity" in c else 1.5, label=c)
clean(ax); ax.legend(frameon=False, loc="upper left")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{int(v):,}"))
ax.set_title(f"Growth of 100 invested in {adf.index[0].year}, by asset class", color=MUTED, loc="left")
plt.show()
''' ))

cells.append(md(
    "## 7. Recommendations\n",
    "\n",
    "1. **Core exposure to the S&P 500 with a horizon of at least 10 years.** Over long\n",
    "   horizons the historical probability of a gain rises above ~89%. It is the stable\n",
    "   core of a portfolio, not a short-term bet.\n",
    "2. **Invest regularly; don't try to time the market.** Periodic contributions cut the\n",
    "   risk of buying at the top and turn volatility into a buying opportunity. *Time in the\n",
    "   market beats timing the market.*\n",
    "3. **Expect the drawdowns; don't sell in panic.** Declines of 20–30% are normal and have\n",
    "   so far always been recovered. Discipline in downturns is the main driver of realised return.\n",
    "4. **Reinvest dividends** (or use accumulating funds): they add roughly +2%/yr of compounding.\n",
    "5. **Size the equity weight to the client's risk profile**, alongside bonds and cash by\n",
    "   horizon and tolerance for losses.\n",
))

cells.append(md(
    "---\n",
    "*Data: Yahoo Finance. The price index excludes dividends; total return is higher. "
    "Past performance is not a guarantee of future results. For informational purposes only, "
    "not personalised investment advice.*\n",
))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook scritto: {OUT}  ({len(cells)} celle)")
