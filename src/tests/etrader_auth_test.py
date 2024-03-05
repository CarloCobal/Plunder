#!/usr/bin/env python

import sys

sys.path.append('../')

from etrader import ETrader

x = ETrader()
# x.place_order(price_type='LIMIT', order_term='GOOD_FOR_DAY', limit_price=25, symbol='APHA', order_action='BUY', quantity=2)
# x.place_order(price_type='LIMIT', order_term='GOOD_FOR_DAY', limit_price=0.002, symbol='MINE', order_action='SELL', quantity=1)
print(x.get_filled_orders())
#print(x.get_ticker_price('TESLA'))
# def preview_order(self, price_type: str, order_term: str, limit_price: str, symbol: str, order_action: str, quantity: int) -> (int, str):
