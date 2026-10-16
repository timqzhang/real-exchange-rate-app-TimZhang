"""
Bilateral Real Exchange Rate (RER) explorer built on IMF SDMX 3.0 data.

Definitions
-----------
S(t)   : units of Country 2 currency per 1 unit of Country 1 currency
P1(t)  : Country 1 monthly CPI (index)
P2(t)  : Country 2 monthly CPI (index)
RER(t) = S(t) * P1(t) / P2(t)
RER*   = mean of RER(t) over valid months in the user-selected sample
Real Index(t) = 100 * RER(t) / RER*

IMF exchange rates (key {ISO3}.XDC_USD.PA_RT.M) are local-currency units per USD
(period average).  With E1 = C1 per USD and E2 = C2 per USD:
    S(t) = E2(t) / E1(t)   (C2 per C1)

Run:  streamlit run app.py
"""

from __future__ import annotations

import io
import json
import os
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://api.imf.org/external/sdmx/3.0"
CPI_FLOW = ("IMF.STA", "CPI")
ER_FLOW = ("IMF.STA", "ER")
CPI_KEY = "{iso}.CPI._T.IX.M"
ER_KEY = "{iso}.XDC_USD.PA_RT.M"
START_MONTH = pd.Timestamp("1976-01-01")
EURO_AREA_CODE = "G163"
EURO_AREA_NAME = "Euro area"
TIMEOUT = 60

CSV_ACCEPT = "application/vnd.sdmx.data+csv;version=2.0.0"
JSON_ACCEPT = "application/vnd.sdmx.data+json;version=2.0.0"
STRUCT_ACCEPT = "application/vnd.sdmx.structure+json;version=2.0.0"

