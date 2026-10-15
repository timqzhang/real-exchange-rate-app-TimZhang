# Two-country real exchange rate

A beginner-friendly Streamlit app written for **Python 3.12**. It compares the CPI-adjusted exchange rate of two IMF economies (including the Euro area), using monthly data from **1976-01 where available**. No local installation is necessary for visitors.

## Deploy entirely in your browser

1. Create a public or private GitHub repository and add **`app.py`**, **`requirements.txt`**, and **`README.md`** at its root.
2. On [Streamlit Community Cloud](https://share.streamlit.io/), sign in with GitHub, choose **Create app**, select the repository, branch, and `app.py`, and deploy.
3. Under **Advanced settings**, choose **Python 3.12** (if offered; verify the app's deployment environment uses Python 3.12). The platform installs the four dependencies automatically.
4. A site owner with an IMF subscription key may optionally set this secret via app settings (never commit it to GitHub):

   ```toml
   IMF_API_KEY = "YOUR_PRIVATE_KEY"
   ```

   Users never need to supply a key. Some IMF series or endpoints might still be restricted or temporarily unavailable.

## Use the app

Choose **Live IMF data**, search for *Country 1 (numerator)* and *Country 2 (denominator)*, and press **Fetch data and plot**. The default pair is United Kingdom / United States. Identical pairs are rejected. For a saved export instead, select **Saved CSV export** and upload its `.csv` file. Upload mode never requests IMF data; its country codes determine the pair. The instructor's `IMF_UK_US_1976_snapshot.csv` can be uploaded if it has the required raw-input columns.

The sole date-range control, **Analysis sample (start and end months)**, selects an inclusive start and end month. Its default is the complete available overlap. **Real**, **Nominal**, and **Both** are plot buttons; changing them never refetches data. In Both mode, the real index uses the left axis and the nominal exchange rate uses the right. Missing months remain gaps, not interpolated lines. **Download selected sample as CSV** exports *all valid observed months* in the chosen sample irrespective of plot visibility.

## Definition and units

Let `q_N` and `q_D` be units of numerator and denominator currencies, respectively, per **one U.S. dollar**. Let `P_N`, `P_D` denote their CPI index levels (Euro area: aggregate HICP).

- **Nominal:** `S = q_D / q_N`: denominator-currency units per numerator-currency unit. United Kingdom / United States has `S = 1 / (GBP per USD)`, in **USD per GBP**.
- **Raw real rate:** `RER = S * P_N / P_D`. A higher RER represents **real appreciation of the numerator** relative to the denominator.
- **Selected-sample index:** first retain only the months between the chosen handles, then compute `mean_RER` as the *arithmetic mean* of valid raw RER observations in that sample, and `real_index = 100 * RER / mean_RER`. Its selected-sample mean is exactly 100 (apart from floating-point rounding). A reading of 110 means 10% above this sample's mean, **not** necessarily overvaluation.

The **nominal line is never normalized**. Its unit is the actual currency pair. Dividing two monthly *period-average* U.S.-dollar exchange rates approximates, but generally does not equal, the average of daily bilateral exchange rates. Different CPI base years cancel after normalization; different CPI baskets do not.

## IMF data coverage and transformations

The app calls the active IMF SDMX 3.0 endpoint (`https://api.imf.org/external/sdmx/3.0`), using IMF.STA **CPI** and **ER** monthly series, with `startPeriod=1976-01`, where available. The exact keys and retrieval timestamps appear in an expander. National CPI uses `{ISO3}.CPI._T.IX.M`; Euro area uses `G163.HICP._T.IX.M`. Period-average local units per U.S. dollar use `{ISO3}.XDC_USD.PA_RT.M`. For the U.S., USD/USD is 1 and does not require a download.

For euro-adopting members, the app combines each member's *national CPI* with the **G163 euro exchange rate** only after euro adoption; it excludes legacy-currency periods rather than stitching inconsistent units. Euro area aggregate data are excluded before January 1999; the IMF HICP series may start later, such as December 1999. Two euro members have a nominal rate of 1 EUR per EUR. Other redenominations/statistical discontinuities are not automatically repaired.

Series are filtered to valid positive finite monthly observations from January 1976 through the **previous UTC month**, then intersected on calendar month. Missing observations are not filled. The sole optional exception is a checked-by-default estimate of **missing U.S. October 2025 CPI**, from the observed September and November mean. An observed October entry is never overwritten; the estimate is labeled and exported. Individual IMF release dates and country availability vary, so 1976 is not guaranteed for a particular pair.

## Data source, caching, and offline use

Successful IMF downloads are cached for **one hour** per series. **Refresh data** clears only the IMF download cache; then click **Fetch data and plot** to request new series. Connection and read timeouts are 10 and 40 seconds, respectively, with up to three attempts for temporary network/server failures. No arbitrary fake observations, automatic stale-data fallback, or silent missing-value interpolation are used. IMF access errors, missing monthly data, unavailable series (including some 404 errors), malformed responses, and invalid CSVs are displayed explicitly.

Download a CSV while the live app is working, then upload it later via **Saved CSV export**. The upload must include `month`, `numerator_country`, `denominator_country`, `cpi_numerator`, `cpi_denominator`, `fx_numerator_per_usd`, and `fx_denominator_per_usd`. Countries must be known IMF ISO3/area codes and constant throughout the file; all four input data columns must be positive and finite. Months must be unique YYYY-MM strings in the allowed historical range. The app validates any included `cpi_numerator_estimated` / `cpi_denominator_estimated` flags as booleans (true/false or 1/0). Older exports with `base_month` or `nominal_index` are accepted and those outdated derived fields ignored. Optional CPI/HICP series identifiers and status flags are preserved when present. **All nominal/real rates and the RER normalization are always recalculated from raw inputs**, never copied from an older export.

## Quick verification checklist

Live IMF access **could not be tested** in the authoring environment (DNS requests were unavailable); do not assume any particular actual start/end date until you run the deployed app. Verify:

1. Fetch **United Kingdom / United States** and inspect a month: `S = 1 / q_GBR` in USD per GBP. Check the actual first/last common month and count.
2. Fetch **Euro area / United States**, verify it uses **HICP** and the `G163` euro exchange rate, and note its actual overlap.
3. Reverse a country pair. The raw nominal rate and RER become reciprocals on overlapping months; the independently normalized real indexes need **not** multiply to 10,000.
4. Shorten the sample with the date-range bar. Earlier rows disappear from table and export, the new mean real index stays **100**, and nominal rates of remaining months do not change.
5. **Real** has one red indexed series and a 100 benchmark. **Nominal** has one blue actual-unit series and no benchmark. **Both** has both lines on separate axes with the 100 line only on the real axis.
6. Compare two euro members after adoption. Their nominal rate is **1**, not 100. Confirm download matches selected-sample rows, not only plotted lines.
7. If U.S. October 2025 CPI is absent and both neighbors exist, toggle the estimate and check the CSV flags; if an October observation exists, verify it is **never** overwritten.
8. Upload a saved export and confirm no network fetch is attempted. Try a duplicate month, invalid country code, negative CPI, and invalid estimated flag; each should show a clear error.

Only the four libraries in `requirements.txt` and Python's standard library are needed at runtime.
