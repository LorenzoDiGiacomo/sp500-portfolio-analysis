#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera la presentazione in PDF (16:9, una pagina per slide) da inviare/scaricare.
Riusa gli stessi dati e lo stile "Ink & Gold" della pipeline.

Esegui prima ./refresh.sh (per dati e metrics.json aggiornati), poi:
  .venv/bin/python analysis/build_pdf.py
Output: presentation/SP500_Investment_Research.pdf
"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_data as u  # palette, fetch_daily, compute_*

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "presentation" / "SP500_Investment_Research.pdf"

INK, MUTED, GOLD = u.INK, u.MUTED, u.GOLD
GAIN, LOSS, GRID, PAPER = u.GAIN, u.LOSS, u.GRID, u.PAPER
ASSET_COLORS = u.ASSET_COLORS

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "svg.fonttype": "none",
})

# ------------------------------------------------------------------ formattazione
def it_int(v):  return f"{round(v):,}".replace(",", ".")
def pct1(v):    return f"{v*100:.1f}".replace(".", ",") + "%"
def pct0(v):    return f"{round(v*100)}%"
def pct0abs(v): return "−" + f"{round(abs(v)*100)}%"

# ------------------------------------------------------------------ primitive pagina
def new_page():
    fig = plt.figure(figsize=(13.333, 7.5))
    fig.patch.set_facecolor(PAPER)
    return fig

def T(fig, x, y, s, size, color=INK, weight="light", ha="left", va="baseline", style="normal"):
    return fig.text(x, y, s, fontsize=size, color=color, ha=ha, va=va,
                    fontweight=weight, fontstyle=style)

def hairline(fig, x, y, w=0.05, color=GOLD, lw=2.4):
    fig.add_artist(Line2D([x, x + w], [y, y], transform=fig.transFigure, color=color, lw=lw))

def eyebrow(fig, txt, y=0.84):
    T(fig, 0.07, y, txt.upper(), 11, color=GOLD, weight="bold")

def metrics_row(fig, items, y=0.30, x0=0.07, dx=0.16):
    """items: list of (value, label, color)"""
    for i, (val, lbl, col) in enumerate(items):
        x = x0 + i * dx
        T(fig, x, y, val, 30, color=col, weight="light")
        T(fig, x, y - 0.07, lbl.upper(), 8.5, color=MUTED, weight="normal")

def chart_axes(fig):
    ax = fig.add_axes([0.46, 0.16, 0.50, 0.62])
    ax.set_facecolor(PAPER)
    return ax

def clean(ax):
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0, labelsize=10, colors=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.9)
    ax.set_axisbelow(True)

def cap(fig, txt):
    T(fig, 0.46, 0.115, txt, 9, color=MUTED)

# ------------------------------------------------------------------ disegno grafici
def draw_price(ax, s):
    s = s.resample("W").last().dropna()
    ax.plot(s.index, s.values, color=INK, lw=1.3)
    ax.fill_between(s.index, s.values, s.min(), color=GOLD, alpha=0.06)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: it_int(v)))
    clean(ax); ax.spines["bottom"].set_color(MUTED)

def draw_annual(ax, s):
    y = s.resample("YE").last().pct_change().dropna()
    ax.bar(y.index.year, y.values * 100,
           color=[GAIN if v >= 0 else LOSS for v in y.values], width=0.8)
    ax.axhline(0, color=MUTED, lw=0.8); clean(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    step = max(1, len(y) // 10)
    ax.set_xticks(y.index.year[::step])

def draw_drawdown(ax, s):
    s = s.resample("W").last().dropna()
    dd = (s / s.cummax() - 1) * 100
    ax.fill_between(dd.index, dd.values, 0, color=LOSS, alpha=0.18)
    ax.plot(dd.index, dd.values, color=LOSS, lw=1.0)
    ax.axhline(0, color=MUTED, lw=0.8); clean(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))

def draw_horizons(ax, m):
    h = m["horizons"]; labels = list(h.keys()); vals = [h[k]["pct_positive"] * 100 for k in labels]
    ax.barh(range(len(labels)), vals, color=GOLD, height=0.6)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=11, color=INK)
    ax.invert_yaxis(); ax.set_xlim(0, 100)
    for i, v in enumerate(vals):
        ax.text(v - 2, i, f"{v:.0f}%", va="center", ha="right", color="white", fontsize=11, fontweight="bold")
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0); ax.set_xticks([])

