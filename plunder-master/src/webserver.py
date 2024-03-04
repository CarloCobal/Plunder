from flask import Flask, request, render_template, url_for, Response
from functools import wraps
from tinydb import TinyDB, Query
import json
import constants as ct

app = Flask(__name__)

wallet_table = TinyDB('../db/wallet.json')
portfolio_table = TinyDB('../db/portfolio.json')
watchlist_table = TinyDB('../db/watchlist.json')

MANAGE_PW = 'larryhadsex'

@app.route("/")
def index():
    response = app.make_response("""       _                 _             _____  __  
      | |               | |           |  _  |/  | 
 _ __ | |_   _ _ __   __| | ___ _ __  | |/' |`| | 
| '_ \| | | | | '_ \ / _` |/ _ \ '__| |  /| | | | 
| |_) | | |_| | | | | (_| |  __/ |    \ |_/ /_| |_
| .__/|_|\__,_|_| |_|\__,_|\___|_|     \___(_)___/
| |                                               
|_|  aint my web dev skills sick

Check /status for more info.

Change log:
    - 01/31 added some features for admins
    - 01/31 moved to AWS
    - 01/27 added bad word filter
    - 01/26 website is up >;D
    - 01/26 tickers that are not bought are no longer added to portfolio
    """)

    response.headers["content-type"] = "text/plain"
    return response

def check_auth(usr, pw):
    return usr == 'Quaid' and pw == MANAGE_PW

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/manage')
@requires_auth
def secret_page():
    return render_template('manage.html')

@app.route('/manage', methods=['POST'])
@requires_auth
def manage_post():
    new_budget = request.form['new_budget']

    # validate budget
    if new_budget.isnumeric():
        new_budget = int(new_budget)
    else:
        return 'Budget must be an integer.'

    # make sure budget is within valid range
    if not (new_budget < 0 or new_budget > 99999):
        # update wallet
        wallet_table.update({'in': new_budget})
        # great success
        return f'<p><img src={url_for("static", filename="success.jpg")}/></p><p><a href="/status">Take me back to the status page</a>'
    else:
        return 'Invalid budget.'

@app.route('/status', methods=['POST'])
@requires_auth
def update_config():
    request.form = dict(request.form)

    for k in request.form:
        if '_st' in k:
            ticker = k.split('_st')[0]
            print(f'updating {ticker} to {request.form[k]}')
            watchlist_table.update({"threshold": float(request.form[k])}, Query().ticker == ticker)

    print(f'got the following: {request.form}')
    return 'Success. <a href="javascript:history.back()">Go Back?</a>'

@app.route('/status')
@requires_auth
def status():
    result = ''
    profit = 0.0

    result += '<style>table, td { border: 1px solid black; border-collapse: collapse;}</style>'
    # define parent table
    result += '<table style="border: 0;">'
    # add first entry
    result += '<tr><td style="border: 0;">'
    result += '<h2>Portfolio: </br></h2>'
    result += '<table >'
    result += '<tr><td>Ticker</td><td>Avg price</td><td>Stake</td><td>Share #</td><td>Status</td></tr>'

    # cycle over portfolio
    for entry in portfolio_table:
        share_no = entry['shares']
        stake = entry['stake']
        ticker = entry['ticker']

        if share_no > 0:
            status = '<td style="background-color:#e0d900">HOLD</td>'
        elif int(share_no) == 0 and int(stake) == 0:
            status = '<td style="background-color:#f2780c">CANCELLED</td>'
        else:
            profit += -stake 
            status = '<td style="background-color:#6dba02">SOLD</td>'
        avg_price = 'N/A' if share_no == 0 else round(stake/share_no, 5)
        info = f'<td>{avg_price}</td><td>{round(stake, 4)}</td><td>{share_no}</td>{status}'
        result += f'<tr><td>{ticker}</td>{info}</tr>'
    result += '</table>'
    # end parent table column, start new one
    result += '</td><td style="vertical-align:top; border: 0; padding-left: 20px;">'
    result += '<h2>Watchlist: </br></h2>'
    result += '<form method="POST">'
    result += '<table>'
    result += '<tr><td>Ticker</td><td>Sell at</td><td></td></tr>'
    for entry in watchlist_table:
        result += f'<tr><td>{entry["ticker"]}</td><td><input type="text" name={entry["ticker"]}_st value="{round(entry["threshold"], 4)}" size=8></td><td><input type="submit" value="update"/></td></tr>'
    result += '</table>'
    result += '</form>'
    # close off parent table
    result += '</td></tr></table>'

    result += '<h2>Wallet: </br></h2>'
    result += '<form action="/manage" method="POST">'
    for entry in wallet_table:
        result += f'Available to invest: <input type="text" name="new_budget" value={round(entry["in"], 4)} {ct.CURRENCY_SYMBOL} size=5/>USD</br>'
        result += f'Actual total profit: {profit} {ct.CURRENCY_SYMBOL}</br>'
        result += f'Estimated profit (from 02/02): {round(entry["out"], 4)} {ct.CURRENCY_SYMBOL}</br>'
        result += '</br>'

    result += '<input type="submit" value="update"/>'
    result += '</form>'
    result += '<h2>Config: </br></h2>'
    result += f'Max ticker price: {ct.MAX_TICKER_PRICE} {ct.CURRENCY_SYMBOL}</br>'
    result += f'Buy increments: {ct.DEFAULT_CURRENCY_BUY_AMOUNT} {ct.CURRENCY_SYMBOL}</br>'
    result += f'Sell threshold: {ct.SELL_THRESH_MULTIPLIER}x purchase price</br>'
    return result

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
