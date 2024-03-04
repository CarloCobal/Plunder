import constants as ct

from portfolio import Portfolio
from watchdog import Watchdog
from logger import Logger
from etrader import ETrader


class Trader(object):
    def __init__(self):
        """
        Sets up trader with given parameters.

        :return: None
        """
        # Setup etrade
        self.__etrader = ETrader()
        # Initialize portfolio
        Portfolio.initialize_wallet(ct.DEFAULT_BALANCE_IN)
        self.__portfolio: Portfolio = Portfolio()
        # Initialize watchdog
        self.__watchdog: Watchdog = Watchdog(self.__portfolio, self.handle_sell_sig, self.__etrader.get_filled_orders, self.__etrader.get_ticker_price)

        self.__watchdog.daemon = True
        self.__watchdog.start()
        
        # hand off pointer to portfolio to set of latest prices
        self.__portfolio.set_watchdog(self.__watchdog)

    def __ticker_contract(self, ticker: str) -> None:
        if not isinstance(ticker, str):
            raise TypeError('Expected str for ticker!')

    def handle_buy_sig(self, ticker: str, negative_bias: bool = False) -> None:
        """
        Handles BUY signal for stock with given ticker.
        """
        self.__ticker_contract(ticker)

        # Check if we already own ticker
        if self.__portfolio.get_asset(ticker):
            Logger.warn(f'Already own {ticker}!')
            return

        # Get latest price
        current_price = self.__watchdog.get_price(ticker)

        if current_price is None or current_price <= 0:
            Logger.error(f'Ticker {ticker} has a price <= 0. Not buying any shares.')
            return

        if current_price > ct.MAX_TICKER_PRICE:
            Logger.error(f'Ticker {ticker} has a price higher than max allowed {ct.MAX_TICKER_PRICE}')
            return

        if negative_bias and current_price > ct.MAX_TICKER_NO_FILTER_PRICE:
            Logger.error(f'Ticker {ticker} has negative bias and is > no filter price {ct.MAX_TICKER_NO_FILTER_PRICE}')
            return

        # Calculate number of shares based on currency amount
        shares_no = self.__portfolio.usd_to_shares(ticker, ct.DEFAULT_CURRENCY_BUY_AMOUNT)
        # Calculate limit price
        limit_price = round(current_price * ct.BUY_LIMIT_PRICE_MULTIPLIER, 4)


        if limit_price * shares_no > self.__portfolio.balance:
            Logger.error(f'Not placing order for {ticker}: cost at limit price: ({limit_price*shares_no}) > balance ({self.__portfolio.balance}).')
            return
        else:
            Logger.info(f'We have enough balance ({self.__portfolio.balance}) to make purchase at limit price; cost: {shares_no*limit_price}')

        # Add ticker to portfolio if needed
        self.__portfolio.add_ticker_if_inexistent(ticker)

        if ct.LIVE_TRADING:
            Logger.warn('Placing LIVE BUY order!')
            valid, order = self.__etrader.place_order(price_type='LIMIT', order_term='GOOD_FOR_DAY', limit_price=limit_price, symbol=ticker, order_action='BUY', quantity=shares_no)

            if valid:
                Logger.info('Successful order. Updating portfolio & subscribing!')
                self.__portfolio.buy_shares(ticker, shares_no, limit_price)
                self.__watchdog.subscribe(ticker, current_price * ct.SELL_THRESH_MULTIPLIER, '>')
                Logger.info('Subscribed')
        else:
            self.__portfolio.buy_shares(ticker, shares_no, limit_price)
            self.__watchdog.subscribe(ticker, current_price * ct.SELL_THRESH_MULTIPLIER, '>')
            


    def handle_sell_sig(self, ticker: str) -> None:
        """
        Handles SELL signal for stock with given ticker.
        """
        row = self.__portfolio.get_asset(ticker)

        if row:
            current_price = self.__watchdog.get_price(ticker)

            profit = -row['stake'] + row['shares'] * current_price
            Logger.info(f'stake: {row["stake"]} shares: {row["shares"]} current_price: {current_price}')
            Logger.info(f'>> SELLING {ticker} for a profit of {profit}')

            limit_price = round(current_price * ct.SELL_LIMIT_PRICE_MULTIPLIER, 4)

            if ct.LIVE_TRADING:
                if row['shares'] < 1:
                    Logger.error(f'Cannot sell: no shares. Maybe none were filled?')
                    return

                valid, order = self.__etrader.place_order(price_type='LIMIT', order_term='GOOD_FOR_DAY', limit_price=limit_price, symbol=ticker, order_action='SELL', quantity=row['shares'])
                
                if not valid:
                    Logger.error(f'Unsuccessful SELL order for {ticker}')
                    self.__watchdog.unsubscribe_all(ticker)
                    return

            self.__watchdog.unsubscribe_all(ticker)
            self.__portfolio.sell_all_shares(ticker, row)
        else:
            Logger.error('Attempted to sell unowned stock!')


