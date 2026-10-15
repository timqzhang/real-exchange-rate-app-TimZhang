"""Two-country real exchange rate: IMF SDMX 3.0 or a validated saved export."""
from __future__ import annotations

import math
import re
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Two-country real exchange rate", layout="wide")

# Static economy labels (ISO 3166-1 alpha-3, plus IMF area G163 and XKX).
COUNTRIES = {
    'Afghanistan': 'AFG',
    'Albania': 'ALB',
    'Algeria': 'DZA',
    'Andorra': 'AND',
    'Angola': 'AGO',
    'Antigua and Barbuda': 'ATG',
    'Argentina': 'ARG',
    'Armenia': 'ARM',
    'Aruba': 'ABW',
    'Australia': 'AUS',
    'Austria': 'AUT',
    'Azerbaijan': 'AZE',
    'Bahamas': 'BHS',
    'Bahrain': 'BHR',
    'Bangladesh': 'BGD',
    'Barbados': 'BRB',
    'Belarus': 'BLR',
    'Belgium': 'BEL',
    'Belize': 'BLZ',
    'Benin': 'BEN',
    'Bhutan': 'BTN',
    'Bolivia': 'BOL',
    'Bosnia and Herzegovina': 'BIH',
    'Botswana': 'BWA',
    'Brazil': 'BRA',
    'Brunei Darussalam': 'BRN',
    'Bulgaria': 'BGR',
    'Burkina Faso': 'BFA',
    'Burundi': 'BDI',
    'Cabo Verde': 'CPV',
    'Cambodia': 'KHM',
    'Cameroon': 'CMR',
    'Canada': 'CAN',
    'Central African Republic': 'CAF',
    'Chad': 'TCD',
    'Chile': 'CHL',
    'China': 'CHN',
    'Colombia': 'COL',
    'Comoros': 'COM',
    'Congo, Democratic Republic of': 'COD',
    'Congo, Republic of': 'COG',
    'Costa Rica': 'CRI',
    'Croatia': 'HRV',
    'Curaçao': 'CUW',
    'Cyprus': 'CYP',
    'Czechia': 'CZE',
    'Côte d’Ivoire': 'CIV',
    'Denmark': 'DNK',
    'Djibouti': 'DJI',
    'Dominica': 'DMA',
    'Dominican Republic': 'DOM',
    'Ecuador': 'ECU',
    'Egypt': 'EGY',
    'El Salvador': 'SLV',
    'Equatorial Guinea': 'GNQ',
    'Eritrea': 'ERI',
    'Estonia': 'EST',
    'Eswatini': 'SWZ',
    'Ethiopia': 'ETH',
    'Fiji': 'FJI',
    'Finland': 'FIN',
    'France': 'FRA',
    'Gabon': 'GAB',
    'Gambia': 'GMB',
    'Georgia': 'GEO',
    'Germany': 'DEU',
    'Ghana': 'GHA',
    'Greece': 'GRC',
    'Grenada': 'GRD',
    'Guatemala': 'GTM',
    'Guinea': 'GIN',
    'Guinea-Bissau': 'GNB',
    'Guyana': 'GUY',
    'Haiti': 'HTI',
    'Honduras': 'HND',
    'Hong Kong': 'HKG',
    'Hungary': 'HUN',
    'Iceland': 'ISL',
    'India': 'IND',
    'Indonesia': 'IDN',
    'Iran': 'IRN',
    'Iraq': 'IRQ',
    'Ireland': 'IRL',
    'Israel': 'ISR',
    'Italy': 'ITA',
    'Jamaica': 'JAM',
    'Japan': 'JPN',
    'Jordan': 'JOR',
    'Kazakhstan': 'KAZ',
    'Kenya': 'KEN',
    'Kiribati': 'KIR',
    'Korea, Republic of': 'KOR',
    'Kosovo': 'XKX',
    'Kuwait': 'KWT',
    'Kyrgyzstan': 'KGZ',
    'Lao P.D.R.': 'LAO',
    'Latvia': 'LVA',
    'Lebanon': 'LBN',
    'Lesotho': 'LSO',
    'Liberia': 'LBR',
    'Libya': 'LBY',
    'Lithuania': 'LTU',
    'Luxembourg': 'LUX',
    'Macao': 'MAC',
    'Madagascar': 'MDG',
    'Malawi': 'MWI',
    'Malaysia': 'MYS',
    'Maldives': 'MDV',
    'Mali': 'MLI',
    'Malta': 'MLT',
    'Marshall Islands': 'MHL',
    'Mauritania': 'MRT',
    'Mauritius': 'MUS',
    'Mexico': 'MEX',
    'Micronesia': 'FSM',
    'Moldova': 'MDA',
    'Mongolia': 'MNG',
    'Montenegro': 'MNE',
    'Morocco': 'MAR',
    'Mozambique': 'MOZ',
    'Myanmar': 'MMR',
    'Namibia': 'NAM',
    'Nauru': 'NRU',
    'Nepal': 'NPL',
    'Netherlands': 'NLD',
    'New Zealand': 'NZL',
    'Nicaragua': 'NIC',
    'Niger': 'NER',
    'Nigeria': 'NGA',
    'North Macedonia': 'MKD',
    'Norway': 'NOR',
    'Oman': 'OMN',
    'Pakistan': 'PAK',
    'Palau': 'PLW',
    'Palestine, State of': 'PSE',
    'Panama': 'PAN',
    'Papua New Guinea': 'PNG',
    'Paraguay': 'PRY',
    'Peru': 'PER',
    'Philippines': 'PHL',
    'Poland': 'POL',
    'Portugal': 'PRT',
    'Qatar': 'QAT',
    'Romania': 'ROU',
    'Russia': 'RUS',
    'Rwanda': 'RWA',
    'Samoa': 'WSM',
    'San Marino': 'SMR',
    'Sao Tome and Principe': 'STP',
    'Saudi Arabia': 'SAU',
    'Senegal': 'SEN',
    'Serbia': 'SRB',
    'Seychelles': 'SYC',
    'Sierra Leone': 'SLE',
    'Singapore': 'SGP',
    'Sint Maarten (Dutch part)': 'SXM',
    'Slovakia': 'SVK',
    'Slovenia': 'SVN',
    'Solomon Islands': 'SLB',
    'Somalia': 'SOM',
    'South Africa': 'ZAF',
    'South Sudan': 'SSD',
    'Spain': 'ESP',
    'Sri Lanka': 'LKA',
    'St. Kitts and Nevis': 'KNA',
    'St. Lucia': 'LCA',
    'St. Vincent and the Grenadines': 'VCT',
    'Sudan': 'SDN',
    'Suriname': 'SUR',
    'Sweden': 'SWE',
    'Switzerland': 'CHE',
    'Syrian Arab Republic': 'SYR',
    'Taiwan, Province of China': 'TWN',
    'Tajikistan': 'TJK',
    'Tanzania': 'TZA',
    'Thailand': 'THA',
    'Timor-Leste': 'TLS',
    'Togo': 'TGO',
    'Tonga': 'TON',
    'Trinidad and Tobago': 'TTO',
    'Tunisia': 'TUN',
    'Turkmenistan': 'TKM',
    'Tuvalu': 'TUV',
    'Türkiye': 'TUR',
    'Uganda': 'UGA',
    'Ukraine': 'UKR',
    'United Arab Emirates': 'ARE',
    'United Kingdom': 'GBR',
    'United States': 'USA',
    'Uruguay': 'URY',
    'Uzbekistan': 'UZB',
    'Vanuatu': 'VUT',
    'Venezuela': 'VEN',
    'Vietnam': 'VNM',
    'Yemen': 'YEM',
    'Zambia': 'ZMB',
    'Zimbabwe': 'ZWE',
    'Euro area': 'G163',
}
CODE_TO_NAME = {code: name for name, code in COUNTRIES.items()}
EURO_START = {
    **dict.fromkeys('AUT BEL DEU ESP FIN FRA IRL ITA LUX NLD PRT'.split(), '1999-01'),
    'GRC': '2001-01', 'SVN': '2007-01', 'CYP': '2008-01',
    'MLT': '2008-01', 'SVK': '2009-01', 'EST': '2011-01',
    'LVA': '2014-01', 'LTU': '2015-01', 'HRV': '2023-01',
    'BGR': '2026-01',
}
START = pd.Period('1976-01', freq='M')
BASE_URL = 'https://api.imf.org/external/sdmx/3.0'
REQUIRED = ['month', 'numerator_country', 'denominator_country',
            'cpi_numerator', 'cpi_denominator', 'fx_numerator_per_usd',
            'fx_denominator_per_usd']


