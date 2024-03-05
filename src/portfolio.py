import math
import os

from tinydb import TinyDB, Query
import constants as ct
from logger import Logger
from threading import Lock

class Portfolio(object):
    DEBUG=True
    def __init__(self):
        # initialize portfolio db which holds our current stakes
        self.__portfolio = TinyDB('db/portfolio.json')
        self.__portfolio_lock = Lock()
        # initialize db which holds how much money we
        # have left to spend and how much we have made
        self.__wallet = TinyDB('db/wallet.json')
        self.__wallet_lock = Lock()

    @staticmethod
    def initialize_wallet(balance_in: int) -> None:
        """
        Initializes wallet db.

        :param balance_in: amount of capital available for investment
        :return: None
        """
        # Check if wallet is already initialized
        if os.path.exists('db/wallet.json'):
            if Portfolio.DEBUG:
                Logger.warn('Wallet already initialized')
            return

        # Initialize wallet
        with TinyDB('db/wallet.json') as db:
            db.insert({'in': balance_in, 'out': 0})

        if Portfolio.DEBUG:
            Logger.debug('Wallet initialized!')

    def set_watchdog(self, wd):
        self.__watchdog = wd

    @property
    def balance(self):
        self.__wallet_lock.acquire()
        result = self.__wallet.all()[0]['in']
        self.__wallet_lock.release()
        return result
        
    def __subtract_from_balance(self, amount: int):
        """
        Subtracts given currency amount from balance

        :returns: None
        """
        balance = self.balance
        self.__wallet_lock.acquire()
        self.__wallet.update({'in': balance - amount})
        self.__wallet_lock.release()

    @property
    def portfolio(self):
        """
        Returns portfolio in the shape of a dict indexed by
        ticker containing properties corresponding to each ticker.
        """
        self.__portfolio_lock.acquire()
        obj = {}
        for k in self.__portfolio:
            obj[k['ticker']] = k
        self.__portfolio_lock.release()
        return obj

    def sync_order_fills(self, orders: dict):
        """
        Synchronizes order fills to portfolio db.

        :param orders: dict from ticker (str) to tuple of (share_no (int), total_value (float))
        :return: None
        """
        self.__portfolio_lock.acquire()
        # cycle over each entry in dict and update share no. in db for ticker
        for ticker, info in orders.items():
            Logger.debug(f'Info for ticker {ticker}: {info}')
            share_no, total_value = info
            if self.__portfolio.contains(Query().ticker == ticker):
                self.__portfolio.update({'shares': share_no, 'stake': total_value}, Query().ticker == ticker)
            else:
                # create new row
                row = self.__get_empty_portfolio_entry(ticker)
                row['shares'] = share_no
                row['stake'] = total_value
                # insert said row
                self.__portfolio.insert(row)
        self.__portfolio_lock.release()
        Logger.debug('Synchronized portfolio')

    def get_asset(self, ticker: str) -> dict:
        """
        Returns row associated with ticker or None.
        """
        query = Query()
        self.__portfolio_lock.acquire()
        records = self.__portfolio.search(query.ticker == ticker)
        self.__portfolio_lock.release()

        # no hit must mean we have zero shares for this ticker
        if len(records) == 0:
            return None

        return records[0]

    def usd_to_shares(self, ticker: str, currency_am: int) -> int:
        """
        Converts USD to shares for a given stock ticker.
        """
        if not isinstance(ticker, str):
            raise TypeError('Expected str for ticker!')

        if not isinstance(currency_am, int) or currency_am <= 0:
            raise TypeError('Expected positive int for currency_am!')

        price = self.__watchdog.get_price(ticker)

        return math.floor(currency_am / price) if price > 0 else 0

    def get_tickers(self) -> list:
        """
        Returns tickers in portfolio.
        """
        return list(self.portfolio.keys())

    def __update_ticker(self, ticker: str, properties: dict) -> None:
        """
        Updates given ticker with given properties.
        """
        self.__portfolio_lock.acquire()
        self.__portfolio.update(properties, Query().ticker == ticker)
        self.__portfolio_lock.release()

    def get_wallet(self) -> dict:
        """
        Retrieves wallet.
        """
        self.__wallet_lock.acquire()
        result = self.__wallet.all()[0]
        self.__wallet_lock.release()
        return result

    def sell_all_shares(self, ticker: str, asset: dict):
        """
        doc
        """
        # asset = self.get_asset(ticker)

        # Update wallet to reflect sale
        profit = -asset['stake'] + asset['shares'] * self.__watchdog.get_price(ticker)
        profit += self.get_wallet()['out']

        self.__wallet_lock.acquire()
        self.__wallet.update({'out': profit})
        self.__wallet_lock.release()

        # Set shares and stake for ticker to  0
        self.__portfolio_lock.acquire()
        self.__portfolio.update({'shares': 0, 'stake':0}, Query().ticker == ticker)
        self.__portfolio_lock.release()

        Logger.info(f'Running profit estimate: {profit}')

    def add_ticker_if_inexistent(self, ticker: str) -> dict:
        """
        Adds ticker if it does not exist already to portfolio 
        and returns corresponding row.
        """
        # get ticker
        row = self.get_asset(ticker)

        if row is None:
            row = self.__get_empty_portfolio_entry(ticker)
            self.__portfolio_lock.acquire()
            self.__portfolio.insert(row)
            self.__portfolio_lock.release()

        return row

    def __get_empty_portfolio_entry(self, ticker: str) -> dict:
        return {'shares': 0, 'ticker': ticker, 'stake':0}

    def buy_shares(self, ticker: str, shares_no: int, currency_amount: int = -1):
        """
        Buys given amount of shares.
        """
        if currency_amount == -1:
            currency_amount = self.__watchdog.get_price(ticker) * shares_no

        if self.balance < currency_amount:
            Logger.error(f'Not enough balance to buy shares!')
            return

        row = self.add_ticker_if_inexistent(ticker)
        # run update query
        self.__update_ticker(ticker, {'shares': 0 if ct.LIVE_TRADING else shares_no, 'stake': 0 if ct.LIVE_TRADING else (row['stake'] + currency_amount)})
        # recalculate outstanding balance
        self.__subtract_from_balance(currency_amount)

        Logger.info(f'Bought {shares_no} shares of {ticker}')
        Logger.info(f'Purchasing balance {self.balance} {ct.CURRENCY_SYMBOL}')

