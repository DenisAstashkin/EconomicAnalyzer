from utils import *
from config import *
import talib
import numpy as np

tiket = input("Введите тикет (SBER): ")

f = get_candles(tiket, TYPE_TO_MARCKET[get_TMI(tiket)], 60, '2024-10-28', '2026-03-17')

data = []

for i in f:
    data.append(i.close)

data = np.array(data, dtype=np.float64)

rsi = talib.RSI(data)
ema50 = talib.EMA(data, 50)
ema200 = talib.EMA(data, 200)
bb = talib.BBANDS(data)
bb = {
    'low': bb[2],
    'middle': bb[1],
    'high': bb[0]
}


last_price = data[-1]
prev_price = data[-2]
last_rsi = rsi[-1]
prev_rsi = rsi[-2]

l_bb_low = bb['low'][-1]
l_bb_mid = bb['middle'][-1]
l_bb_high = bb['high'][-1]

l_ema50 = ema50[-1]
l_ema200 = ema200[-1]


is_oversold = last_rsi < 30 or last_price <= l_bb_low
is_overbought = last_rsi > 70 or last_price >= l_bb_high
is_uptrend = l_ema50 > l_ema200
is_reversing_up = last_rsi > prev_rsi

verdict = "НАБЛЮДЕНИЕ (Вне диапазона)"
reason = "Цена в середине канала, четких сигналов нет."

if is_oversold and is_uptrend and is_reversing_up:
    verdict = "ПОКУПКА (Buy Range)"
    reason = f"Цена {last_price:.2f} у нижней границы BB, RSI {last_rsi:.1f} начал расти при бычьем тренде."


elif is_overbought:
    verdict = "ПРОДАЖА (Sell Range)"
    reason = f"Цена {last_price:.2f} в зоне перекупленности или выше верхней границы BB."


elif last_price > l_bb_mid and is_uptrend:
    verdict = "УДЕРЖАНИЕ (Hold Range)"
    reason = "Цена выше средней линии BB, тренд стабильно растущий."


elif last_price < l_bb_low and not is_uptrend:
    verdict = "ВНЕ РЫНКА (Strong Downtrend)"
    reason = "Сильный нисходящий тренд, опасно ловить дно."

print("\n" + "="*30)
print(f"ИТОГОВЫЙ ВЕРДИКТ ДЛЯ {tiket}: {verdict}")
print(f"ОБОСНОВАНИЕ: {reason}")
print("="*30)