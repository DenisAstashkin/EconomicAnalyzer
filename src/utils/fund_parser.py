import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_number(value):
    if value is None or value == '' or value == '—':
        return None
    s = str(value).strip()
    # Удаляем возможные единицы измерения и лишние символы (не цифры, не запятая/точка/минус)
    s = re.sub(r'[^\d,.\-]', '', s)
    # Меняем запятую на точку, только если в числе нет точки (иначе запятая — разделитель тысяч)
    if '.' not in s and ',' in s:
        s = s.replace(',', '.')
    else:
        s = s.replace(',', '')
    s = s.replace(' ', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None

def parse_ticker_data(ticker):
    url = f"https://smart-lab.ru/q/{ticker}/f/y/"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        return None

    # Сопоставление синонимов с целевыми названиями признаков модели
    FEATURE_ALIASES = {
        'EPS, руб': [
            'eps, руб', 'eps', 'прибыль на акцию, руб', 'eps (руб.)',
            'прибыль на 1 акцию, руб'
        ],
        'P/E': [
            'p/e', 'p/e (капитализация/прибыль)', 'капитализация/прибыль',
            'p/e ratio'
        ],
        'Капитал, млрд руб': [
            'капитализация, млрд руб', 'капитализация', 'капитал, млрд руб',
            'рыночная капитализация, млрд руб', 'market cap, млрд руб'
        ],
        'Чистая прибыль, млрд руб': [
            'чистая прибыль, млрд руб', 'чистая прибыль (млрд руб.)',
            'чистая прибыль', 'чистая прибыль, млрд руб.'
        ],
        'Расх на персонал, млрд руб': [
            'расходы на персонал, млрд руб', 'расх на персонал, млрд руб',
            'расходы на персонал', 'затраты на персонал, млрд руб'
        ],
        'P/B': [
            'p/b', 'p/b (капитализация/балансовая стоимость)',
            'капитализация/балансовая стоимость', 'p/b ratio'
        ]
    }

    all_data = {}   # {целевое_название: {год: значение}}

    # Перебираем все таблицы на странице
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue

        # Ищем строку заголовка с годами (>=2 года вида 20XX)
        header_idx = None
        years = []
        col_idx_of_year = []

        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            years_in_row = []
            for j, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                m = re.match(r'^(20\d{2})$', text)
                if m:
                    years_in_row.append((j, int(m.group(1))))
            if len(years_in_row) >= 2:
                header_idx = i
                col_idx_of_year = [j for j, _ in years_in_row]
                years = [y for _, y in years_in_row]
                break

        if header_idx is None:
            continue   # в этой таблице нет нужного формата годов

        # Обрабатываем строки данных (всё, что после заголовка)
        for row in rows[header_idx + 1:]:
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue

            raw_name = cells[0].get_text(strip=True)
            if not raw_name or raw_name.lower() in ('показатель', 'наименование', ''):
                continue

            # Извлекаем значения по найденным годам
            values_by_year = {}
            for col_j, year in zip(col_idx_of_year, years):
                if col_j >= len(cells):
                    continue
                val = clean_number(cells[col_j].get_text(strip=True))
                if val is not None:
                    values_by_year[year] = val

            if not values_by_year:
                continue

            # Сопоставляем название показателя с целевыми именами
            name_lower = raw_name.lower().strip()
            matched_target = None
            for target, aliases in FEATURE_ALIASES.items():
                for alias in aliases:
                    if alias in name_lower:
                        matched_target = target
                        break
                if matched_target:
                    break

            if matched_target is None:
                continue

            # Сохраняем данные (при дубликатах оставляем первое найденное значение для года)
            if matched_target not in all_data:
                all_data[matched_target] = {}
            for y, v in values_by_year.items():
                if y not in all_data[matched_target] or all_data[matched_target][y] is None:
                    all_data[matched_target][y] = v

    if not all_data:
        return None

    # Собираем множество всех годов
    all_years = sorted({y for d in all_data.values() for y in d})

    # Формируем DataFrame
    data_for_df = {}
    for target in FEATURE_ALIASES:
        if target in all_data:
            row = [all_data[target].get(y, None) for y in all_years]
            data_for_df[target] = row

    df = pd.DataFrame.from_dict(data_for_df, orient='index', columns=all_years)
    df = df.dropna(how='all').sort_index()
    return df if not df.empty else None