class DataError(Exception):
    """User-actionable IMF or uploaded-data failure."""


def month_period(x):
    if not isinstance(x, str):
        raise DataError(f'Invalid month: {x!r}')
    value = x.strip()
    match = re.fullmatch(r'(\d{4})-(?:M)?(0[1-9]|1[0-2])', value)
    if not match:
        raise DataError(f'Invalid monthly date {x!r}; expected YYYY-MM or YYYY-MMM.')
    return pd.Period(f'{match.group(1)}-{match.group(2)}', freq='M')


def latest_allowed_month():
    now = datetime.now(timezone.utc)
    return pd.Period(year=now.year, month=now.month, freq='M') - 1


def dimensions(structure, level):
    dims = structure.get('dimensions', {}).get(level, [])
    if not isinstance(dims, list):
        raise DataError(f'Unexpected SDMX {level} dimensions.')
    return sorted(dims, key=lambda x: x.get('keyPosition', 0)) if level == 'series' else dims


def decode_key(raw, dims):
    parts = str(raw).split(':')
    if len(parts) != len(dims):
        raise DataError('SDMX series key has the wrong number of dimensions.')
    result = {}
    for part, dim in zip(parts, dims):
        values = dim.get('values', [])
        try:
            value = values[int(part)]
            result[dim['id']] = str(value.get('id', value.get('value')))
        except (TypeError, ValueError, IndexError, KeyError) as exc:
            raise DataError('Invalid SDMX series dimension index.') from exc
    return result


