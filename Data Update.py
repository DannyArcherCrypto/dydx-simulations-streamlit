from dydx3 import Client
from web3 import Web3
import pandas as pd
import datetime as datetime

client = Client(
    host='https://api.dydx.exchange'
)

markets = client.public.get_markets()
markets = pd.DataFrame(markets.data['markets'])

for futures_local_name in markets.columns:
    print(futures_local_name)
    time_increment = '1HOUR'
    
    if time_increment == '1HOUR':
        time_delta = datetime.timedelta(hours=90)
    elif time_increment == '4HOURS':
        time_delta = datetime.timedelta(hours=360)
    elif time_increment == '1DAY':
        time_delta = datetime.timedelta(days=90)
        
    timeseries = pd.DataFrame()
    new_results = True
    today = datetime.datetime.now()
    
    try: #if existing file
        timeseries = pd.read_pickle("./Price_Data/" + str(time_increment) + "/" + str(futures_local_name) + ".pkl")
        max_time = timeseries['startedAt'].max()
        start_time = datetime.datetime.strptime(max_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        print(start_time)
    
    except FileNotFoundError: #if no existing file
        initial = '2021-02-26T00:00:00.000Z'
        start_time = datetime.datetime.strptime(initial, "%Y-%m-%dT%H:%M:%S.%fZ")
        print(start_time)
        
    while new_results == True:
        
        end_time = start_time + time_delta
        api_result = client.public.get_candles(
            market=futures_local_name,
            resolution=str(time_increment),
            from_iso=start_time,
            to_iso=end_time,
            limit=90
        )

        api_result = pd.DataFrame(api_result.data['candles'])
        timeseries = pd.concat([timeseries, api_result])
        timeseries = timeseries.drop_duplicates(subset=['startedAt'])    
        start_time = end_time
        
        timeseries.to_pickle("./Price_Data/" + str(time_increment) + "/" + str(futures_local_name) + ".pkl")
        timeseries = pd.read_pickle("./Price_Data/" + str(time_increment) + "/" + str(futures_local_name) + ".pkl")
        
        if start_time > today:
            new_results = False