from utils import *
from config import *
import talib
import numpy as np

# параметры
BB_PERIOD = 20
BB_STD = 2.0
EMA_PERIOD = 50
RSI_PERIOD = 14
ATR_PERIOD = 14
STOP_LOSS_ATR_MULT = 1.5
TAKE_PROFIT_ATR_MULT = 3.0
MIN_RSI_OVERSOLD = 30
MAX_RSI_OVERBOUGHT = 70

# получение данных
ticket = input("Введите тикет (SBER/GAZP/LKOH/etc): ")
candles = get_candles(ticket, TYPE_TO_MARCKET[get_TMI(ticket)], 60, '2024-10-28', '2026-03-17')

n = len(candles)
close = np.array([c.close for c in candles], dtype=np.float64)
high = np.array([c.high for c in candles], dtype=np.float64)
low = np.array([c.low for c in candles], dtype=np.float64)

# расчет индикаторов
rsi = talib.RSI(close, timeperiod=RSI_PERIOD)
ema = talib.EMA(close, timeperiod=EMA_PERIOD)
upper_bb, middle_bb, lower_bb = talib.BBANDS(close, timeperiod=BB_PERIOD,
                                             nbdevup=BB_STD, nbdevdn=BB_STD)
atr = talib.ATR(high, low, close, timeperiod=ATR_PERIOD)

start = max(BB_PERIOD, EMA_PERIOD, RSI_PERIOD, ATR_PERIOD)

