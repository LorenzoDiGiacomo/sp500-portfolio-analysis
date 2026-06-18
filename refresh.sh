#!/usr/bin/env bash
# Aggiorna dati, metriche e grafici della presentazione S&P 500.
# Uso:  ./refresh.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[setup] creo il virtualenv e installo le dipendenze..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet yfinance pandas matplotlib
fi

.venv/bin/python analysis/update_data.py
