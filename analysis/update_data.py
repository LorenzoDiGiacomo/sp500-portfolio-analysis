#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline di analisi S&P 500 — automatica e sempre aggiornata.

Cosa fa, in ordine:
  1. Scarica da Yahoo Finance:
       - S&P 500 prezzo (^GSPC, storico dal 1927)
       - S&P 500 total return (^SP500TR, con dividendi reinvestiti, dal 1988)
       - proxy asset class: azionario (SPY), obbligazioni (AGG), oro (GLD), liquidita' (BIL)
     Con retry; se la rete non e' disponibile usa l'ultima copia in cache, cosi' la
     presentazione non si rompe mai.
  2. Calcola le metriche chiave (CAGR, volatilita', drawdown, rendimenti annui,
     analisi per orizzonte, prezzo vs total return, confronto asset class).
  3. Genera i grafici in SVG con stile minimalista "Ink & Gold".
  4. Scrive assets/data.js  ->  i numeri della presentazione si aggiornano da soli.

Eseguilo con:  ./refresh.sh   (oppure  .venv/bin/python analysis/update_data.py)
"""

import json
import re
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# --------------------------------------------------------------------------- #
# Percorsi
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "presentation" / "assets"
DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

TICKER = "^GSPC"
ASSET_TICKERS = {"Azionario (S&P 500)": "SPY", "Obbligazioni": "AGG",
                 "Oro": "GLD", "Liquidità": "BIL"}

# --------------------------------------------------------------------------- #
# Palette "Ink & Gold" — coerente con la presentazione
# --------------------------------------------------------------------------- #
INK = "#1f2328"        # testo / linee principali
MUTED = "#8a8f98"      # assi / testo secondario
GOLD = "#b6892b"       # accento
GAIN = "#2f7d5b"       # rendimenti positivi
LOSS = "#b0413e"       # rendimenti negativi / drawdown
GRID = "#e7e3da"       # griglia leggerissima
PAPER = "#faf8f3"      # sfondo carta (uguale al deck)

# colori per il confronto fra asset class
ASSET_COLORS = {
    "Azionario (S&P 500)": GOLD,
    "Obbligazioni": "#3f6f8f",
    "Oro": "#7a8450",
    "Liquidità": "#aba499",
}

plt.rcParams.update({
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 13,
    "axes.edgecolor": MUTED,
    "axes.linewidth": 0.8,
    "axes.titlesize": 14,
    "axes.titleweight": "regular",
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "svg.fonttype": "none",
})


# --------------------------------------------------------------------------- #
# 1. Acquisizione dati (generica, con cache per-ticker)
# --------------------------------------------------------------------------- #
def _cache_path(ticker: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9]", "_", ticker)
    return DATA_DIR / f"{safe}_daily.csv"


def fetch_daily(ticker: str, retries: int = 4, pause: int = 3, min_rows: int = 100) -> pd.Series:
    """Scarica la chiusura giornaliera (auto_adjust); ripiega sulla cache se offline."""
    import yfinance as yf

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(ticker, period="max", interval="1d",
                             progress=False, auto_adjust=True, threads=False)
            if df is not None and len(df) > min_rows:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                close = df["Close"].dropna()
                close.index = pd.to_datetime(close.index)
                close.to_csv(_cache_path(ticker))
                print(f"[dati] {ticker:10} {len(close)} oss. "
                      f"({close.index.min().date()} -> {close.index.max().date()})")
                return close
            raise RuntimeError("dataset troppo piccolo o vuoto")
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[dati] {ticker}: tentativo {attempt}/{retries} fallito ({e})")
            time.sleep(pause)

    p = _cache_path(ticker)
    if p.exists():
        print(f"[dati] {ticker}: rete non disponibile -> uso cache")
        s = pd.read_csv(p, index_col=0, parse_dates=True).iloc[:, 0].dropna()
        return s

    print(f"[errore] {ticker}: nessun dato e nessuna cache: {last_err}", file=sys.stderr)
    return pd.Series(dtype=float)


# --------------------------------------------------------------------------- #
# 2. Metriche
# --------------------------------------------------------------------------- #
def compute_metrics(close: pd.Series) -> dict:
    s = close.copy().asfreq("B").ffill()
    rets = s.pct_change().dropna()

    first_date, last_date = s.index[0], s.index[-1]
    first_px, last_px = float(s.iloc[0]), float(s.iloc[-1])
    years = (last_date - first_date).days / 365.25

    cagr = (last_px / first_px) ** (1 / years) - 1
    vol = float(rets.std() * np.sqrt(252))

    dd = s / s.cummax() - 1.0
    max_dd = float(dd.min())
    max_dd_date = dd.idxmin()

    yearly = s.resample("YE").last()
    yearly_ret = yearly.pct_change().dropna()
    prev_year_close = yearly[yearly.index.year == last_date.year - 1]
    ytd = (last_px / float(prev_year_close.iloc[0]) - 1) if len(prev_year_close) else float("nan")

    best_year = yearly_ret.idxmax().year
    worst_year = yearly_ret.idxmin().year
    growth_100 = 100 * last_px / first_px

    monthly = s.resample("ME").last()
    horizons = {}
    for ylabel, n in [("1 anno", 12), ("5 anni", 60), ("10 anni", 120),
                      ("15 anni", 180), ("20 anni", 240)]:
        if len(monthly) > n:
            w = (monthly / monthly.shift(n) - 1).dropna()
            horizons[ylabel] = {"pct_positive": float((w > 0).mean()),
                                "median_total": float(w.median())}

    return {
        "ticker": TICKER,
        "generated_at": datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M"),
        "first_date": first_date.strftime("%Y"),
        "last_date": last_date.strftime("%d/%m/%Y"),
        "last_close": last_px,
        "years": years,
        "cagr": cagr,
        "vol": vol,
        "max_dd": max_dd,
        "max_dd_year": int(max_dd_date.year),
        "ytd": ytd,
        "best_year": best_year, "best_year_ret": float(yearly_ret.max()),
        "worst_year": worst_year, "worst_year_ret": float(yearly_ret.min()),
        "pct_positive_years": float((yearly_ret > 0).mean()),
        "avg_year": float(yearly_ret.mean()),
        "growth_100": growth_100,
        "horizons": horizons,
    }


def compute_total_return(price: pd.Series, tr: pd.Series) -> dict:
    """Confronto prezzo vs total return sul periodo comune."""
    if tr is None or tr.empty:
        return {}
    p = price.asfreq("B").ffill()
    t = tr.asfreq("B").ffill()
    df = pd.concat([p, t], axis=1, keys=["price", "tr"]).dropna()
    if df.empty:
        return {}
    start = df.index[0]
    years = (df.index[-1] - start).days / 365.25
    p0, t0 = df["price"].iloc[0], df["tr"].iloc[0]
    p_g = 100 * df["price"].iloc[-1] / p0
    t_g = 100 * df["tr"].iloc[-1] / t0
    p_cagr = (p_g / 100) ** (1 / years) - 1
    t_cagr = (t_g / 100) ** (1 / years) - 1
    return {
        "start_year": start.strftime("%Y"),
        "years": years,
        "price_growth100": float(p_g),
        "tr_growth100": float(t_g),
        "price_cagr": float(p_cagr),
        "tr_cagr": float(t_cagr),
        "dividend_cagr": float(t_cagr - p_cagr),
    }


def compute_assets(series_by_name: dict) -> dict:
    """Confronto fra asset class sul periodo comune piu' lungo possibile."""
    series_by_name = {k: v for k, v in series_by_name.items() if v is not None and not v.empty}
    if len(series_by_name) < 2:
        return {}
    df = pd.concat({k: v.asfreq("B").ffill() for k, v in series_by_name.items()}, axis=1).dropna()
    if df.empty:
        return {}
    start = df.index[0]
    years = (df.index[-1] - start).days / 365.25
    norm = df / df.iloc[0] * 100
    items = {}
    for name in df.columns:
        rets = df[name].pct_change().dropna()
        g = float(norm[name].iloc[-1])
        items[name] = {
            "growth100": g,
            "cagr": float((g / 100) ** (1 / years) - 1),
            "vol": float(rets.std() * np.sqrt(252)),
        }
    return {"start_year": start.strftime("%Y"), "years": years, "items": items}


