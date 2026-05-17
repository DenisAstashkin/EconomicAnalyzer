from fastapi import FastAPI
from src.utils import *
from src.config import *
from tensorflow import keras
from datetime import datetime, timedelta
import numpy as np
import talib
from fastapi.responses import JSONResponse
import asyncio


app = FastAPI()
model = keras.models.load_model('src/AI_models/invest_ai_model.keras')

def predict_invest(model, d1_raw, w1_raw, mn_raw):
    def scale(win):
        mi, ma = win.min(axis=0), win.max(axis=0)
        den = ma - mi + 1e-7
        return (win - mi) / den, mi, den

    s_d1, mi_d1, den_d1 = scale(np.array(d1_raw))
    s_w1, _, _ = scale(np.array(w1_raw))
    s_mn, _, _ = scale(np.array(mn_raw))

    pred = model.predict([s_d1[None,...], s_w1[None,...], s_mn[None,...]], verbose=0)
    
    return pred.flatten() * den_d1[1] + mi_d1[1]

@app.get("/tickets/algo/{ticket}")
async def algo_analyze(ticket):
    
    from_date = (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d")
    candles = await get_candles(ticket, TYPE_TO_MARCKET[get_TMI(ticket)], 60, from_date, '')
    
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
        
    return {"verdict": verdict, "reason": reason, "strategy_results":[f"Общий тренд: {trend_direction} ({trend_percent:.1f}%)", f"Совокупная доходность: {total_return:.2f}%",
                                                                      f"Коэффициент Шарпа: {sharpe:.2f}", f"Количество сделок: {num_trades}", f"Прибыльных сделок: {winning_trades} ({win_rate:.1f}%)",
                                                                      f"Средняя доходность сделки: {avg_return:.2f}%", f"Средняя прибыль: {avg_win:.2f}%", f"Средний убыток: {avg_loss:.2f}%",
                                                                      f"Фактор прибыли: {profit_factor:.2f}"]}

@app.get("/tickets/techAI/{ticket}")
async def tickets(ticket):
    
    candles24, candles7, candles31 = await asyncio.gather(
        get_candles(ticket, TYPE_TO_MARCKET[get_TMI(ticket)], 24, (datetime.now() - timedelta(days=1000)).strftime("%Y-%m-%d"), ''),
        get_candles(ticket, TYPE_TO_MARCKET[get_TMI(ticket)], 7, (datetime.now() - timedelta(weeks=624)).strftime("%Y-%m-%d"), ''),
        get_candles(ticket, TYPE_TO_MARCKET[get_TMI(ticket)], 31, (datetime.now() - timedelta(weeks=1000)).strftime("%Y-%m-%d"), '')
    )
    
    close24 = np.array([i.close for i in candles24], dtype=np.float64)
    close7 = np.array([i.close for i in candles7], dtype=np.float64)
    close31 = np.array([i.close for i in candles31], dtype=np.float64)
    
    rsi24 = talib.RSI(close24)
    rsi7 = talib.RSI(close7)
    rsi31 = talib.RSI(close31)
    
    ema24 = talib.EMA(close24, 15)
    ema7 = talib.EMA(close7, 15)
    ema31 = talib.EMA(close31, 15)
    
    bb24 = talib.BBANDS(close24)
    bb7 = talib.BBANDS(close7)
    bb31 = talib.BBANDS(close31)
    
    bb24 = {
        'low': bb24[2],
        'high': bb24[0]
    }
    bb7 = {
        'low': bb7[2],
        'high': bb7[0]
    }
    bb31 = {
        'low': bb31[2],
        'high': bb31[0]
    }
    
    D = []
    W = []
    M = []
    
    
    for i in range(len(candles24) - 30, len(candles24)):
        D.append([candles24[i].open, candles24[i].close, candles24[i].high, candles24[i].low, candles24[i].volume, rsi24[i], bb24['high'][i], bb24['low'][i], ema24[i]])
    
    for i in range(len(candles7) - 54, len(candles7)):
        W.append([candles7[i].open, candles7[i].close, candles7[i].high, candles7[i].low, candles7[i].volume, rsi7[i], bb7['high'][i], bb7['low'][i], ema7[i]])
        
    for i in range(len(candles31) - 28, len(candles31)):
        M.append([candles31[i].open, candles31[i].close, candles31[i].high, candles31[i].low, candles31[i].volume, rsi31[i], bb31['high'][i], bb31['low'][i], ema31[i]])
    
    return JSONResponse({'candles':  [c.__dict__ for c in candles24[-18:]], 'candles_pred': list(predict_invest(model, np.array(D), np.array(W), np.array(M)))})