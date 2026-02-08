import requests
from models import Candle

def get_TMI(ticker: str) -> str:
    """ Функция для сопоставления нейминга ценной бумаги с её типом (акция, облигация и тд)

    Args:
        ticker (str): Нейминг ценной бумаги

    Raises:
        Exception: Ошибка ненайденных данных
        Exception: Ошибка ненайденного типа бумаги

    Returns:
        str: Тип бумаги
    """
    
    url = f'https://iss.moex.com/iss/securities.json'
    
    params = {
        'q': ticker
    }

    response = requests.get(url, params=params)
    
    data = response.json()
    
    data = data['securities']['data']
    
    if len(data) == 0:
        raise Exception('[ERROR] Asset type not found')
    
    for i in data:
        if i[0] == ticker and i[13] != 'null':
            return i[13]
    
    raise Exception('[ERROR] Asset type not found')
    
    
def get_candles(ticker: str, type_ticker: str, interval: int, start: str, end: str) -> list[Candle]:
    """ Функция для парсинга данных свечевого графика для определённой бумаги

    Args:
        ticker (str): Нейминг ценной бумаги
        type_ticker (str): Тип ценной бумаги
        interval (int): Таймфрейм
        start (str): Дата начала парсинга (ГГГГ-ММ-ДД ЧЧ:ММ:СС)
        end (str): Дата окончания парсинга (ГГГГ-ММ-ДД ЧЧ:ММ:СС)

    Raises:
        Exception: Ошибка получения свечевого графика

    Returns:
        list[Candle]: Список свеч
    """
    
    if type_ticker == 'null':
        raise Exception('[ERROR] Type_ticker is not defined')
    
    url = f'https://iss.moex.com/iss/engines/stock/markets/{type_ticker}/securities/{ticker}/candles.json'

    params = {
        'interval': interval,
        'from': start,
        'till': end
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise Exception(f'[ERROR] Status code is {response.status_code}')
    
    data = response.json()

    data = data['candles']['data']
    
    if len(data) == 0:
        raise Exception('[ERROR] Information about candles was not found')

    candles = []
    
    for i in data:
        candle = Candle(i[3], i[2], i[0], i[1])
        
        candles.append(candle)
    
    return candles