_PERIOD_RE = re.compile(r"^\s*(\d{4})\s*-?\s*M?\s*(\d{1,2})\s*$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _api_key() -> str | None:
    """Optional IMF API subscription key (env var or Streamlit secrets)."""
    key = os.environ.get("IMF_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("IMF_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        return None


def _headers(accept: str) -> dict[str, str]:
    h = {
        "Accept": accept,
        "User-Agent": "rer-streamlit-app/1.0 (python-requests)",
        "Cache-Control": "no-cache",
    }
    key = _api_key()
    if key:
        h["Ocp-Apim-Subscription-Key"] = key
    return h


def parse_period(value) -> pd.Timestamp:
    """Parse IMF monthly periods such as '2020-M01', '2020M01', '2020-01'."""
    m = _PERIOD_RE.match(str(value))
    if not m:
        return pd.NaT
    year, month = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        return pd.NaT
    return pd.Timestamp(year=year, month=month, day=1)


def _to_series(periods, values) -> pd.Series:
    idx = pd.DatetimeIndex([parse_period(p) for p in periods])
    s = pd.Series(pd.to_numeric(pd.Series(list(values)), errors="coerce").values, index=idx)
    s = s[s.index.notna()]
    s = s[~s.index.duplicated(keep="first")].sort_index()
    s = s[s.index >= START_MONTH]
    s = s.where(s > 0)  # CPI and exchange rates must be strictly positive
    return s.dropna().astype(float)


def _parse_csv(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text), dtype=str)
    cols = {c.upper(): c for c in df.columns}
    if "TIME_PERIOD" not in cols or "OBS_VALUE" not in cols:
        return pd.Series(dtype=float)
    # If several series came back, keep the first one.
    series_cols = [c for c in ("COUNTRY", "INDICATOR", "INDEX_TYPE", "COICOP_1999",
                               "TYPE_OF_TRANSFORMATION", "FREQUENCY", "SERIES_KEY", "KEY")
                   if c in cols]
    if series_cols:
        first = df.iloc[0]
        mask = np.ones(len(df), dtype=bool)
        for c in series_cols:
            mask &= (df[cols[c]] == first[cols[c]]).to_numpy()
        df = df[mask]
    return _to_series(df[cols["TIME_PERIOD"]], df[cols["OBS_VALUE"]])


def _parse_json(text: str) -> pd.Series:
    js = json.loads(text)
    data = js.get("data", js)
    datasets = data.get("dataSets") or []
    structures = data.get("structures") or ([data["structure"]] if "structure" in data else [])
    if not datasets or not structures:
        return pd.Series(dtype=float)
    obs_dims = structures[0].get("dimensions", {}).get("observation", [])
    t_pos = next((i for i, d in enumerate(obs_dims) if d.get("id") == "TIME_PERIOD"), 0)
    if not obs_dims:
        return pd.Series(dtype=float)
    t_values = obs_dims[t_pos].get("values", [])
    series = datasets[0].get("series", {}) or {}
    periods, values = [], []
    for _, s in series.items():
        for okey, ov in (s.get("observations") or {}).items():
            idx = int(str(okey).split(":")[t_pos])
            tv = t_values[idx]
            periods.append(tv.get("id") or tv.get("value") or tv.get("name"))
            values.append(ov[0] if isinstance(ov, list) and ov else None)
        break  # first series only
    return _to_series(periods, values)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_series(agency: str, flow: str, key: str) -> tuple[pd.Series, str]:
    """Download one monthly series. Returns (series, diagnostic message)."""
    errors: list[str] = []
    for version in ("+", "~"):
        url = f"{BASE_URL}/data/dataflow/{agency}/{flow}/{version}/{key}"
        for accept, parser in ((CSV_ACCEPT, _parse_csv), (JSON_ACCEPT, _parse_json)):
            try:
                r = requests.get(url, headers=_headers(accept), timeout=TIMEOUT)
            except requests.RequestException as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                continue
            if r.status_code == 404:
                errors.append(f"404 (no data) for {key}")
                continue
            if not r.ok:
                errors.append(f"HTTP {r.status_code} for {key}")
                continue
            try:
                s = parser(r.text)
            except Exception as exc:  # malformed / unexpected payload
                errors.append(f"parse error ({accept.split(';')[0]}): {exc}")
                continue
            if not s.empty:
                return s, "ok"
            errors.append(f"empty response for {key}")
    return pd.Series(dtype=float), "; ".join(dict.fromkeys(errors)) or "no data"


# ---------------------------------------------------------------------------
# Country list
# ---------------------------------------------------------------------------
def _name_of(code_obj: dict) -> str:
    name = code_obj.get("name")
    if isinstance(name, dict):
        name = name.get("en") or next(iter(name.values()), None)
    if not name:
        names = code_obj.get("names") or {}
        name = names.get("en") or next(iter(names.values()), None)
    return str(name or code_obj.get("id"))


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def load_countries() -> dict[str, str]:
    """Return {ISO3 code: name}. Tries the IMF codelist, falls back to pycountry."""
    countries: dict[str, str] = {}
    for agency in ("IMF", "IMF.STA"):
        url = f"{BASE_URL}/structure/codelist/{agency}/CL_COUNTRY/+"
        try:
            r = requests.get(url, headers=_headers(STRUCT_ACCEPT), timeout=TIMEOUT)
            if not r.ok:
                continue
            js = r.json()
            lists = js.get("data", js).get("codelists", [])
            for code in (lists[0].get("codes", []) if lists else []):
                cid = str(code.get("id", ""))
                if re.fullmatch(r"[A-Z]{3}", cid):
                    countries[cid] = _name_of(code)
            if countries:
                break
        except Exception:
            continue

    if not countries:
        try:
            import pycountry

            countries = {c.alpha_3: getattr(c, "common_name", None) or c.name
                         for c in pycountry.countries}
        except Exception:
            countries = {"USA": "United States", "GBR": "United Kingdom", "JPN": "Japan",
                         "CAN": "Canada", "CHN": "China", "DEU": "Germany",
                         "FRA": "France", "CHE": "Switzerland", "AUS": "Australia"}
    return dict(sorted(countries.items(), key=lambda kv: kv[1]))


# ---------------------------------------------------------------------------
# Data assembly and calculations
# ---------------------------------------------------------------------------
def get_exchange_rate(iso: str) -> tuple[pd.Series, str]:
    s, msg = fetch_series(*ER_FLOW, ER_KEY.format(iso=iso))
    if s.empty and iso == "USA":
        # USD per USD is identically 1.
        idx = pd.date_range(START_MONTH, pd.Timestamp.today().normalize(), freq="MS")
        return pd.Series(1.0, index=idx), "USD per USD set to 1"
    return s, msg


def build_frame(iso1: str, iso2: str) -> tuple[pd.DataFrame, dict[str, str]]:
    e1, m_e1 = get_exchange_rate(iso1)
    e2, m_e2 = get_exchange_rate(iso2)
    p1, m_p1 = fetch_series(*CPI_FLOW, CPI_KEY.format(iso=iso1))
    p2, m_p2 = fetch_series(*CPI_FLOW, CPI_KEY.format(iso=iso2))
    diag = {"E1": m_e1, "E2": m_e2, "P1": m_p1, "P2": m_p2}

    df = pd.concat({"E1": e1, "E2": e2, "P1": p1, "P2": p2}, axis=1).sort_index()
    if df.empty:
        return df, diag
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="MS")
    df = df.reindex(full_idx)
    df.index.name = "date"
    df["S"] = df["E2"] / df["E1"]                    # C2 per C1
    df["RER"] = df["S"] * df["P1"] / df["P2"]
    df["valid"] = np.isfinite(df["RER"]) & (df["RER"] > 0)
    return df, diag


