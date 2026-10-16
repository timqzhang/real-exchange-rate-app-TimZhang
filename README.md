# Bilateral Real Exchange Rate Explorer (IMF data)

A Streamlit app that builds a monthly bilateral real exchange rate (RER) for any two
countries using IMF CPI and exchange-rate data, starting January 1976 where available.

## Definitions

| Symbol | Meaning |
|---|---|
| E1(t), E2(t) | IMF exchange rates: local-currency units per USD (period average) |
| S(t) | Units of Country 2 currency per 1 unit of Country 1 currency = E2(t) / E1(t) |
| P1(t), P2(t) | Monthly CPI index for Country 1 and Country 2 |
| RER(t) | S(t) × P1(t) / P2(t) |
| RER* | Average of RER(t) over valid months in the selected sample |
| Real Index(t) | 100 × RER(t) / RER* |

A month is **valid** when all four inputs (E1, E2, P1, P2) are present and positive.
RER* is recalculated automatically whenever the start or end month changes.
A rise in the Real Index means a real appreciation of Country 1's currency against
Country 2's.

The nominal rate S(t) is plotted in actual currency units (not normalized).

## Data source

IMF SDMX 3.0 API: `https://api.imf.org/external/sdmx/3.0`

| Series | Dataflow | Key |
|---|---|---|
| CPI | `IMF.STA/CPI` | `{ISO3}.CPI._T.IX.M` |
| Exchange rate | `IMF.STA/ER` | `{ISO3}.XDC_USD.PA_RT.M` |

Example request:
```
https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/+/JPN.CPI._T.IX.M
```

- The Euro area uses code `G163` (can be switched on or off in the sidebar).
- For the United States, if the IMF returns no USD-per-USD series, E(t) is set to 1.
- The app requests SDMX-CSV first and falls back to SDMX-JSON.
- The country list comes from the IMF `CL_COUNTRY` codelist; if that request fails,
  it falls back to ISO 3166 codes from `pycountry`. Not every listed country has data.
- Downloads are cached for 24 hours. Use **Refresh IMF data** in the sidebar to clear the cache.
- If your network requires an IMF API subscription key, set the environment variable
  `IMF_API_KEY` (or add `IMF_API_KEY = "..."` to `.streamlit/secrets.toml`).

## Features

- Choose Country 1 and Country 2 from IMF countries (Euro area optional).
- Choose the sample period with a start/end month slider (defaults to the full overlap
  of all four series).
- Interactive Plotly chart: **Real**, **Nominal**, or **Both** (separate y-axes), with an
  optional log scale for the nominal rate.
- Coverage table showing the date range and status of each IMF series.
- **Download CSV** of every month in the selected sample, including E1, E2, S, P1, P2,
  RER, RER*, Real Index and a validity flag. Months with gaps are kept, with blank values.

## Installation (Python 3.12)

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Caveats

- IMF coverage varies by country: many series start well after 1976, and some contain gaps.
  The coverage table shows exactly what was returned.
- Euro-area member countries report euro rates after 1999; earlier values depend on how the
  IMF reports legacy currencies.
- CPI base years differ across countries. This does not affect the Real Index, because
  the index is normalized by RER* over the selected sample.
- In hyperinflation episodes S(t) can span many orders of magnitude; use the log-scale option.

## Files

- `app.py` — the Streamlit application
- `requirements.txt` — Python dependencies
- `README.md` — this file
