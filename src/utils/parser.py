import requests
from src.models import Candle

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
    
    if response.status_code != 200:
        raise Exception(f'[ERROR] Status code is {response.status_code}')
    
    data = response.json()
    
    data = data['securities']['data']
    
    if len(data) == 0:
        raise Exception('[ERROR] Asset type not found')
    
    for i in data:
        if i[0] == ticker and i[13] != 'null':
            return i[13]
    
    raise Exception('[ERROR] Asset type not found')
    
    
async def get_candles(ticker: str, type_ticker: str, interval: int, start: str, end: str) -> list[Candle]:
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
    
    candles = []
    starts = 0
    
    while True:
        url = f'https://iss.moex.com/iss/engines/stock/markets/{type_ticker}/securities/{ticker}/candles.json'

        params = {
            'interval': interval,
            'from': start,
            'till': end,
            'start': starts
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f'[ERROR] Status code is {response.status_code}')
        
        data = response.json()

        data = data['candles']['data']
        
        if not data:
            break
        
        if len(data) == 0:
            raise Exception('[ERROR] Information about candles was not found')
        
        for i in data:
            candle = Candle(i[3], i[2], i[0], i[1], i[5], i[7])
            
            candles.append(candle)
            
        starts += 500
    
    return candles