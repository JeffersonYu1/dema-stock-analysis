from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import alpaca_trade_api as tradeapi
import math

# Options
ticker = ''
short_interval = 14  # optimal interval lengths based on testing
long_interval = 23
frequency = 'day'  # 1Min, 2Min, 15Min, day
curr = 'DEMA'  # current strategy, DEMA or SMA
fts = '2020-10-01T09:30:00-04:00'  # start time
tts = '2021-10-08T09:30:00-04:00'  # end time


def DEMA_Calc(data, interval, column):
    EMA = data[column].ewm(span=interval, adjust=False).mean()
    DEMA = 2*EMA - EMA.ewm(span=interval, adjust=False).mean()
    return DEMA


def SMA_Calc(data, interval, column):
    SMA = data[column].rolling(window=interval).mean()
    return SMA


def Run_Strategy(data, name):
    buy_list = []  # Create a list to store the price at which to buy
    sell_list = []  # Create a list to store the price at which to sell
    flag = False  # Create a flag to determine when the indicators cross
    last_buy = -1
    # Loop through the data
    for i in range(0, len(data)):
        # Check if Short Term DEMA crosses Long Term DEMA
        if data[name + '_Short'][i] > data[name + '_Long'][i]:
            if flag == False:
                buy_list.append(data['close'][i])
                sell_list.append(np.nan)
                flag = True
                last_buy = data['close'][i]
            else:
                buy_list.append(np.nan)
                sell_list.append(np.nan)
        # Check if Short Term DEMA crosses Long Term DEMA
        elif data[name + '_Short'][i] < data[name + '_Long'][i]:
            if flag == True and data['close'][i] > last_buy*1.07:
                buy_list.append(np.nan)
                sell_list.append(data['close'][i])
                flag = False
                last_buy = -1
            else:
                buy_list.append(np.nan)
                sell_list.append(np.nan)
        else:  # Else they didn't cross
            buy_list.append(np.nan)
            sell_list.append(np.nan)
    # Store the Buy and Sell signals in the data set
    data['Buy_' + name] = buy_list
    data['Sell_' + name] = sell_list


# authentication and connection details
api_key = ''
api_secret = ''
base_url = 'https://paper-api.alpaca.markets'

# instantiate REST API
api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

# Get account information.
account = api.get_account()
# print(account)

# Check if account is restricted from trading.
if account.trading_blocked:
    print('Account is currently restricted from trading.')

# Check how much money we can use to open new positions.
# print('${} is available as buying power.'.format(account.buying_power))

# Get data for a stock
df = api.get_barset(ticker, frequency, limit=1000,
                    start=fts, end=tts).df
# print(df)

# Convert multiindex df into single index
df2 = pd.concat([df[ticker]['open'], df[ticker]['close']], axis=1)
# df2.index = df2.index.date

for i in range(len(df2)):
    if df2['close'][i] == 0:
        df2.drop(df2.index[i])

# Calculate Short- and Long-Term Averages
df2['DEMA_Short'] = DEMA_Calc(df2, short_interval, 'close')
df2['DEMA_Long'] = DEMA_Calc(df2, long_interval, 'close')
# df2['SMA_Short'] = SMA_Calc(df2, short_interval, 'close')
# df2['SMA_Long'] = SMA_Calc(df2, long_interval, 'close')


# Run Strategies
# Run_Strategy(df2, 'SMA')
Run_Strategy(df2, 'DEMA')

# Name buy and sell strats
buy_strat = 'Buy_' + curr
sell_strat = 'Sell_' + curr

amount = 300
starting_amount = amount
# print("Original Balance : {}".format(amount))
first_buy = -1
last_buy = -1

for i in range(len(df2)):
    # print(df2['Buy_DEMA'][i])
    if first_buy == -1 and np.isnan(df2[buy_strat][i]) == False:
        first_buy = df2[buy_strat][i]
        amount -= first_buy
        last_buy = first_buy
        print("First Buy Price : ${:.2f}".format(first_buy))
        # print("Balance After First Buy : {}".format(amount))
    elif np.isnan(df2[buy_strat][i]) == False:
        last_buy = df2[buy_strat][i]
        amount -= df2[buy_strat][i]
    elif np.isnan(df2[sell_strat][i]) == False:
        amount += df2[sell_strat][i]
        last_buy = -1
    else:
        continue
if last_buy != -1:
    amount += last_buy
# print("Final Balance : {}".format(amount))
profit = round(amount - starting_amount, 2)
percent_profit = profit/first_buy
print("Profit : ${:.2f}".format(profit))
print("% Profit : {:.2%}".format(percent_profit))

# create subplot
f = plt.figure(figsize=(16, 9))
ax = f.add_subplot()

# add data
ax.plot(df2['close'], color='g', label='Close Price', alpha=0.3)
# ax.plot(df2[curr + '_Short'], color='r', label=(curr + '_Short'), alpha=1.0)
ax.plot(df2[curr + '_Long'], color='g', label=(curr + '_Long'), alpha=1.0)
# ax.plot(df2['DEMA_Short'], color='r', label='DEMA_Short', alpha=1.0)
# ax.plot(df2['DEMA_Long'], color='g', label='DEMA_Long', alpha=1.0)

# add buy/sell signals
ax.scatter(x=df2.index, y=df2['Buy_' + curr], color='g',
           label=('Buy Signal (' + curr + ')'), marker='^', alpha=1)
ax.scatter(x=df2.index, y=df2['Sell_' + curr], color='r',
           label=('Sell Signal (' + curr + ')'), marker='v', alpha=1)

# set labels, legend, and title
ax.legend(loc="upper left")
ax.set_title(ticker + ' Historical Price')
ax.set_xlabel('Date')
ax.set_ylabel('Stock Price')

# Use automatic StrMethodFormatter
ax.yaxis.set_major_formatter('${x:1.2f}')

plt.show()
