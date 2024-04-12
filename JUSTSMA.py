import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import time

mt5.initialize() 

login = 30818760
password = 'klinbliss556G'
server = 'Deriv-Demo'

mt5.login(login=login, password=password, server=server)

def market_order(symbol, volume, order_type, deviation):
    tick = mt5.symbol_info_tick(symbol)

    order_dict = {'buy': 0, 'sell': 1}
    price_dict = {'buy': tick.ask, 'sell': tick.bid}
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_dict[order_type],
        "price": price_dict[order_type],
        "deviation": deviation,
        "magic": 100,
        "comment": "python market order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,  # Change to FOK or other supported mode
    }

    order_result = mt5.order_send(request)
    print(order_result)

    return {"ticket": order_result.order, "price": order_result.price}  # Return a dictionary

def modify_trailing_stop(ticket, stop_loss):
    request = {
        "action": mt5.TRADE_ACTION_MODIFY,
        "position": ticket,
        "stoploss": stop_loss,
    }
    mt5.order_send(request)

def get_exposure(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        pos_df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())
        exposure = pos_df['volume'].sum()
        return exposure
    else:
        return 0

def signal(symbol, timeframe, sma_period):
    bars = mt5.copy_rates_from_pos(symbol, timeframe, 0, 2)

    if len(bars) < 2:
        return None, None, 'insufficient_data'

    bars_df = pd.DataFrame(bars)

    if 'close' not in bars_df.columns:
        return None, None, 'no_close_column'

    last_close = bars_df['close'].iloc[-2]
    sma = bars_df['close'].mean()
    direction = 'flat'

    if last_close > sma:
        direction = 'buy'
    elif last_close < sma:
        direction = 'sell'

    return last_close, sma, direction

def check_break_even(position, trailing_stop_pips=10):
    current_price = mt5.symbol_info_tick(position.symbol).last
    if position.type == 0:  # Buy position
        if current_price - position.price_open > trailing_stop_pips * mt5.symbol_info(position.symbol).point:
            return True
    elif position.type == 1:  # Sell position
        if position.price_open - current_price > trailing_stop_pips * mt5.symbol_info(position.symbol).point:
            return True
    return False

def move_to_break_even(position, trailing_stop_pips=10):
    current_price = mt5.symbol_info_tick(position.symbol).last
    if position.type == 0:  # Buy position
        new_stop_loss = current_price - trailing_stop_pips * mt5.symbol_info(position.symbol).point
    elif position.type == 1:  # Sell position
        new_stop_loss = current_price + trailing_stop_pips * mt5.symbol_info(position.symbol).point

    modify_trailing_stop(position.ticket, new_stop_loss)

import time 
import sys 

if __name__ == '__main__':
    SYMBOL = 'Volatility 75 Index'
    VOLUME = 0.005
    TIMEFRAME = mt5.TIMEFRAME_M30
    SMA_PERIOD = 10
    DEVIATION = 20
    TRAILING_STOP_PIPS = 10

    while True:
        exposure = get_exposure(SYMBOL)
        last_close, sma, direction = signal(SYMBOL, TIMEFRAME, SMA_PERIOD)

        if direction == 'buy':
            print('Waiting for 30 seconds before opening BUY trades...')
            time.sleep(30)  # Introduce a delay of 30 seconds
            print('Opening BUY trades...')
            if not mt5.positions_total():
                for _ in range(3):  # Open three positions
                    market_order(SYMBOL, VOLUME, direction, DEVIATION)

                # Close opposite SELL positions
                sell_positions = mt5.positions_get(symbol=SYMBOL)
                for position in sell_positions:
                    if position.type == 1:  # Type 1 indicates a sell position
                        close_order(position.ticket, DEVIATION)

        elif direction == 'sell':
            print('Waiting for 30 seconds before opening SELL trades...')
            time.sleep(30)  # Introduce a delay of 30 seconds
            print('Opening SELL trades...')
            if not mt5.positions_total():
                for _ in range(3):  # Open three positions
                    market_order(SYMBOL, VOLUME, direction, DEVIATION)

                # Close opposite BUY positions
                buy_positions = mt5.positions_get(symbol=SYMBOL)
                for position in buy_positions:
                    if position.type == 0:  # Type 0 indicates a buy position
                        close_order(position.ticket, DEVIATION)

        # Check and move to break-even for existing positions
        positions = mt5.positions_get(symbol=SYMBOL)
        for position in positions:
            if check_break_even(position, TRAILING_STOP_PIPS):
                print('Moving to break-even for position:', position.ticket)
                move_to_break_even(position, TRAILING_STOP_PIPS)

        print('-------\n')
        time.sleep(40)

        print('time: ', datetime.now())
        print('exposure: ', exposure)
        print('last_close: ', last_close)
        print('sma: ', sma)
        print('signal: ', direction)
        print('-------\n')

        time.sleep(40)