# --------------------------------------------------------------------------- #
# 3. Grafici (SVG, stile minimalista)
# --------------------------------------------------------------------------- #
def _clean_axes(ax):
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(ASSETS_DIR / name, format="svg", bbox_inches="tight", transparent=False)
    plt.close(fig)
    print(f"[grafico] {name}")


def _euro_int(v, _):  # separatore migliaia con punto
    return f"{int(v):,}".replace(",", ".")


def chart_price(s: pd.Series):
    s = s.resample("W").last().dropna()
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.plot(s.index, s.values, color=INK, linewidth=1.4)
    ax.fill_between(s.index, s.values, s.min(), color=GOLD, alpha=0.06)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_euro_int))
    _clean_axes(ax)
    ax.spines["bottom"].set_color(MUTED)
    ax.set_title("Valore dell'indice — scala logaritmica", color=MUTED, loc="left", pad=14)
    save(fig, "price_log.svg")


def chart_annual(s: pd.Series):
    yearly = s.resample("YE").last().pct_change().dropna()
    years = yearly.index.year
    vals = yearly.values * 100
    colors = [GAIN if v >= 0 else LOSS for v in vals]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.bar(years, vals, color=colors, width=0.78)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    _clean_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    step = max(1, len(years) // 12)
    ax.set_xticks(years[::step])
    ax.set_title("Rendimento per anno solare", color=MUTED, loc="left", pad=14)
    save(fig, "annual_returns.svg")


def chart_drawdown(s: pd.Series):
    s = s.resample("W").last().dropna()
    dd = (s / s.cummax() - 1.0) * 100
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.fill_between(dd.index, dd.values, 0, color=LOSS, alpha=0.18)
    ax.plot(dd.index, dd.values, color=LOSS, linewidth=1.0)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    _clean_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("Perdita dai massimi (drawdown)", color=MUTED, loc="left", pad=14)
    save(fig, "drawdown.svg")


def chart_horizons(metrics: dict):
    h = metrics["horizons"]
    labels = list(h.keys())
    vals = [h[k]["pct_positive"] * 100 for k in labels]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.barh(range(len(labels)), vals, color=GOLD, height=0.6)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    for i, v in enumerate(vals):
        ax.text(v - 2, i, f"{v:.0f}%", va="center", ha="right",
                color="white", fontsize=12, fontweight="bold")
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    ax.set_xticks([])
    ax.set_title("Probabilita' storica di chiudere in positivo, per orizzonte",
                 color=MUTED, loc="left", pad=14)
    save(fig, "horizons.svg")


def chart_price_vs_tr(price: pd.Series, tr: pd.Series, tr_meta: dict):
    if not tr_meta:
        return
    p = price.asfreq("B").ffill()
    t = tr.asfreq("B").ffill()
    df = pd.concat([p, t], axis=1, keys=["price", "tr"]).dropna().resample("W").last()
    norm = df / df.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.plot(norm.index, norm["tr"], color=GOLD, linewidth=1.8, label="Con dividendi reinvestiti")
    ax.plot(norm.index, norm["price"], color=INK, linewidth=1.4, label="Solo prezzo")
    ax.fill_between(norm.index, norm["price"], norm["tr"], color=GOLD, alpha=0.10)
    _clean_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_euro_int))
    ax.legend(loc="upper left", frameon=False, fontsize=12)
    ax.set_title(f"Crescita di 100 dal {tr_meta['start_year']} — il peso dei dividendi",
                 color=MUTED, loc="left", pad=14)
    save(fig, "price_vs_tr.svg")


