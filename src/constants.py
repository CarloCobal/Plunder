# default amount of currency worth of stock to buy
DEFAULT_BALANCE_IN=1000
DEFAULT_CURRENCY_BUY_AMOUNT=1000
WATCHDOG_UPDATE_PERIOD=30
SELL_THRESH_MULTIPLIER=1.5 #i.e. 1.1 means we sell when we've made a profit 
                           # or taken a loss of at least 10%
MAX_TICKER_PRICE=0.002
MAX_TICKER_NO_FILTER_PRICE=0.0009 # anything at this price or below will not be subject to word filter
BUY_LIMIT_PRICE_MULTIPLIER=1.1
SELL_LIMIT_PRICE_MULTIPLIER=0.95
CURRENCY_SYMBOL='USD'
LIVE_TRADING=True

# TELEGRAM SPECIFIC
# only listen for messages from these user ids
TG_USER_ID_FILTER=['813772733']
# only listen for messages from these chat ids
TG_CHAT_ID_FILTER=[429000, -1001489461174]
# filter flag
TG_FILTER_ENABLED=True


# negative words
NEGATIVE_WORDS = ['tenbagger', 'chased', 'on volume', 'custo play', 'custodian', 'new high', 'new highs', 'hod', 'boom', 'booom', 'boooom', 'booooom', 'boooooom', 'high of']
