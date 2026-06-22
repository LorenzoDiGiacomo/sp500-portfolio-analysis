# S&P 500 — Analisi & Presentazione per i clienti

Sistema **automatico e sempre aggiornato**: uno script Python scarica i dati reali
dell'S&P 500, calcola le metriche e rigenera i grafici; la presentazione HTML li
mostra e si aggiorna da sola.

**Portfolio:**
[🌐 Presentazione live](https://lorenzodigiacomo.github.io/sp500-portfolio-analysis/)
· [📄 PDF da inviare](https://lorenzodigiacomo.github.io/sp500-portfolio-analysis/presentation/SP500_Investment_Research.pdf)
· [📊 Kaggle Notebook](https://www.kaggle.com/code/lorenzodigiacomo13/s-p-500-long-term-analysis-recommendations)
· [🗂️ Kaggle Dataset](https://www.kaggle.com/datasets/lorenzodigiacomo13/s-p-500-index-long-term-analysis-data)

## Uso rapido

**1. Aggiorna l'analisi** (scarica i dati più recenti e rigenera tutto):

```bash
./refresh.sh
```

Alla prima esecuzione crea il virtualenv e installa le dipendenze (yfinance,
pandas, matplotlib). Le volte successive è immediato.

**2. Apri la presentazione**: fai doppio clic su

```
presentation/index.html
```

Si apre nel browser, funziona offline, nessun server necessario.
Frecce ← → (o spazio / clic) per navigare; i pallini in basso saltano alle slide.

> Ogni volta che lanci `./refresh.sh` e ricarichi la pagina, numeri e grafici
> riflettono l'ultimo dato di mercato. Non si tocca nulla a mano.

**3. (Opzionale) Genera il PDF da inviare:**

```bash
.venv/bin/python analysis/build_pdf.py
```

Crea `presentation/SP500_Investment_Research.pdf` (10 pagine, 16:9) da allegare via email.

## Struttura

```
analysis/update_data.py     Pipeline: dati → metriche → grafici SVG → data.js
data/                       Cache dati (sp500_daily.csv) e metrics.json
presentation/
  index.html                Il deck (template, non cambia)
  style.css                 Stile "Ink & Gold", minimalista
  deck.js                   Navigazione + iniezione dei dati
  assets/                   Generati automaticamente: *.svg + data.js
refresh.sh                  Comando unico di aggiornamento
```

## Contenuto della presentazione (10 slide)

1. Copertina
2. Cos'è l'S&P 500
3. Andamento storico (crescita di lungo periodo)
4. Il peso dei dividendi (prezzo vs total return)
5. Il rischio: i drawdown
6. Rendimenti anno per anno
7. L'orizzonte temporale cambia tutto
8. S&P 500 e le altre asset class (azionario vs obbligazioni / oro / liquidità)
9. **Raccomandazioni** (evidence-based)
10. Sintesi e disclaimer

Valori in **dollari ($)**, valuta nativa dell'indice.

## Note metodologiche

- Fonti (Yahoo Finance):
  - S&P 500 prezzo: `^GSPC` (storico dal 1927)
  - S&P 500 total return: `^SP500TR` (con dividendi reinvestiti, dal 1988)
  - Asset class (ETF rappresentativi, total return): `SPY` azionario, `AGG` obbligazioni,
    `GLD` oro, `BIL` liquidità — confrontati sul periodo comune (dal 2007).
- Le metriche headline di lungo periodo (CAGR, drawdown dal 1927) usano l'indice di **prezzo**,
  che non include i dividendi: la slide 4 mostra esplicitamente il rendimento totale (≈ +2,3%/anno
  in più). Scelta conservativa e dichiarata.
- Se la rete non è raggiungibile, la pipeline usa le copie in cache (`data/*_daily.csv`)
  e la presentazione continua a funzionare.
- I rendimenti passati non sono garanzia di risultati futuri. Documento informativo,
  non consulenza personalizzata.

## Aggiornamento programmato (opzionale)

Per tenerla aggiornata da sola, ad es. ogni giorno alle 8:00, aggiungi a `crontab -e`:

```
0 8 * * *  cd "/Users/lorenzodigiacomo/Downloads/portfolio management analisis" && ./refresh.sh
```
