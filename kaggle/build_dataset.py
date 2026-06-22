#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assembla i file del Kaggle Dataset a partire dagli output della pipeline locale.
Esegui prima ./refresh.sh (per avere data/*.csv e metrics.json aggiornati).

Uso:  .venv/bin/python kaggle/build_dataset.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "kaggle" / "dataset"
OUT.mkdir(parents=True, exist_ok=True)

# sorgente -> nome pubblico nel dataset
MAPPING = {
    "_GSPC_daily.csv": "sp500_price_daily.csv",
    "_SP500TR_daily.csv": "sp500_total_return_daily.csv",
    "SPY_daily.csv": "etf_spy_equity_daily.csv",
    "AGG_daily.csv": "etf_agg_bonds_daily.csv",
    "GLD_daily.csv": "etf_gld_gold_daily.csv",
    "BIL_daily.csv": "etf_bil_cash_daily.csv",
    "metrics.json": "metrics.json",
}

copied = 0
for src, dst in MAPPING.items():
    p = DATA / src
    if p.exists():
        shutil.copy(p, OUT / dst)
        copied += 1
        print(f"  + {dst}")
    else:
        print(f"  ! manca {src} (esegui ./refresh.sh)")

# presentazione PDF (se presente: esegui prima analysis/build_pdf.py)
pdf = ROOT / "presentation" / "SP500_Investment_Research.pdf"
if pdf.exists():
    shutil.copy(pdf, OUT / pdf.name)
    copied += 1
    print(f"  + {pdf.name}")

print(f"Dataset assemblato in {OUT} ({copied} file).")