# определение глобального тренда
if n > start:
    first_price = np.mean(close[start:n//2])
    last_price = close[-1]
    trend_direction = "UP" if last_price > first_price else "DOWN"
    trend_percent = ((last_price - first_price) / first_price) * 100
else:
    first_price = close[0]
    last_price = close[-1]
    trend_direction = "UP" if last_price > first_price else "DOWN"
    trend_percent = ((last_price - first_price) / first_price) * 100

print(f"\n Общий тренд {ticket} за период: {trend_direction} ({trend_percent:.1f}%)")

# определение сигналов
signal = np.zeros(n, dtype=int)
position = np.zeros(n, dtype=int)
entry_price = np.full(n, np.nan)
stop_loss = np.full(n, np.nan)
take_profit = np.full(n, np.nan)

for i in range(start, n):
    price = close[i]
    rsi_val = rsi[i]
    ema_val = ema[i]
    upper = upper_bb[i]
    lower = lower_bb[i]
    atr_val = atr[i]
    
    if np.isnan(rsi_val) or np.isnan(ema_val) or np.isnan(atr_val):
        position[i] = position[i-1] if i > 0 else 0
        continue
    
    if position[i-1] == 0:
        # Инициализируем сигнал как 0
        signal[i] = 0
        
        # ПОКУПКА
        buy_signal = False
        if trend_direction == "UP":
            buy_signal = ((price < lower or rsi_val < MIN_RSI_OVERSOLD) and price > ema_val)
        else:
            buy_signal = ((price < lower and rsi_val < MIN_RSI_OVERSOLD - 10) and price > ema_val)
        
        if buy_signal:
            signal[i] = 1
            position[i] = 1
            entry_price[i] = price
            stop_loss[i] = price - STOP_LOSS_ATR_MULT * atr_val
            take_profit[i] = price + TAKE_PROFIT_ATR_MULT * atr_val
        
        # ПРОДАЖА 
        elif signal[i] == 0:
            sell_signal = False
            if trend_direction == "DOWN":
                sell_signal = ((price > upper or rsi_val > MAX_RSI_OVERBOUGHT) and price < ema_val)
            else:
                sell_signal = ((price > upper and rsi_val > MAX_RSI_OVERBOUGHT + 10) and price < ema_val)
            
            if sell_signal:
                signal[i] = -1
                position[i] = -1
                entry_price[i] = price
                stop_loss[i] = price + STOP_LOSS_ATR_MULT * atr_val
                take_profit[i] = price - TAKE_PROFIT_ATR_MULT * atr_val
            else:
                position[i] = 0
        else:
            position[i] = 0
    
    else:
        position[i] = position[i-1]
        entry_price[i] = entry_price[i-1]
        stop_loss[i] = stop_loss[i-1]
        take_profit[i] = take_profit[i-1]
        
        if position[i] == 1:
            if (price <= stop_loss[i] or price >= take_profit[i] or
                (price < ema_val and rsi_val < 45)):
                position[i] = 0
                entry_price[i] = np.nan
                stop_loss[i] = np.nan
                take_profit[i] = np.nan
        
        elif position[i] == -1:
            if (price >= stop_loss[i] or price <= take_profit[i] or
                (price > ema_val and rsi_val > 55)):
                position[i] = 0
                entry_price[i] = np.nan
                stop_loss[i] = np.nan
                take_profit[i] = np.nan

# бектест
returns = np.zeros(n)
trade_returns = []

for i in range(1, n):
    if position[i-1] != 0:
        ret = (close[i] / close[i-1] - 1) * position[i-1]
        returns[i] = ret
        
        if position[i] == 0 and position[i-1] != 0:
            trade_returns.append(ret)

cumulative = np.cumprod(1 + returns)
total_return = (cumulative[-1] - 1) * 100

if np.std(returns) != 0:
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
else:
    sharpe = 0

num_trades = len(trade_returns)
winning_trades = sum(1 for r in trade_returns if r > 0)
win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
avg_return = np.mean(trade_returns) * 100 if trade_returns else 0
avg_win = np.mean([r for r in trade_returns if r > 0]) * 100 if winning_trades > 0 else 0
avg_loss = np.mean([r for r in trade_returns if r < 0]) * 100 if (num_trades - winning_trades) > 0 else 0
profit_factor = abs(sum([r for r in trade_returns if r > 0]) / sum([r for r in trade_returns if r < 0])) if sum([r for r in trade_returns if r < 0]) != 0 else 0

print("\n" + "="*50)
print(f"РЕЗУЛЬТАТЫ СТРАТЕГИИ ДЛЯ {ticket}")
print(f"Общий тренд: {trend_direction} ({trend_percent:.1f}%)")
print(f"Совокупная доходность: {total_return:.2f}%")
print(f"Коэффициент Шарпа: {sharpe:.2f}")
print(f"Количество сделок: {num_trades}")
print(f"Прибыльных сделок: {winning_trades} ({win_rate:.1f}%)")
print(f"Средняя доходность сделки: {avg_return:.2f}%")
print(f"Средняя прибыль: {avg_win:.2f}%")
print(f"Средний убыток: {avg_loss:.2f}%")
print(f"Фактор прибыли: {profit_factor:.2f}")
print("="*50)

# вердикт
last_idx = n - 1
last_price = close[last_idx]
last_rsi = rsi[last_idx]
last_ema = ema[last_idx]
last_upper_bb = upper_bb[last_idx]
last_lower_bb = lower_bb[last_idx]
position_val = position[last_idx]

is_oversold = last_rsi < MIN_RSI_OVERSOLD or last_price <= last_lower_bb
is_overbought = last_rsi > MAX_RSI_OVERBOUGHT or last_price >= last_upper_bb
is_uptrend = last_price > last_ema
is_downtrend = last_price < last_ema

if position_val == 1:
    verdict = "В ДЛИННОЙ ПОЗИЦИИ"
    reason = f"Цена {last_price:.2f} выше EMA, RSI {last_rsi:.1f}. Стоп {stop_loss[last_idx]:.2f}"
elif position_val == -1:
    verdict = "В КОРОТКОЙ ПОЗИЦИИ"
    reason = f"Цена {last_price:.2f} ниже EMA, RSI {last_rsi:.1f}. Стоп {stop_loss[last_idx]:.2f}"
else:
    if is_oversold and is_uptrend and trend_direction == "UP":
        verdict = "ПОКУПКА"
        reason = f"Цена у нижней BB, RSI {last_rsi:.1f} < {MIN_RSI_OVERSOLD}, тренд восходящий."
    elif is_overbought and is_downtrend and trend_direction == "DOWN":
        verdict = "ПРОДАЖА"
        reason = f"Цена у верхней BB, RSI {last_rsi:.1f} > {MAX_RSI_OVERBOUGHT}, тренд нисходящий."
    elif is_uptrend:
        verdict = "УДЕРЖАНИЕ"
        reason = f"Цена {last_price:.2f} выше EMA, RSI {last_rsi:.1f}, ждём отката для покупки."
    elif is_downtrend:
        verdict = "ВНЕ РЫНКА"
        reason = f"Цена {last_price:.2f} ниже EMA, RSI {last_rsi:.1f}, ждём сигнала на продажу."
    else:
        verdict = "НАБЛЮДЕНИЕ"
        reason = f"Цена {last_price:.2f} вблизи EMA, RSI {last_rsi:.1f}"

print("\n" + "="*30)
print(f"ВЕРДИКТ ДЛЯ {ticket}: {verdict}")
print(f"ОБОСНОВАНИЕ: {reason}")
print("="*30)