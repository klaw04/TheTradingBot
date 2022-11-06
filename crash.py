import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import time

import requests


def market_order(symbol, volume, order_type, **kwargs):
    tick = mt5.symbol_info_tick(symbol)

    order_dict = {'buy': 0, 'sell': 1}
    price_dict = {'buy': tick.ask, 'sell': tick.bid}

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_dict[order_type],
        "price": price_dict[order_type],
        "deviation": DEVIATION,
        "magic": 100,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    order_result = mt5.order_send(request)
    print(order_result)

    return order_result


def close_order(ticket):
    positions = mt5.positions_get()

    for pos in positions:
        tick = mt5.symbol_info_tick(pos.symbol)
        type_dict = {0: 1, 1: 0}
        price_dict = {0: tick.ask, 1: tick.bid}

        if pos.ticket == ticket:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": type_dict[pos.type],
                "price": price_dict[pos.type],
                "deviation": DEVIATION,
                "magic": 100,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            order_result = mt5.order_send(request)
            print(order_result)

            return order_result

    return 'Ticket does not exist'


def get_exposure(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        pos_df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())
        exposure = pos_df['volume'].sum()

        return exposure


def signal(symbol, timeframe, sma_period):
    bars = mt5.copy_rates_from_pos(symbol, timeframe, 1, sma_period)
    bars_df = pd.DataFrame(bars)

    last_close = bars_df.iloc[-1].close
    sma = bars_df.close.mean()

    direction = 'flat'
    if last_close > sma:
        direction = 'buy'
    elif last_close < sma:
        direction = 'sell'

    return last_close, sma, direction


period = input('Input time please: ')
period = int(period)

indexes = mt5.positions_get(symbol="Crash 500 Index")

for index in indexes:
        print(index.identifier)

TICKET = index.identifier
MAX_DIST_SL = 0.010
TRAIL_AMOUNT = 0.070
DEFAULT_SL = 0.070


def trail_sl():
    position = mt5.positions_get(ticket=TICKET)

    if position:
        position = position[0]
    else:
        print('Position does not exist')

    order_type = position.type
    price_current = position.price_current
    price_open = position.price_open
    sl = position.sl

    dist_from_sl = abs(round(price_current - sl, 6))

    if dist_from_sl > MAX_DIST_SL:

        if sl != 0.0:
            if order_type == 0:
                new_sl = sl + TRAIL_AMOUNT

            elif order_type == 1:
                new_sl = sl - TRAIL_AMOUNT

        else:

            new_sl = price_open - DEFAULT_SL if order_type == 0 else price_open + DEFAULT_SL

        request = {
            'action': mt5.TRADE_ACTION_SLTP,
            'position': position.ticket,
            'sl': new_sl,
        }

        result = mt5.order_send(request)
        print(result)
        return result


if __name__ == '__main__':

    SYMBOL = "Crash 500 Index"
    VOLUME = 0.60
    TIMEFRAME = mt5.TIMEFRAME_m15
    SMA_PERIOD = 20
    DEVIATION = 20

    mt5.initialize(login=30160883, server="Deriv-Demo", password="Brian0043")

    while True:

        exposure = get_exposure(SYMBOL)
        last_close, sma, direction = signal(SYMBOL, TIMEFRAME, SMA_PERIOD)

        if direction == 'buy':

            for pos in mt5.positions_get():
                if pos.type == 1:
                    close_order(pos.ticket)

            if not mt5.positions_total():
                market_order(SYMBOL, VOLUME, direction)

        elif direction == 'sell':

            for pos in mt5.positions_get():
                if pos.type == 0:
                    close_order(pos.ticket)

            if not mt5.positions_total():
                market_order(SYMBOL, VOLUME, direction)

        print('time: ', datetime.now())
        print('exposure: ', exposure)
        print('last_close: ', last_close)
        print('sma: ', sma)
        print('signal: ', direction)
        print('-------\n')

        time.sleep(period)

        print('Starting Trailing Stoploss..')
        print(f'Position: {str(TICKET)}')

        # strategy loop
        while True:
            result = trail_sl()
            # wait 1 second
            time.sleep(1)

        account_info = mt5.account_info()
        gains = pd.DataFrame(account_info)
        profit = pd.DataFrame(account_info).iloc[12]
        balance = pd.DataFrame(account_info).iloc[10]
        equity = pd.DataFrame(account_info).iloc[13]
        TOKEN = "5461375116:AAFCu0IVtPIerZfcZLGRgfgCspn9pfwR_hI"
        chat_id = "5664711054"
        message = """Profits:""" + profit.to_string(index=False) + \
                  """Balance:""" + balance.to_string(index=False)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        print(requests.get(url).json)
