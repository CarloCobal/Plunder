from rauth import OAuth1Service
import credentials as cd
import webbrowser
import random
import json
from logger import Logger
from collections import defaultdict
import numpy


class ETrader(object):
    def __init__(self):
        etrade = OAuth1Service(
            name="etrade",
            consumer_key=cd.CONSUMER_KEY,
            consumer_secret=cd.CONSUMER_SECRET,
            request_token_url="https://api.etrade.com/oauth/request_token",
            access_token_url="https://api.etrade.com/oauth/access_token",
            authorize_url="https://us.etrade.com/e/t/etws/authorize?key={}&token={}",
            base_url="https://api.etrade.com")

        
        # Step 1: Get OAuth 1 request token and secret
        request_token, request_token_secret = etrade.get_request_token(
            params={"oauth_callback": "oob", "format": "json"})

        # Step 2: Go through the authentication flow. Login to E*TRADE.
        # After you login, the page will provide a text code to enter.
        authorize_url = etrade.authorize_url.format(etrade.consumer_key, request_token)
        Logger.debug(f'Go to {authorize_url} for token and enter it:')
        text_code = input("Please accept agreement and enter text code from browser: ")

        # Step 3: Exchange the authorized request token for an authenticated OAuth 1 session
        self.__session = etrade.get_auth_session(request_token,
                                      request_token_secret,
                                      params={"oauth_verifier": text_code})

        # Add parameters and header information
        self.__headers = {"Content-Type": "application/xml", "consumerKey": cd.CONSUMER_KEY}
        Logger.info('Authenticated')

    def get_ticker_price(self, ticker: str) -> float:
        """
        Gets the latest price for the given ticker.
        """
        # URL for the API endpoint
        url = cd.BASE_URL + "/v1/market/quote/" + ticker + ".json"

        # Make API call for GET request
        response = self.__session.get(url)

        if response is not None and response.status_code == 200:
            parsed = json.loads(response.text)

            # Handle and parse response
            data = response.json()
            if data is not None and "QuoteResponse" in data and "QuoteData" in data["QuoteResponse"]:
                for quote in data["QuoteResponse"]["QuoteData"]:
                    if quote is not None and "All" in quote and "lastTrade" in quote["All"]:
                        return quote["All"]["lastTrade"]

            Logger.warn(f'Could not retrive price for ticker {ticker}')
            return -1

    def get_filled_orders(self, marker=None) -> dict:
        """
        Returns a dict of ticker -> (share no., value)
        """
        # Make up url
        url = cd.BASE_URL + "/v1/accounts/" + cd.ACCOUNT_ID_KEY + "/orders.json"
        # Make up headers
        headers = {"consumerkey": cd.CONSUMER_KEY}

        # Make up client order id
        params_indiv_fills = {"status": "INDIVIDUAL_FILLS"}

        if marker is not None:
            Logger.debug(f'Retrieving for marker {marker}')
            params_indiv_fills['marker'] = marker

        response_indiv_fills = self.__session.get(url, header_auth=True, params=params_indiv_fills, headers=headers)

        Logger.debug("Individual Fills Orders:")
        # Handle and parse response
        if response_indiv_fills.status_code == 204:
            Logger.debug(f"Response Body: {response_executed}")
            return {}
        elif response_indiv_fills.status_code == 200:
            parsed = json.loads(response_indiv_fills.text)
            Logger.debug(f'Got 200 back {parsed}')

            # Initialize collection of ticker -> (no. of shares, total ticker value)
            ticker_to_share_no = {}
            ticker_to_share_no = defaultdict(lambda: (0, 0), ticker_to_share_no)

            # Verify integrity of JSON
            if parsed is not None and 'OrdersResponse' in parsed and 'Order' in parsed['OrdersResponse']:
                orders = parsed['OrdersResponse']['Order']
                marker = parsed['OrdersResponse']['marker'] if 'marker' in parsed['OrdersResponse'] else None

                for order in orders:
                    if 'OrderDetail' in order and len(order['OrderDetail']) > 0 and 'orderValue' in order['OrderDetail'][0] and 'Instrument' in order['OrderDetail'][0]:
                        instrument = order['OrderDetail'][0]['Instrument']
                        order_value = order['OrderDetail'][0]['orderValue']

                        if len(instrument) < 1:
                            Logger.warn('Less than one instrument in order detail. Skipping..')
                            continue

                        instrument = instrument[0]
                        # extract operands for element-wise tuple addition
                        x = ticker_to_share_no[instrument['Product']['symbol']]
                        y = (instrument['filledQuantity'], order_value)
                        order_action = instrument['orderAction']

                        # update collection entry
                        x = tuple(numpy.add(x, y)) if order_action == 'BUY' else tuple(numpy.subtract(x, y)) 
                        x = (int(x[0]), x[1])
                        ticker_to_share_no[instrument['Product']['symbol']] = x
                    else:
                        Logger.warn('Malformed order. Skipping...')
                        continue

                dict1 = dict(ticker_to_share_no)
                if marker:
                    dict2 = self.get_filled_orders(marker)
                    return self.__merge_dicts(dict1, dict2)
                return dict1
        else:
            Logger.warn(f'Invalid status code; response: {response_indiv_fills.text}')
        
        return {}

    def __merge_dicts(self, dict1: dict, dict2: dict) -> dict:
        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            raise TypeError('Expected dicts for dict1 and dict2!')

        final_dict = {}
        final_dict = defaultdict(lambda: (0, 0), final_dict)
        # add elements in dict1
        for key1 in dict1:
            final_dict[key1] = tuple(numpy.add(final_dict[key1], dict1[key1]))
            final_dict[key1] = (int(final_dict[key1][0]), final_dict[key1][1])

        # add the elements particular to dict2
        for key2 in dict2:
            final_dict[key2] = tuple(numpy.add(final_dict[key2], dict2[key2]))
            final_dict[key2] = (int(final_dict[key2][0]), final_dict[key2][1])

        return dict(final_dict)

    def place_order(self, price_type: str, order_term: str, limit_price: str, symbol: str, order_action: str, quantity: int) -> (bool, list):
        """
        Returns tuple of success_flag (bool) and order objects (list).
        """

        preview_id, order_html = self.preview_order(price_type, order_term, limit_price, symbol, order_action, quantity)

        if preview_id == 0 or len(order_html) <= 0:
            Logger.error('Order preview was invalid. Not placing order!')
            return False, []

        # Make up url
        url = cd.BASE_URL + "/v1/accounts/" + cd.ACCOUNT_ID_KEY + "/orders/place.json"

        # Make up client order id
        client_order_id = random.randint(1000000000, 9999999999)

        # Add payload for POST Request
        payload = f"""<PlaceOrderRequest>
                       <orderType>EQ</orderType>
                       <clientOrderId>{client_order_id}</clientOrderId>
                       <PreviewIds>
                           <previewId>{preview_id}</previewId>
                           <cashMargin>CASH</cashMargin>
                       </PreviewIds>{order_html}
                   </PlaceOrderRequest>"""

        # print(f'posting payload {payload}')
        # Make API call for POST request
        response = self.__session.post(url, header_auth=True, headers=self.__headers, data=payload)

        Logger.debug(f'place response {response.text}')

        if response is not None and response.status_code == 200:
            parsed = response.json()

            if parsed is not None and 'PlaceOrderResponse' in parsed and 'Order' in parsed['PlaceOrderResponse']:
                order = parsed['PlaceOrderResponse']['Order']

                return True, order
            else:
                Logger.error('Error: did not obtain place order response!')
        else:
            Logger.error('Error: place_order did not return valid status code')
        
        return False, []

    def preview_order(self, price_type: str, order_term: str, limit_price: str, symbol: str, order_action: str, quantity: int) -> (int, str):
        """
        Returns preview_id and order_html if successful. Otherwise, it returns (0, '').
        """

        # Make up url
        url = cd.BASE_URL + "/v1/accounts/" + cd.ACCOUNT_ID_KEY + "/orders/preview.json"

        # Make up client order id
        client_order_id = random.randint(1000000000, 9999999999)

        preview_id = None

        # Create order html
        order_html = f"""
                       <Order>
                           <allOrNone>false</allOrNone>
                           <priceType>{price_type}</priceType>
                           <orderTerm>{order_term}</orderTerm>
                           <marketSession>REGULAR</marketSession>
                           <stopPrice></stopPrice>
                           <limitPrice>{limit_price}</limitPrice>
                           <Instrument>
                               <Product>
                                   <securityType>EQ</securityType>
                                   <symbol>{symbol}</symbol>
                               </Product>
                               <orderAction>{order_action}</orderAction>
                               <quantityType>QUANTITY</quantityType>
                               <quantity>{quantity}</quantity>
                           </Instrument>
                       </Order>"""

        # Add payload for POST Request
        payload = f"""<PreviewOrderRequest>
                       <orderType>EQ</orderType>
                       <clientOrderId>{client_order_id}</clientOrderId>{order_html}
                   </PreviewOrderRequest>"""

        Logger.debug(f'posting payload {payload}')
        # Make API call for POST request
        response = self.__session.post(url, header_auth=True, headers=self.__headers, data=payload)

        Logger.debug(f'preview response {response.text}')
        
        # check if response returned valid status
        if response is not None and response.status_code == 200:
            # deserialize json
            parsed = response.json()

            # check integrity of json
            if parsed is not None and 'PreviewOrderResponse' in parsed and 'PreviewIds' in parsed['PreviewOrderResponse']:
                preview_ids = parsed['PreviewOrderResponse']['PreviewIds']

                # make sure we got at least one preview id
                if len(preview_ids) > 0 and 'previewId' in preview_ids[0]:
                    preview_id = preview_ids[0]['previewId']
                    Logger.debug(f'Preview id: {preview_id}')
                    return preview_id, order_html
                else:
                    Logger.error('No preview ids returned!')
            else:
                Logger.error('Malformed valid response!')

        return 0, ''
