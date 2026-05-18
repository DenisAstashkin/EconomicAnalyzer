import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[ОШИБКА] Запрос не удался: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Ищем блок с финансовыми данными (div class='data')
    data_div = soup.find('div', class_='data')
    if not data_div:
        print("[ОШИБКА] Не найден div class='data'")
        return None

    years = []
    raw_rows = []  # [название_показателя, значение_2021, значение_2022, ...]

    # Все блоки показателей (div class='item')
    items = data_div.find_all('div', class_='item')
    if not items:
        print("[ОШИБКА] Нет div с классом 'item'")
        return None

    for item in items:
        # Название показателя (span class='ru')
        name_span = item.find('span', class_='ru')
        if not name_span:
            continue
        metric_name = name_span.get_text(strip=True)

        # Блоки с данными за каждый год (div class='d2')
        data_blocks = item.find_all('div', class_='d2')
        if not data_blocks:
            continue

        row_values = []
        # Если года ещё не собраны – берём из первого показателя
        if not years:
            for block in data_blocks:
                year_span = block.find('span', class_='y')
                if year_span:
                    year_text = year_span.get_text(strip=True)
                    if year_text and re.match(r'^\d{4}$', year_text):
                        years.append(year_text)

        # Числовое значение показателя (span class='n')
        for block in data_blocks:
            val_span = block.find('span', class_='n')
            val_text = val_span.get_text(strip=True) if val_span else ''
            row_values.append(val_text)

        raw_rows.append([metric_name] + row_values)

    if not years:
        print("[ОШИБКА] Годы не найдены")
        return None

    # Формируем DataFrame
    columns = ['Показатель'] + years
    df = pd.DataFrame(raw_rows, columns=columns)

    # Очищаем числовые колонки: убираем пробелы, заменяем запятую на точку
    for col in years:
        df[col] = df[col].astype(str).str.replace(' ', '').str.replace(',', '.')
        df[col] = df[col].apply(
            lambda x: float(x) if re.match(r'^-?\d+(\.\d+)?$', x) else pd.NA
        )

    # Транспонируем: строки – года, колонки – показатели
    df = df.set_index('Показатель').T
    df.index.name = 'Год'
    df.index = df.index.astype(int)
    df = df.sort_index()

    # (Опционально) Переименовываем колонки в английские названия
    rename_map = {
        'Чистый проц. доход': 'Net_interest_income',
        'Чистый комисс. доход': 'Net_fee_income',
        'Чистая прибыль': 'Net_profit',
        'Капитал': 'Capital',
        'Число клиентов': 'Number_of_clients',
        'EPS, руб': 'EPS',
        'P/E': 'PE',
        'P/B': 'PB'
    }
    df = df.rename(columns=rename_map)

    return df