def chart_assets(series_by_name: dict, assets_meta: dict):
    if not assets_meta:
        return
    names = list(assets_meta["items"].keys())
    df = pd.concat({k: series_by_name[k].asfreq("B").ffill() for k in names}, axis=1).dropna()
    norm = (df / df.iloc[0] * 100).resample("W").last()
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for name in names:
        lw = 2.1 if "Azionario" in name else 1.5
        ax.plot(norm.index, norm[name], color=ASSET_COLORS.get(name, MUTED),
                linewidth=lw, label=name)
    _clean_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_euro_int))
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    ax.set_title(f"Crescita di 100 investiti nel {assets_meta['start_year']}, per asset class",
                 color=MUTED, loc="left", pad=14)
    save(fig, "assets.svg")


# --------------------------------------------------------------------------- #
# 4. Scrittura dati per la presentazione
# --------------------------------------------------------------------------- #
def write_data_js(metrics: dict):
    payload = "window.METRICS = " + json.dumps(metrics, ensure_ascii=False, indent=2) + ";\n"
    (ASSETS_DIR / "data.js").write_text(payload, encoding="utf-8")
    (DATA_DIR / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[dati] assets/data.js aggiornato")


def main():
    print("=" * 60)
    print("Aggiornamento analisi S&P 500")
    print("=" * 60)

    close = fetch_daily(TICKER)
    tr = fetch_daily("^SP500TR")
    assets = {name: fetch_daily(tk) for name, tk in ASSET_TICKERS.items()}

    metrics = compute_metrics(close)
    metrics["tr"] = compute_total_return(close, tr)
    metrics["assets"] = compute_assets(assets)

    chart_price(close)
    chart_annual(close)
    chart_drawdown(close)
    chart_horizons(metrics)
    chart_price_vs_tr(close, tr, metrics["tr"])
    chart_assets(assets, metrics["assets"])
    write_data_js(metrics)

    print("-" * 60)
    print(f"Ultimo dato : {metrics['last_date']}  |  livello {metrics['last_close']:,.0f}")
    print(f"CAGR prezzo : {metrics['cagr']*100:.1f}%  dal {metrics['first_date']}")
    if metrics["tr"]:
        print(f"CAGR TR     : {metrics['tr']['tr_cagr']*100:.1f}%  "
              f"(+{metrics['tr']['dividend_cagr']*100:.1f}% dai dividendi, dal {metrics['tr']['start_year']})")
    print("Fatto. Apri presentation/index.html")
    print("=" * 60)


if __name__ == "__main__":
    main()
