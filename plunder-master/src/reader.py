from telegram.client import Telegram
from trader import Trader
import re
from logger import Logger
import credentials as cd
import constants as ct
import traceback

# Author: drw
# Date:   Jan 2021

# debug flag
DEBUG = True

class Reader(object):
    def __init__(self):
        # initialize trader
        self.__trader = Trader()

    def __payload_contract(self, payload: dict):
        if not isinstance(payload, dict):
            raise TypeError('Expected dict for payload!')

    def __new_msg_handler(self, payload: dict) -> None:
        self.__payload_contract(payload)
        # validate packet
        if 'message' not in payload or 'chat_id' not in payload['message']:
            raise Exception('Malformed payload')

        chat_id = payload['message']['chat_id']

        # filter if filter is enabled
        if ct.TG_FILTER_ENABLED and chat_id not in ct.TG_CHAT_ID_FILTER:
            if DEBUG:
                Logger.debug(f'Ignoring messages from: {chat_id}')
            return

        if DEBUG:
            Logger.debug(f'payload: {payload}')

        # handle by type
        if payload['@type'] == 'updateNewMessage':
            self._handle_update_new_message(payload['message']['content'])

    def _handle_update_new_message(self, payload: dict) -> None:
        self.__payload_contract(payload)
        # handle by type
        if payload['@type'] == 'messageText' and ('text' in payload):
            self._handle_message_text(payload['text'])

    def _handle_message_text(self, payload: dict) -> None:
        self.__payload_contract(payload)
        # handle by type
        if payload['@type'] == 'formattedText' and 'text' in payload:
            actual_text = payload['text']


            tickers = self._make_out_tickers(actual_text)

            if DEBUG:
                Logger.debug(f'Text received {actual_text}')

            negative_bias = False
            # get lowercase text
            low_actual_text = actual_text.lower()
            # see if we can find any negative bias
            for negative_word in ct.NEGATIVE_WORDS:
                if negative_word in low_actual_text:
                    negative_bias = True
                    break

            # buy each ticker
            for ticker in tickers:
                Logger.debug(f'>> TICKER: {ticker}')
                self.__trader.handle_buy_sig(ticker, negative_bias=negative_bias)
        
    def _make_out_tickers(self, txt: str) -> [str]:
        """
        Returns a list of stock tickers.
        """
        if not isinstance(txt, str):
            raise TypeError('Expected str for txt!')

        return re.findall(r'\b[A-Z]{3,5}\b[.!?]?', txt) 

    def run(self):
        # authenticate
        tg = Telegram(api_id=cd.TG_API_ID, api_hash=cd.TG_API_HASH, phone=cd.TG_PHONE_NO, database_encryption_key=cd.TG_DB_KEY)
        tg.login()
        # setup handlers 
        tg.add_message_handler(self.__new_msg_handler)
        # wait for async callbacks
        tg.idle()

if __name__ == '__main__':
    try:
        reader = Reader()
        reader.run()
    except Exception as e:
        Logger.error(f'Exception happened: {e}')
        Logger.error(traceback.format_exc())