def draw_price_vs_tr(ax, price, tr):
    df = pd.concat([price.asfreq("B").ffill(), tr.asfreq("B").ffill()],
                   axis=1, keys=["p", "t"]).dropna().resample("W").last()
    n = df / df.iloc[0] * 100
    ax.plot(n.index, n["t"], color=GOLD, lw=1.8, label="Con dividendi reinvestiti")
    ax.plot(n.index, n["p"], color=INK, lw=1.3, label="Solo prezzo")
    ax.fill_between(n.index, n["p"], n["t"], color=GOLD, alpha=0.10)
    clean(ax); ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: it_int(v)))

def draw_assets(ax, assets, names):
    df = pd.concat({k: assets[k].asfreq("B").ffill() for k in names}, axis=1).dropna()
    n = (df / df.iloc[0] * 100).resample("W").last()
    for name in names:
        ax.plot(n.index, n[name], color=ASSET_COLORS.get(name, MUTED),
                lw=2.1 if "Azionario" in name else 1.5, label=name)
    clean(ax); ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: it_int(v)))

# ------------------------------------------------------------------ build
def main():
    metrics = json.loads((ROOT / "data" / "metrics.json").read_text(encoding="utf-8"))
    m = metrics
    price = u.fetch_daily("^GSPC")
    tr = u.fetch_daily("^SP500TR")
    assets = {name: u.fetch_daily(tk) for name, tk in u.ASSET_TICKERS.items()}

    with PdfPages(OUT) as pdf:
        # 1. COVER
        fig = new_page()
        eyebrow(fig, "Investment Research · Portfolio Advisory", y=0.70)
        T(fig, 0.07, 0.52, "S&P 500", 78, color=INK, weight="light")
        T(fig, 0.07, 0.40, "Cos'è, come si è comportato nel tempo", 18, color="#3c4147")
        T(fig, 0.07, 0.355, "e cosa ne ricaviamo per i portafogli dei clienti.", 18, color="#3c4147")
        hairline(fig, 0.07, 0.30)
        T(fig, 0.07, 0.22, f"Dati aggiornati al {m['last_date']}  ·  serie storica dal {m['first_date']}  ·  "
                           f"Fonte: S&P 500 (^GSPC), Yahoo Finance", 10.5, color=MUTED)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 2. COS'È
        fig = new_page()
        eyebrow(fig, "Il punto di partenza")
        T(fig, 0.07, 0.70, "Cos'è l'S&P 500", 40, color=INK, weight="light")
        lead = ("Un indice che misura l'andamento delle circa 500 maggiori società quotate\n"
                "statunitensi. È il riferimento più usato al mondo per il mercato azionario USA.")
        T(fig, 0.07, 0.585, lead, 15, color="#3c4147")
        facts = [("~500", "grandi aziende USA, da più settori:\ntecnologia, salute, finanza, consumi, energia."),
                 ("Ponderato", "per capitalizzazione: le aziende più\ngrandi pesano di più. Si ribilancia da solo."),
                 ("Diversificato", "un solo strumento espone a centinaia\ndi aziende: il rischio del singolo titolo si diluisce.")]
        for i, (k, t) in enumerate(facts):
            x = 0.07 + i * 0.30
            fig.add_artist(Line2D([x, x + 0.26], [0.40, 0.40], transform=fig.transFigure, color=GRID, lw=1))
            T(fig, x, 0.345, k, 22, color=GOLD, weight="light")
            T(fig, x, 0.275, t, 11, color="#3c4147")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 3. ANDAMENTO STORICO
        fig = new_page()
        eyebrow(fig, "Andamento storico")
        T(fig, 0.07, 0.71, "Una crescita", 30, weight="light")
        T(fig, 0.07, 0.645, "di lungo periodo", 30, weight="light")
        T(fig, 0.07, 0.515,"Nonostante guerre, recessioni e crisi,\nsul lungo periodo l'indice ha sempre\nsuperato i massimi precedenti.",
          14, color="#3c4147")
        metrics_row(fig, [("$" + it_int(m["growth_100"]), f"da $100 nel {m['first_date']}", GOLD),
                          ("+" + pct1(m["cagr"]), "rendimento medio annuo", INK)], y=0.30)
        draw_price(chart_axes(fig), price)
        cap(fig, "Scala logaritmica: stessa distanza = stessa crescita percentuale.")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 4. DIVIDENDI
        fig = new_page()
        trm = m["tr"]
        eyebrow(fig, "Prezzo vs rendimento totale")
        T(fig, 0.07, 0.71, "I dividendi", 30, weight="light")
        T(fig, 0.07, 0.645, "cambiano il risultato", 30, weight="light")
        T(fig, 0.07, 0.515,f"L'indice di prezzo ignora i dividendi.\nReinvestendoli, dal {trm['start_year']} il capitale\nfinale è più che raddoppiato.",
          14, color="#3c4147")
        metrics_row(fig, [("$" + it_int(trm["tr_growth100"]), "con dividendi (da $100)", GOLD),
                          ("$" + it_int(trm["price_growth100"]), "solo prezzo", INK),
                          ("+" + pct1(trm["dividend_cagr"]), "all'anno dai dividendi", GAIN)], y=0.30, dx=0.13)
        draw_price_vs_tr(chart_axes(fig), price, tr)
        cap(fig, f"Rendimento totale annuo {pct1(trm['tr_cagr'])} contro {pct1(trm['price_cagr'])} del solo prezzo.")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 5. DRAWDOWN
        fig = new_page()
        eyebrow(fig, "L'altra faccia: il rischio")
        T(fig, 0.07, 0.71, "Le cadute fanno", 30, weight="light")
        T(fig, 0.07, 0.645, "parte del percorso", 30, weight="light")
        T(fig, 0.07, 0.515,"Il rendimento non è gratis: cali profondi\nsono ricorrenti. Vanno messi in conto,\nnon temuti.", 14, color="#3c4147")
        metrics_row(fig, [(pct0abs(m["max_dd"]), f"caduta massima ({m['max_dd_year']})", LOSS),
                          (pct0(m["vol"]), "volatilità annua", INK)], y=0.30)
        draw_drawdown(chart_axes(fig), price)
        cap(fig, "Distanza percentuale dal massimo precedente, nel tempo.")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 6. RENDIMENTI ANNUI
        fig = new_page()
        eyebrow(fig, "Anno per anno")
        T(fig, 0.07, 0.71, "Più anni positivi", 30, weight="light")
        T(fig, 0.07, 0.645, "che negativi", 30, weight="light")
        T(fig, 0.07, 0.515,"I singoli anni sono imprevedibili, ma\nla maggioranza si chiude in guadagno.", 14, color="#3c4147")
        metrics_row(fig, [(pct0(m["pct_positive_years"]), "anni in positivo", GAIN),
                          ("+" + pct0(m["best_year_ret"]), f"migliore ({m['best_year']})", GAIN),
                          (pct0(m["worst_year_ret"]), f"peggiore ({m['worst_year']})", LOSS)], y=0.30, dx=0.13)
        draw_annual(chart_axes(fig), price)
        cap(fig, "Verde: anno positivo · Rosso: anno negativo.")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 7. ORIZZONTE
        fig = new_page()
        eyebrow(fig, "L'idea chiave")
        T(fig, 0.07, 0.71, "L'orizzonte temporale", 30, weight="light")
        T(fig, 0.07, 0.645, "cambia tutto", 30, weight="light", color=GOLD)
        T(fig, 0.07, 0.515,"Più a lungo si resta investiti, più alta\nè storicamente la probabilità di\nchiudere in guadagno.", 14, color="#3c4147")
        metrics_row(fig, [(pct0(m["horizons"]["1 anno"]["pct_positive"]), "su 1 anno", INK),
                          (pct0(m["horizons"]["20 anni"]["pct_positive"]), "su 20 anni", GAIN)], y=0.30)
        draw_horizons(chart_axes(fig), m)
        cap(fig, "Quota di periodi storici chiusi in positivo, per durata dell'investimento.")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 8. ASSET CLASS
        fig = new_page()
        am = m["assets"]
        eyebrow(fig, "Il contesto di portafoglio")
        T(fig, 0.07, 0.71, "S&P 500 e le altre", 30, weight="light")
        T(fig, 0.07, 0.65, "asset class", 30, weight="light", color=GOLD)
        T(fig, 0.07, 0.535, f"Dal {am['start_year']}: l'azionario è il principale\nmotore di crescita; obbligazioni e\nliquidità danno stabilità.", 13, color="#3c4147")
        # tabellina
        rows = [("Azionario (S&P 500)", "Azionario (S&P 500)", GOLD), ("Oro", "Oro", "#7a8450"),
                ("Obbligazioni", "Obbligazioni", "#3f6f8f"), ("Liquidità", "Liquidità", "#aba499")]
        ty = 0.40
        T(fig, 0.085, ty, "ASSET", 8.5, color=MUTED, weight="normal")
        T(fig, 0.27, ty, "REND.", 8.5, color=MUTED, weight="normal", ha="right")
        T(fig, 0.34, ty, "VOL.", 8.5, color=MUTED, weight="normal", ha="right")
        for j, (lbl, key, col) in enumerate(rows):
            yy = ty - 0.055 * (j + 1)
            fig.add_artist(Line2D([0.07, 0.34], [yy + 0.03, yy + 0.03], transform=fig.transFigure, color=GRID, lw=0.8))
            fig.add_artist(plt.matplotlib.patches.Circle((0.078, yy + 0.008), 0.006, transform=fig.transFigure, color=col))
            T(fig, 0.095, yy, lbl, 11, color=INK, weight="normal")
            T(fig, 0.27, yy, pct1(am["items"][key]["cagr"]), 11, color=INK, ha="right")
            T(fig, 0.34, yy, pct0(am["items"][key]["vol"]), 11, color=MUTED, ha="right")
        draw_assets(chart_axes(fig), assets, list(am["items"].keys()))
        cap(fig, f"Crescita di $100 dal {am['start_year']}. Fonte: ETF (SPY, AGG, GLD, BIL).")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 9. RACCOMANDAZIONI
        fig = new_page()
        eyebrow(fig, "La nostra posizione")
        T(fig, 0.07, 0.74, "Raccomandazioni", 36, weight="light")
        recos = [
            ("01", "Esposizione core all'S&P 500, orizzonte ≥ 10 anni",
             f"Su orizzonti lunghi la probabilità storica di guadagno supera il {pct0(m['horizons']['10 anni']['pct_positive'])}. Il cuore stabile del portafoglio."),
            ("02", "Investire in modo regolare, non cercare il momento perfetto",
             "Versamenti periodici (PAC) riducono il rischio di entrare al picco. Il tempo nel mercato batte il tempismo sul mercato."),
            ("03", "Mettere in conto le cadute, senza disinvestire nel panico",
             "Cali del 20–30% sono fisiologici e finora sempre recuperati. La disciplina nei ribassi guida il rendimento reale."),
            ("04", "Dimensionare il peso azionario sul profilo di rischio",
             "Motore di crescita da affiancare a obbligazioni e liquidità in base a orizzonte e tolleranza alle perdite."),
            ("05", "Reinvestire i dividendi (o usare fondi ad accumulazione)",
             "Aggiungono circa +2% l'anno di rendimento composto nel lungo periodo."),
        ]
        yy = 0.62
        for n, t, d in recos:
            fig.add_artist(Line2D([0.07, 0.93], [yy + 0.035, yy + 0.035], transform=fig.transFigure, color=GRID, lw=0.8))
            T(fig, 0.07, yy, n, 13, color=GOLD, weight="normal")
            T(fig, 0.12, yy, t, 14.5, color=INK, weight="normal")
            T(fig, 0.12, yy - 0.035, d, 10.5, color="#3c4147")
            yy -= 0.115
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # 10. SINTESI
        fig = new_page()
        eyebrow(fig, "In sintesi")
        T(fig, 0.07, 0.66, "Crescita nel lungo periodo,", 30, weight="light")
        T(fig, 0.07, 0.595, "disciplina nel breve.", 30, weight="light")
        hairline(fig, 0.07, 0.52)
        T(fig, 0.07, 0.44, "L'S&P 500 ha premiato storicamente gli investitori pazienti e diversificati.\n"
                           "Il nostro ruolo è allineare orizzonte, rischio e aspettative di ogni cliente.", 13, color="#3c4147")
        T(fig, 0.07, 0.27, f"Analisi rigenerata automaticamente · ultimo aggiornamento {m['generated_at']}", 10, color=GOLD, weight="bold")
        T(fig, 0.07, 0.16, "Nota: l'indice di prezzo non include i dividendi; il rendimento totale reinvestito è superiore.\n"
                           "I rendimenti passati non sono garanzia di risultati futuri. Documento informativo, non consulenza personalizzata.",
          9, color="#a8aab0")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        d = pdf.infodict()
        d["Title"] = "S&P 500 — Investment Research"
        d["Author"] = "Lorenzo Di Giacomo"
        d["Subject"] = "Analisi S&P 500 e raccomandazioni di portafoglio"

    print(f"PDF creato: {OUT}")


if __name__ == "__main__":
    main()
