import requests
import pandas as pd
import re
from io import StringIO

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_number(value):
    """Очистка числового значения"""
    if pd.isna(value) or value == '':
        return None
    cleaned = str(value).replace(' ', '').replace(',', '.').replace('%', '').replace('?', '')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def parse_ticker_data(ticker):
    url = f"https://smart-lab.ru/q/{ticker}/f/y/"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        tables = pd.read_html(
            StringIO(response.text), match="Выручка|Чистая прибыль"
        )
        raw_df = max(tables, key=len).copy()

        header_row_idx = None
        for i, row in raw_df.iterrows():
            years_detected = [
                str(cell).strip()
                for cell in row
                if re.match(r"^20\d{2}$", str(cell).strip())
            ]
            if len(years_detected) >= 2:
                header_row_idx = i
                break
        if header_row_idx is None:
            return None

        data_section = raw_df.iloc[header_row_idx:].copy()
        headers_raw = [str(c).strip() for c in data_section.iloc[0].tolist()]

        years = []
        year_col_indices = []
        for idx, cell in enumerate(headers_raw):
            year_match = re.search(r"(20\d{2})", cell)
            if year_match:
                years.append(int(year_match.group(1)))
                year_col_indices.append(idx)

        result_data = {}
        for idx in range(1, len(data_section)):
            row = data_section.iloc[idx]
            indicator = str(row.iloc[0]).strip()
            if indicator == "nan" or indicator == "":
                continue
            if any(
                trash in indicator.lower()
                for trash in [
                    "smart-lab",
                    "дата отчета",
                    "валюта",
                    "финансовый отчет",
                ]
            ):
                continue
            values = []
            for col_idx in year_col_indices:
                val = row.iloc[col_idx]
                values.append(clean_number(val))
            result_data[indicator] = values

        df = pd.DataFrame.from_dict(result_data, orient="index", columns=years)
        return df.dropna(how="all").sort_index()
    except:
        return None