import traceback
import uuid
from threading import Thread, Lock
import time
from enum import Enum
import constants as ct
from logger import Logger
from tinydb import TinyDB, Query


class Watchdog(Thread):

    """Aggregates price data for stocks and flares events."""
    DEBUG=True

    def __init__(self, portfolio: 'Portfolio', sell_handler: 'callable', get_order_fills: 'callable', get_ticker_price: 'callable'):
        """TODO: to be defined. """

        Thread.__init__(self)
        # initialize portfolio
        self.__portfolio = portfolio
        # initialize get_ticker_price mutex
        self.__mutex = Lock()
        # initialize watch list (list of list)
        self.__watchlist = TinyDB('db/watchlist.json')
        # initialize sell handler
        self.__sell_handler = sell_handler
        # initialize get_order_fills
        self.__get_order_fills = get_order_fills
        # initialize get_ticker_price
        self.__get_ticker_price = get_ticker_price

    def run(self):
        """
        Watches market to trigger sales.
        """
        while True:
            if Watchdog.DEBUG:
                Logger.debug('Pulling latest prices..')

            try:
                self.__check_for_events()
                time.sleep(ct.WATCHDOG_UPDATE_PERIOD)
            except Exception as ex:
                Logger.error(f'Exception {ex}. Exiting thread..')
                Logger.error(traceback.format_exc())
                break

    def __check_for_events(self):
        """TODO: Docstring for __check_for_events.
        """
        tickers = self.__portfolio.get_tickers()

        # check for order fills
        if ct.LIVE_TRADING:
            orders = self.__get_order_fills()
            self.__portfolio.sync_order_fills(orders)

        # check for sell signals
        for subscription in self.__watchlist:
            # extract tokens
            ticker = subscription['ticker']
            op = subscription['op']
            thresh = subscription['threshold']
            identifier = subscription['uuid']

            # make sure ticker is owned
            if ticker not in tickers:
                Logger.warn(f'Skipping over subscribed ticker not in portfolio!')
                # TODO: unsubscribe from this ticker
                continue

            ticker_price = self.get_price(ticker)

            if op == '>' and ticker_price > thresh:
                self.__sell_handler(ticker)
            elif op == '<' and ticker_price < thresh:
                self.__sell_handler(ticker)
            else:
                if Watchdog.DEBUG:
                    Logger.debug(f'Not triggering event for {ticker}: price: {ticker_price} operator: {op} thresh: {thresh}')

    def get_price(self, ticker: str) -> float:
        """TODO: Docstring for get_price.
        :returns: current market price of ticker

        """
        if not isinstance(ticker, str):
            raise TypeError('Expected str for ticker!')

        self.__mutex.acquire()
        price = self.__get_ticker_price(ticker)
        self.__mutex.release()

        return price

    def unsubscribe_all(self, ticker: str) -> None:
        """
        Kills all subscriptions associated with ticker.
        """
        self.__watchlist.remove(Query().ticker == ticker)

    def subscribe(self, ticker: str, threshold: float, op: str):
        """
        Subscribes delegate to event described by $CURRENT_PRICE [operator] threshold.

        :param ticker: TODO
        :returns: TODO

        """
        identifier = str(uuid.uuid1())
        self.__watchlist.insert({'uuid': identifier, 'ticker': ticker, 'threshold': threshold, 'op': op})