def compute_sample(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, float]:
    w = df.loc[start:end].copy()
    valid = w.loc[w["valid"], "RER"]
    rer_star = float(valid.mean()) if not valid.empty else float("nan")
    w["RER_star"] = rer_star
    w["Real_Index"] = 100.0 * w["RER"] / rer_star if np.isfinite(rer_star) else np.nan
    return w, rer_star


def coverage(s: pd.Series) -> str:
    s = s.dropna()
    if s.empty:
        return "no data"
    return f"{s.index.min():%Y-%m} to {s.index.max():%Y-%m} ({len(s)} months)"


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
REAL_COLOR = "#1f5aa6"
NOM_COLOR = "#b5651d"


def make_chart(w: pd.DataFrame, view: str, nominal_label: str, log_nominal: bool) -> go.Figure:
    x = w.index
    real_trace = go.Scatter(x=x, y=w["Real_Index"], name="Real index (sample mean = 100)",
                            mode="lines", line=dict(color=REAL_COLOR, width=2), connectgaps=False,
                            hovertemplate="%{x|%Y-%m}<br>Real index: %{y:.2f}<extra></extra>")
    nom_trace = go.Scatter(x=x, y=w["S"], name=f"Nominal S(t): {nominal_label}",
                           mode="lines", line=dict(color=NOM_COLOR, width=2), connectgaps=False,
                           hovertemplate="%{x|%Y-%m}<br>S(t): %{y:,.6g}<extra></extra>")

    if view == "Both":
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(real_trace, secondary_y=False)
        fig.add_trace(nom_trace, secondary_y=True)
        fig.add_hline(y=100, line_dash="dot", line_color="grey", secondary_y=False)
        fig.update_yaxes(title_text="Real index (sample mean = 100)", secondary_y=False,
                         title_font_color=REAL_COLOR)
        fig.update_yaxes(title_text=nominal_label, secondary_y=True, showgrid=False,
                         type="log" if log_nominal else "linear", title_font_color=NOM_COLOR)
    elif view == "Real":
        fig = go.Figure(real_trace)
        fig.add_hline(y=100, line_dash="dot", line_color="grey")
        fig.update_yaxes(title_text="Real index (sample mean = 100)")
    else:
        fig = go.Figure(nom_trace)
        fig.update_yaxes(title_text=nominal_label, type="log" if log_nominal else "linear")

    fig.update_layout(height=520, hovermode="x unified", margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(rangeslider_visible=True)
    return fig


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Bilateral Real Exchange Rate (IMF)", layout="wide")
    st.title("Bilateral real exchange rate")
    st.caption("Monthly IMF CPI and exchange-rate data from January 1976 where available. "
               "S(t) = units of Country 2 currency per 1 unit of Country 1 currency; "
               "RER(t) = S(t) × P1(t) / P2(t).")

    with st.sidebar:
        st.header("Countries")
        with st.spinner("Loading country list..."):
            countries = load_countries()
        include_euro = st.checkbox("Include Euro area (G163)", value=True)
        if include_euro:
            countries = {EURO_AREA_CODE: EURO_AREA_NAME, **countries}
        codes = list(countries)
        fmt = lambda c: f"{countries[c]} ({c})"  # noqa: E731

        def default_index(code: str, fallback: int) -> int:
            return codes.index(code) if code in codes else fallback

        iso1 = st.selectbox("Country 1 (base currency)", codes,
                            index=default_index("USA", 0), format_func=fmt)
        iso2 = st.selectbox("Country 2 (quote currency)", codes,
                            index=default_index("JPN", min(1, len(codes) - 1)), format_func=fmt)

        if st.button("Refresh IMF data"):
            st.cache_data.clear()
            st.rerun()

    if iso1 == iso2:
        st.warning("Choose two different countries.")
        st.stop()

    name1, name2 = countries[iso1], countries[iso2]

    with st.spinner(f"Downloading IMF data for {name1} and {name2}..."):
        df, diag = build_frame(iso1, iso2)

    with st.expander("Data coverage", expanded=False):
        cov = pd.DataFrame({
            "Series": [f"E1: {name1} currency per USD", f"E2: {name2} currency per USD",
                       f"P1: {name1} CPI", f"P2: {name2} CPI"],
            "IMF key": [ER_KEY.format(iso=iso1), ER_KEY.format(iso=iso2),
                        CPI_KEY.format(iso=iso1), CPI_KEY.format(iso=iso2)],
            "Coverage": [coverage(df[c]) if c in df else "no data" for c in ("E1", "E2", "P1", "P2")],
            "Status": [diag[c] for c in ("E1", "E2", "P1", "P2")],
        })
        st.dataframe(cov, hide_index=True, use_container_width=True)

    missing = [c for c in ("E1", "E2", "P1", "P2") if c not in df or df[c].dropna().empty]
    if missing:
        st.error("The IMF returned no data for: " + ", ".join(missing) +
                 ". Try another country pair, or check the coverage table above.")
        st.stop()
    if not df["valid"].any():
        st.error("The four series never overlap, so RER(t) cannot be computed for this pair.")
        st.stop()

    # ---- Sample period -----------------------------------------------------
    valid_idx = df.index[df["valid"]]
    months = [d.strftime("%Y-%m") for d in df.index]
    default = (valid_idx.min().strftime("%Y-%m"), valid_idx.max().strftime("%Y-%m"))

    st.subheader("Sample period")
    start_s, end_s = st.select_slider("Start and end month", options=months, value=default)
    start, end = pd.Timestamp(start_s + "-01"), pd.Timestamp(end_s + "-01")

    w, rer_star = compute_sample(df, start, end)
    n_valid = int(w["valid"].sum())
    n_total = len(w)

    if n_valid == 0:
        st.error("No month in this sample has all four series. Widen the sample period.")
        st.stop()
    if n_valid < n_total:
        st.info(f"{n_total - n_valid} of {n_total} months in the sample have missing data; "
                f"RER* uses the {n_valid} valid months only.")

    last = w.loc[w["valid"]].iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RER* (sample mean)", f"{rer_star:,.6g}")
    c2.metric("Valid months", f"{n_valid} / {n_total}")
    c3.metric(f"Real index, {last.name:%Y-%m}", f"{last['Real_Index']:.2f}")
    c4.metric(f"S(t), {last.name:%Y-%m}", f"{last['S']:,.6g}")

    # ---- Chart ---------------------------------------------------------------
    nominal_label = f"{name2} currency per 1 {name1} currency"
    col_a, col_b = st.columns([3, 1])
    view = col_a.radio("Show", ["Real", "Nominal", "Both"], index=2, horizontal=True)
    log_nominal = col_b.checkbox("Log scale for nominal", value=False,
                                 disabled=(view == "Real"))
    st.plotly_chart(make_chart(w, view, nominal_label, log_nominal), use_container_width=True)
    st.caption("A rise in the real index means Country 1's currency has appreciated in real terms "
               f"against Country 2's ({name1} goods became relatively more expensive).")

    # ---- Table and CSV -------------------------------------------------------
    out = pd.DataFrame({
        "month": w.index.strftime("%Y-%m"),
        "country1": iso1,
        "country2": iso2,
        f"E1_{iso1}_LCU_per_USD": w["E1"],
        f"E2_{iso2}_LCU_per_USD": w["E2"],
        f"S_{iso2}_per_{iso1}": w["S"],
        f"P1_CPI_{iso1}": w["P1"],
        f"P2_CPI_{iso2}": w["P2"],
        "RER": w["RER"],
        "RER_star": w["RER_star"],
        "Real_Index": w["Real_Index"],
        "valid_obs": w["valid"],
        "sample_start": start_s,
        "sample_end": end_s,
    })

    st.download_button(
        "Download CSV for this sample",
        data=out.to_csv(index=False).encode("utf-8"),
        file_name=f"rer_{iso1}_{iso2}_{start_s}_{end_s}.csv",
        mime="text/csv",
    )
    with st.expander("Observations in the sample"):
        st.dataframe(out, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