def decode_attributes(raw, definitions):
    result = {}
    if raw is None:
        return result
    if not isinstance(raw, list):
        raise DataError('Unexpected SDMX attributes.')
    for definition, value in zip(definitions, raw):
        if value is None:
            continue
        if isinstance(value, int) and not isinstance(value, bool) and definition.get('values'):
            try:
                item = definition['values'][value]
                value = item.get('id', item.get('value'))
            except (IndexError, TypeError) as exc:
                raise DataError('Invalid SDMX attribute index.') from exc
        result[definition['id']] = str(value)
    return result


def parse_sdmx(payload, flow, key):
    try:
        body = payload['data']
        data_sets = body['dataSets']
        structures = body['structures']
        if not isinstance(data_sets, list) or not isinstance(structures, list):
            raise ValueError('non-list datasets or structures')
        found = []
        for data_set in data_sets:
            reference = data_set['structure']
            if isinstance(reference, int):
                structure = structures[reference]
            elif isinstance(reference, str) and reference.isdigit():
                structure = structures[int(reference)]
            else:
                raise DataError('Unknown SDMX dataset structure reference.')
            series_dims = dimensions(structure, 'series')
            obs_dims = dimensions(structure, 'observation')
            if len(obs_dims) != 1 or obs_dims[0].get('id') != 'TIME_PERIOD':
                raise DataError('Expected one TIME_PERIOD observation dimension.')
            expected_ids = (['COUNTRY', 'INDEX_TYPE', 'COICOP_1999',
                             'TYPE_OF_TRANSFORMATION', 'FREQUENCY'] if flow == 'CPI'
                            else ['COUNTRY', 'INDICATOR', 'TYPE_OF_TRANSFORMATION', 'FREQUENCY'])
            if [d.get('id') for d in series_dims] != expected_ids:
                raise DataError('IMF returned unexpected series dimensions.')
            series = data_set.get('series', {})
            if not isinstance(series, dict):
                raise DataError('Unexpected SDMX series container.')
            for raw_key, series_data in series.items():
                actual = decode_key(raw_key, series_dims)
                expected = dict(zip(expected_ids, key.split('.')))
                if actual != expected:
                    raise DataError(f'IMF returned different indicators: {actual!r}')
                found.append((series_data, structure, obs_dims[0], data_set))
        if len(found) != 1:
            raise DataError(f'Expected exactly one series for {key}; found {len(found)}.')
        series_data, structure, time_dim, data_set = found[0]
        defs = structure.get('attributes', {})
        s_attrs = decode_attributes(series_data.get('attributes'), defs.get('series', []))
        d_attrs = decode_attributes(data_set.get('attributes'), defs.get('dataSet', []))
        common_attrs = {**d_attrs, **s_attrs}
        try:
            scale = int(common_attrs.get('SCALE', 0))
        except (TypeError, ValueError) as exc:
            raise DataError('Invalid IMF SCALE attribute.') from exc
        if abs(scale) > 100:
            raise DataError('Unreasonable IMF SCALE exponent.')
        obs_defs = defs.get('observation', [])
        observations = series_data.get('observations', {})
        if not isinstance(observations, dict) or not observations:
            raise DataError(f'No monthly observations in {flow}: {key}.')
        rows = []
        for raw_idx, obs in observations.items():
            try:
                month_item = time_dim['values'][int(raw_idx)]
                month = month_period(str(month_item.get('value', month_item.get('id'))))
                if not isinstance(obs, list) or not obs:
                    raise ValueError('observation not an array')
                number = float(obs[0]) if obs[0] is not None else math.nan
                attrs = decode_attributes(obs[1:], obs_defs)
                status = attrs.get('STATUS', common_attrs.get('STATUS', ''))
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                raise DataError(f'Malformed observation in {key}.') from exc
            if START <= month <= latest_allowed_month() and math.isfinite(number) and number > 0:
                scaled = number * (10 ** scale)
                if math.isfinite(scaled) and scaled > 0:
                    rows.append({'month': month, 'value': scaled, 'status': status})
        result = pd.DataFrame(rows, columns=['month', 'value', 'status'])
        if result.empty:
            raise DataError(f'{key} has no valid positive monthly observations since 1976.')
        if result['month'].duplicated().any():
            raise DataError(f'Duplicate IMF months in {key}.')
        return result.sort_values('month').reset_index(drop=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise DataError(f'Unexpected IMF SDMX-JSON structure for {key}: {exc}') from exc


@st.cache_data(ttl=3600, show_spinner=False)
def download_series(flow, key, api_key):
    url = f'{BASE_URL}/data/dataflow/IMF.STA/{flow}/+/{key}'
    headers = {'Accept': 'application/vnd.sdmx.data+json;version=2.0.0'}
    if api_key:
        headers['Ocp-Apim-Subscription-Key'] = api_key
    for attempt in range(3):
        try:
            reply = requests.get(url, params={'startPeriod': '1976-01'},
                                 headers=headers, timeout=(10, 40))
            if reply.status_code in (401, 403):
                raise DataError('IMF authentication/access denied. Check the owner-managed API key.')
            if reply.status_code == 404:
                raise DataError(f'{key}: IMF 404—series unavailable or access restricted.')
            if reply.status_code == 429 or 500 <= reply.status_code < 600:
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                raise DataError(f'IMF temporarily unavailable (HTTP {reply.status_code}) for {key}.')
            if not reply.ok:
                raise DataError(f'IMF HTTP {reply.status_code} for {key}.')
            if 'json' not in reply.headers.get('Content-Type', '').lower():
                raise DataError(f'IMF returned non-JSON content for {key}.')
            try:
                payload = reply.json()
            except ValueError as exc:
                raise DataError(f'IMF returned malformed JSON for {key}.') from exc
            frame = parse_sdmx(payload, flow, key)
            return frame, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 2:
                raise DataError(f'Cannot reach IMF for {key} after three attempts: {exc}') from exc
            time.sleep(attempt + 1)
    raise DataError(f'Unable to download {key}.')


def imf_key(code, flow):
    if flow == 'CPI':
        return f'{code}.HICP._T.IX.M' if code == 'G163' else f'{code}.CPI._T.IX.M'
    return f'{code}.XDC_USD.PA_RT.M'


def maybe_estimate_us_cpi(frame):
    target = pd.Period('2025-10', freq='M')
    if target in set(frame['month']):
        return frame, False
    lookup = frame.set_index('month')['value']
    before, after = target - 1, target + 1
    if before in lookup.index and after in lookup.index:
        extra = pd.DataFrame([{'month': target,
                               'value': (lookup[before] + lookup[after]) / 2,
                               'status': 'ESTIMATED_ADJACENT_MONTHS'}])
        return pd.concat([frame, extra], ignore_index=True).sort_values('month'), True
    return frame, False


def currency(code):
    return 'EUR' if code == 'G163' or code in EURO_START else ('USD' if code == 'USA' else code)


def get_live_pair(n, d, estimate_us, api_key):
    if n == d:
        raise DataError('Select two different countries/areas.')
    frames, provenance = {}, []
    codes = list(dict.fromkeys([n, d]))
    for code in codes:
        key = imf_key(code, 'CPI')
        frame, downloaded = download_series('CPI', key, api_key)
        if code == 'USA' and estimate_us:
            frame, inserted = maybe_estimate_us_cpi(frame)
            if inserted:
                st.info('Estimated missing U.S. CPI for 2025-10 from observed 2025-09 and 2025-11.')
        frames[(code, 'cpi')] = frame
        provenance.append((key, downloaded))
    for code in codes:
        rate_code = 'G163' if code in EURO_START else code
        if rate_code == 'USA':
            provenance.append(('USA: USD/USD = 1 (definition; no ER request)', 'not downloaded'))
            continue
        token = (rate_code, 'fx')
        if token not in frames:
            key = imf_key(rate_code, 'ER')
            frames[token], downloaded = download_series('ER', key, api_key)
            provenance.append((key, downloaded))
    frame = None
    for side, code in [('numerator', n), ('denominator', d)]:
        p = frames[(code, 'cpi')].rename(columns={
            'value': f'cpi_{side}', 'status': f'cpi_{side}_status'})
        if frame is None:
            frame = p
        else:
            frame = frame.merge(p, on='month', how='inner')
        rate_code = 'G163' if code in EURO_START else code
        if rate_code == 'USA':
            fx = pd.DataFrame({'month': frame['month'].copy(),
                               f'fx_{side}_per_usd': 1.0,
                               f'fx_{side}_status': 'DEFINITION'})
        else:
            fx = frames[(rate_code, 'fx')].rename(columns={
                'value': f'fx_{side}_per_usd', 'status': f'fx_{side}_status'})
        frame = frame.merge(fx, on='month', how='inner')
        if code == 'G163' or code in EURO_START:
            first = pd.Period('1999-01', freq='M') if code == 'G163' else pd.Period(EURO_START[code], freq='M')
            frame = frame.loc[frame['month'] >= first].copy()
    if frame.empty:
        raise DataError('No common valid monthly CPI and exchange-rate observations.')
    for side, code in [('numerator', n), ('denominator', d)]:
        frame[f'cpi_{side}_estimated'] = ((code == 'USA') & (frame['month'] == pd.Period('2025-10', freq='M')) &
                                         (frame[f'cpi_{side}_status'] == 'ESTIMATED_ADJACENT_MONTHS'))
        frame[f'cpi_{side}_series'] = imf_key(code, 'CPI')
    frame['numerator_country'] = n
    frame['denominator_country'] = d
    return frame.sort_values('month').reset_index(drop=True), provenance


def bool_column(values, label):
    mapping = {'true': True, 'false': False, '1': True, '0': False}
    result = values.astype('string').str.strip().str.lower().map(mapping)
    if result.isna().any():
        raise DataError(f'{label} must contain only true/false (or 1/0).')
    return result.astype(bool)


def load_saved(upload):
    try:
        data = pd.read_csv(upload, dtype={'month': str, 'numerator_country': str,
                                          'denominator_country': str})
    except Exception as exc:
        raise DataError(f'Cannot read saved CSV: {exc}') from exc
    missing = [c for c in REQUIRED if c not in data.columns]
    if missing:
        raise DataError('Saved export lacks required columns: ' + ', '.join(missing))
    if data.empty:
        raise DataError('Saved CSV has no rows.')
    for side in ('numerator', 'denominator'):
        key = f'{side}_country'
        choices = data[key].dropna().str.strip().unique().tolist()
        if len(choices) != 1 or choices[0] not in CODE_TO_NAME:
            raise DataError(f'{key} must contain one recognized IMF ISO3/area code.')
        data[key] = choices[0]
    if data['numerator_country'].iloc[0] == data['denominator_country'].iloc[0]:
        raise DataError('Saved countries must be different.')
    data['month'] = data['month'].apply(month_period)
    if data['month'].duplicated().any():
        raise DataError('Saved CSV has duplicate months.')
    if ((data['month'] < START) | (data['month'] > latest_allowed_month())).any():
        raise DataError('Saved CSV has months outside the permitted historical range.')
    for name in REQUIRED[3:]:
        data[name] = pd.to_numeric(data[name], errors='coerce')
        if not data[name].apply(lambda x: math.isfinite(x) and x > 0).all():
            raise DataError(f'{name} must be finite and strictly positive in every row.')
    for side in ('numerator', 'denominator'):
        flag = f'cpi_{side}_estimated'
        data[flag] = bool_column(data[flag], flag) if flag in data else False
        for optional in (f'cpi_{side}_status', f'fx_{side}_status'):
            if optional not in data:
                data[optional] = ''
        series = f'cpi_{side}_series'
        if series not in data:
            data[series] = imf_key(data[f'{side}_country'].iloc[0], 'CPI')
    return data.sort_values('month').reset_index(drop=True)


def compute_sample(source, start, end):
    """Restrict first, then compute raw RER and normalize on selected arithmetic mean."""
    selected = source.loc[source['month'].between(start, end)].copy()
    if selected.empty:
        raise DataError('No observations in the chosen analysis sample.')
    selected['S_denominator_per_numerator'] = (selected['fx_denominator_per_usd'] /
                                                 selected['fx_numerator_per_usd'])
    selected['RER'] = (selected['S_denominator_per_numerator'] * selected['cpi_numerator'] /
                       selected['cpi_denominator'])
    if not selected['RER'].apply(lambda x: math.isfinite(x) and x > 0).all():
        raise DataError('Computed RER contains invalid values.')
    mean = selected['RER'].mean()
    selected['rer_sample_mean'] = mean
    selected['real_index'] = 100 * selected['RER'] / mean
    selected['analysis_sample_start'] = str(start)
    selected['analysis_sample_end'] = str(end)
    n, d = selected.iloc[0][['numerator_country', 'denominator_country']]
    selected['nominal_units'] = f'{currency(d)} per {currency(n)}'
    selected['month'] = selected['month'].astype(str)
    return selected


def graph(data, mode, n, d):
    units = data['nominal_units'].iloc[0]
    fig = go.Figure()
    dates = pd.to_datetime(data['month'] + '-01')
    if mode in ('Real', 'Both'):
        fig.add_trace(go.Scatter(x=dates, y=data['real_index'], name='Real (mean = 100)',
                                 line=dict(color='#d62728', width=2), connectgaps=False,
                                 yaxis='y'))
    if mode in ('Nominal', 'Both'):
        fig.add_trace(go.Scatter(x=dates, y=data['S_denominator_per_numerator'],
                                 name=f'Nominal ({units})', line=dict(color='#1f77b4', width=2),
                                 connectgaps=False, yaxis='y2' if mode == 'Both' else 'y'))
    yaxis = dict(title='Real exchange rate index (sample mean = 100)' if mode != 'Nominal'
                 else f'Nominal exchange rate ({units})', showgrid=True)
    layout = dict(template='plotly_white', xaxis_title='Month', yaxis=yaxis,
                  title=f'{CODE_TO_NAME[n]} / {CODE_TO_NAME[d]}', hovermode='x unified',
                  legend=dict(orientation='h', y=1.1), margin=dict(t=85, b=45))
    if mode == 'Both':
        layout['yaxis2'] = dict(title=f'Nominal exchange rate ({units})',
                                overlaying='y', side='right', showgrid=False)
    fig.update_layout(**layout)
    # The benchmark always belongs to the REAL axis, never the nominal axis.
    if mode in ('Real', 'Both'):
        fig.add_hline(y=100, line_color='#d62728', line_dash='dot', opacity=.65)
    return fig


def make_continuous_line_data(sample):
    """Make absent calendar months appear as gaps without adding them to the export."""
    series = sample.copy()
    series['month'] = pd.PeriodIndex(series['month'], freq='M')
    full = pd.period_range(series['month'].min(), series['month'].max(), freq='M')
    return series.set_index('month').reindex(full).rename_axis('month').reset_index().assign(
        month=lambda x: x['month'].astype(str))


st.title('Two-country real exchange rate')
st.latex(r'S_t=\frac{q_{D,t}}{q_{N,t}},\qquad RER_t=S_t\frac{P_{N,t}}{P_{D,t}}')
st.caption('N is the numerator country and D the denominator country. q is local-currency units '
           'per USD; S is D-currency units per one N-currency unit. An increase in RER means '
           'real appreciation of N relative to D.')

source_choice = st.radio('Data source', ['Live IMF data', 'Saved CSV export'], horizontal=True)
try:
    api_key = st.secrets.get('IMF_API_KEY', '')
except Exception:
    api_key = ''

if source_choice == 'Live IMF data':
    with st.form('countries'):
        names = sorted(COUNTRIES)
        n_name = st.selectbox('Country 1 (numerator N)', names,
                              index=names.index('United Kingdom'))
        d_name = st.selectbox('Country 2 (denominator D)', names,
                              index=names.index('United States'))
        estimate = st.checkbox('Estimate missing October 2025 U.S. CPI from adjacent months', value=True)
        fetch = st.form_submit_button('Fetch data and plot', type='primary')
    if st.button('Refresh data', help='Clear only cached IMF downloads, then fetch again.'):
        download_series.clear()
        st.session_state.pop('loaded_live', None)
        st.info('IMF download cache cleared. Click “Fetch data and plot” to request new data.')
    if fetch:
        n, d = COUNTRIES[n_name], COUNTRIES[d_name]
        if n == d:
            st.error('Choose two different economies.')
        else:
            try:
                with st.spinner('Downloading and validating monthly IMF data...'):
                    st.session_state['loaded_live'] = (get_live_pair(n, d, estimate, api_key), (n, d, estimate))
            except DataError as exc:
                st.session_state.pop('loaded_live', None)
                st.error(str(exc))
    stored = st.session_state.get('loaded_live')
    if not stored:
        st.info('Choose two countries and click “Fetch data and plot”. Not every economy has monthly CPI and ER data.')
        st.stop()
    (raw, provenance), (n, d, _) = stored
    st.caption('Source: live IMF API download (possibly cached for up to one hour).')
    with st.expander('Exact IMF source series and download timestamps (UTC)'):
        for label, downloaded in provenance:
            st.write(f'`{label}` — {downloaded}')
else:
    uploaded = st.file_uploader('Upload a saved RER CSV export (including instructor snapshot)', type=['csv'])
    if uploaded is None:
        st.info('Upload a saved CSV export. Saved mode never contacts IMF.')
        st.stop()
    try:
        raw = load_saved(uploaded)
    except DataError as exc:
        st.error(str(exc))
        st.stop()
    n, d = raw['numerator_country'].iloc[0], raw['denominator_country'].iloc[0]
    st.caption('Source: uploaded saved export, NOT a live update. Stored calculated columns are ignored.')

minimum, maximum = raw['month'].min(), raw['month'].max()
if minimum > maximum:
    st.error('No usable date coverage.')
    st.stop()
if n == 'G163' or d == 'G163' or n in EURO_START or d in EURO_START:
    st.info('Euro data use G163 euro/USD exchange rates. National CPI is retained for each euro '
            'member only from its euro adoption; Euro area uses aggregate HICP (available history may '
            'begin in 1999-12). Pre-adoption national currency months are excluded.')
st.write(f'**Available common coverage:** {minimum} to {maximum}; **{len(raw)} valid months** '
         '(missing calendar months are not filled).')
if n == 'G163' or d == 'G163':
    st.caption('Euro area CPI measure: harmonised index of consumer prices (HICP).')

# A single two-handled date bar; timestamps are used to keep the slider month-based.
# Use first-of-month dates, which the Streamlit range slider supports natively.
all_months = pd.period_range(minimum, maximum, freq='M')
if len(all_months) == 1:
    start_month = end_month = minimum
    st.caption(f'Analysis sample (start and end months): {minimum} (only one available month)')
else:
    left, right = st.select_slider(
        'Analysis sample (start and end months)',
        options=list(all_months), value=(minimum, maximum),
        format_func=lambda p: str(p), key=f'sample_{source_choice}_{n}_{d}_{minimum}_{maximum}')
    start_month, end_month = left, right
try:
    result = compute_sample(raw, start_month, end_month)
except DataError as exc:
    st.error(str(exc))
    st.stop()

st.write(f'**Selected averaging period:** {start_month} to {end_month}; '
         f'**{len(result)} observed months**. Normalized real-index average = '
         f'**{result["real_index"].mean():.6f}**.')
st.caption(f'Nominal S is expressed as **{result["nominal_units"].iloc[0]}**, in actual currency '
           'units; it is not rebased. A real index of 110 is 10% above the selected-period '
           'average; it does not establish overvaluation. Different CPI reference years cancel '
           'after real-index normalization, but different CPI baskets remain important.')
st.caption('Dividing two period-average USD rates approximates the average daily bilateral rate. '
           'Currency redenominations and statistical breaks outside the documented euro changeovers '
           'are not automatically repaired.')

if 'display_mode' not in st.session_state:
    st.session_state['display_mode'] = 'Both'
cols = st.columns(3)
for col, mode in zip(cols, ('Real', 'Nominal', 'Both')):
    if col.button(mode, type='primary' if st.session_state['display_mode'] == mode else 'secondary',
                  use_container_width=True):
        st.session_state['display_mode'] = mode
        st.rerun()
st.plotly_chart(graph(make_continuous_line_data(result), st.session_state['display_mode'], n, d),
                use_container_width=True)

columns = ['month', 'numerator_country', 'denominator_country', 'cpi_numerator',
           'cpi_denominator', 'fx_numerator_per_usd', 'fx_denominator_per_usd',
           'S_denominator_per_numerator', 'RER', 'real_index', 'rer_sample_mean',
           'analysis_sample_start', 'analysis_sample_end', 'nominal_units',
           'cpi_numerator_estimated', 'cpi_denominator_estimated']
columns += [x for x in ('cpi_numerator_series', 'cpi_denominator_series',
                         'cpi_numerator_status', 'cpi_denominator_status',
                         'fx_numerator_status', 'fx_denominator_status') if x in result.columns]
st.subheader('Selected-sample data')
st.dataframe(result[columns], use_container_width=True, hide_index=True)
st.download_button('Download selected sample as CSV',
                   data=result[columns].to_csv(index=False).encode('utf-8'),
                   file_name=f'IMF_RER_{n}_{d}_{start_month}_{end_month}.csv',
                   mime='text/csv')
