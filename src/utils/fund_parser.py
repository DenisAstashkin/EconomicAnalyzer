import requests
import pandas as pd
import re
from io import StringIO

ticker = 'GAZP'
url = f'https://smart-lab.ru/q/{ticker}/f/y/'

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

try:
    print(f"Запуск парсинга для: {url}")
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    # Извлекаем таблицы
    tables = pd.read_html(StringIO(response.text), match='Выручка|Чистая прибыль')
    raw_df = max(tables, key=len).copy()
    
    # Находим строку с годами
    header_row_idx = None
    for i, row in raw_df.iterrows():
        years = [str(cell).strip() for cell in row if re.match(r'^20\d{2}$', str(cell).strip())]
        if len(years) >= 2:
            header_row_idx = i
            break
    
    if header_row_idx is None:
        raise ValueError("Не удалось найти строку с годами")
    
    print(f"Строка с заголовками найдена на индексе: {header_row_idx}")
    
    # Получаем данные 
    data_section = raw_df.iloc[header_row_idx:].copy()
    
    # заголовки
    headers_raw = data_section.iloc[0].tolist()
    
    # очистка данных
    years = []
    other_cols = []
    for cell in headers_raw:
        cell_str = str(cell).strip()
        year_match = re.search(r'(20\d{2})', cell_str)
        if year_match:
            years.append(year_match.group(1))
        else:
            other_cols.append(cell_str)
    
    # структура данных вручную
    result_data = {}
    current_indicator = None
    
    # обрабатываем строки данных 
    for idx in range(1, len(data_section)):
        row = data_section.iloc[idx]
        cells = [str(cell).strip() for cell in row if str(cell).strip() not in ['nan', '']]
        
        if len(cells) == 0:
            continue
            
        indicator = cells[0]
        
        # пропускаем служебные строки
        if any(trash in indicator.lower() for trash in ['smart-lab', 'дата отчета', 'валюта', 'финансовый отчет']):
            continue
        
        # собираем по годам
        values = []
        for i, year in enumerate(years):
            if i + 1 < len(cells):
                value = clean_number(cells[i + 1])
                values.append(value)
            else:
                values.append(None)
        
        result_data[indicator] = values
    
    # DataFrame
    df = pd.DataFrame.from_dict(result_data, orient='index', columns=years)
    
    # удаляем пустые строки
    df = df.dropna(how='all')
    
    # сортируем 
    df = df.sort_index()
    
    print(f"Успешно: {len(df)}")
    print(f"Годы: {years}")
    
    # выводим 
    print("\nВсе показатели:")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 200, 'display.float_format', '{:.2f}'.format):
        print(df)
    
    # Сохраняем в CSV
    df.to_csv(f'{ticker}_fundamental.csv', encoding='utf-8-sig')
    print(f"\nДанные сохранены в {ticker}_fundamental.csv")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    print("\nПолный стек ошибки:")
    traceback.print_exc()