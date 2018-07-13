import threading
import pandas as pd
from datetime import datetime
from decimal import *
import twitter
from auth import *
from binance.client import Client
global client
client = Client("V40EnBQtXZZLdxv7r7DmVqfJ6NFGdHn1Wp8OhTr9Nq5BnpQNl1qqdRZORGRsaYTu", binance_private_key)

# Settings
amt = 20 # Trading Amount in USD
tradingSymbol = "NEOUSDT"
# Arrays
buys = []
sells = []
# Global Variables
isRunning = True
isOrderOpen = False 
uptrend = 0
refreshSpeed = 1.0 # seconds
lastPrice = 0
quant = {'init': amt, 'usd': amt, 'qa':0} 

# Functions
def tweet(x):
    api = twitter.Api(consumer_key,consumer_secret,access_token_key,access_token_secret)
    status = api.PostUpdate(x)

def srcAvg(x):
    avg = 0.0
    for i in range(1,5):     # len(x) -> 9
        avg += float(x[i])
    return avg / 4           # return average of open, high, low, close

def s(x, r = 3): # str(round())
    return str(round(x,r))

def ma(isExp, length, klines, closesOnly = 1):
    # klines = client.get_historical_klines("ETHUSDT", Client.KLINE_INTERVAL_1MINUTE, "1 hour ago UTC")
    if closesOnly:
        closes = pd.Series(data = [x[4] for x in klines])
    else:
        closes = pd.Series(data = [srcAvg(x) for x in klines])
    if isExp:
        return list(closes.ewm(span=length).mean())[-1]
    else:
        return list(closes.rolling(window=length).mean())[-1]

def checkPrices():
    global refreshSpeed, uptrend, lastPrice, isRunning, isOrderOpen, tradingSymbol, quant
    if quant['usd'] < quant['init'] * 9/10:
        isRunning = False          # Stop program if losses exceed 10%
        
    prices = client.get_all_tickers()
    curPrice = float([x['price'] for x in prices if x['symbol'] == tradingSymbol][0])
    quant['qa'] = quant['usd'] / curPrice    # set Trading Amount in Quote Asset or Symbol
    candles = client.get_historical_klines(tradingSymbol, Client.KLINE_INTERVAL_1DAY, "1 month ago UTC")
    temp = uptrend           
    maClose = ma(True, 5, candles)       # EMAs
    maMiddle = ma(True, 8, candles, 0)
    maFar = ma(True, 13, candles, 0)
    dif = 100 * abs(maClose - maFar) / curPrice # Percentage difference in EMAs
    if dif > 5:
        refreshSpeed = 60.0
    elif dif > 0.5:
        refreshSpeed = dif * 10.0
    else:
        refreshSpeed = 1.0
    if maClose > maFar:
        uptrend = 1 
    elif maClose < maFar: 
        uptrend = 0
    if not isOrderOpen and uptrend > temp:
        tweet("bot: Buy " + tradingSymbol + " at "+ s(curPrice, 0))
        print("buy at "+s(curPrice*1.0005))
        order = client.order_market_buy(
            symbol= tradingSymbol,
            quantity=quant['qa'])
        buys.append(curPrice*1.0005)
    if isOrderOpen and maClose < maMiddle:
        tweet("bot: Sell " + tradingSymbol + " at "+ s(curPrice, 0))
        print("sell at "+s(curPrice*0.9995) + " Profit: " + s(buys[-1]))
        order = client.order_market_sell(
            symbol= tradingSymbol,
            quantity=quant['qa'])
        quant['usd'] = quant['qa'] * curPrice*0.9995   # Update USD value of Trading Amount
        sells.append(curPrice*0.9995)
    isOrderOpen = len(buys) - len(sells)
    if isRunning:
        threading.Timer(refreshSpeed, checkPrices).start()
    if abs(lastPrice - curPrice) / curPrice > 0.001:
        print(s(curPrice, 2) + " d: " + s(dif) + " up: " + s(uptrend) + " re: " +
              str(int(round(refreshSpeed, 0))) + "s MAs:" + s(maClose) + " " + s(maMiddle) + " " + s(maFar))
    lastPrice = curPrice

print(tradingSymbol + ", MA % Difference, isUptrend, Refresh Speed")
# Start Trading
checkPrices()
