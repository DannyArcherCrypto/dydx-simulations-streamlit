import streamlit as st
from dydx3 import Client
from web3 import Web3
import pandas as pd
import datetime as datetime
import json
import numpy as np
from random import randrange
from matplotlib.pyplot import figure
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal
from scipy.stats import norm


st.title("DYDX Risk Station")
st.header("Select Perpetuals")

options = st.multiselect(
     'Which Perpetuals are in your portfolio?',
     ['BTC-USD', 'SOL-USD', 'ETH-USD', 'LINK-USD', 'AAVE-USD', 'UNI-USD', 'SUSHI-USD', 'YFI-USD',
     '1INCH-USD', 'AVAX-USD', 'SNX-USD', 'CRV-USD', 'UMA-USD', 'DOT-USD', 'DOGE-USD', 'MATIC-USD',
     'MKR-USD', 'FIL-USD', 'ADA-USD', 'ATOM-USD', 'COMP-USD', 'BCH-USD', 'LTC-USD', 'EOS-USD',
     'ALGO-USD', 'ZRX-USD', 'XMR-USD', 'ZEC-USD', 'ENJ-USD', 'XLM-USD', 'ETC-USD', 'NEAR-USD', 
     'RUNE-USD', 'CELO-USD', 'ICP-USD', 'TPX-USD', 'XTZ-USD'])

no_selections = len(options)
df_size = pd.DataFrame(columns=["name", "position"])

for perp in options:
     st.subheader(perp)
     size = st.number_input(str(perp) + ' Position Size')
     new_row = {'name':str(perp), 'position':size}
     df_size = df_size.append(new_row, ignore_index=True)

Initial_USDC = st.number_input('Account Equity (USDC)')
st.write('Account USDC: ', Initial_USDC)

if st.button('Get Risk Statistics'):
     ########### GET DATA ##############
     client = Client(host='https://api.dydx.exchange')
     for perp in options:
          print(perp)
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
               timeseries = pd.read_pickle("./Price_Data/" + str(time_increment) + "/" + str(perp) + ".pkl")
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
                    market=perp,
                    resolution=str(time_increment),
                    from_iso=start_time,
                    to_iso=end_time,
                    limit=90
               )

               api_result = pd.DataFrame(api_result.data['candles'])
               timeseries = pd.concat([timeseries, api_result])
               timeseries = timeseries.drop_duplicates(subset=['startedAt'])    
               start_time = end_time
               
               timeseries.to_pickle("./Price_Data/" + str(time_increment) + "/" + str(perp) + ".pkl")
               timeseries = pd.read_pickle("./Price_Data/" + str(time_increment) + "/" + str(perp) + ".pkl")
               
               if start_time > today:
                    new_results = False
     
     ######## Generate PCT Returns DF ###########
     perp = options[0]
     df = pd.read_pickle("./Price_Data/1HOUR/" + str(perp) + ".pkl")
     closes = df[['startedAt', 'close']] #Reduce DataFrame to close Prices
     closes.loc[:, 'close'] = closes['close'].astype(float) #Change
     
     start_price = closes.iloc[-1]['close']
     a_file = open("./dydx_maintenance_margin.json", "r")
     output = a_file.read()
     res = json.loads(output)
     maintenance_margin = res[str(perp)]["maintenance_margin"]

     df2 = pd.DataFrame(columns=["name", "start_price", "maintenance_margin"])
     new_row = {'name': str(perp), 'start_price': start_price, 'maintenance_margin': maintenance_margin}
     df2 = df2.append(new_row, ignore_index=True)

     closes.loc[:, str(perp)] = closes["close"].pct_change()
     closes = closes.drop(['close'], axis=1)
     result = closes

     for perp in options[1:]:
          df = pd.read_pickle("./Price_Data/1HOUR/" + str(perp) + ".pkl")
          closes = df[['startedAt', 'close']] #Reduce DataFrame to close Prices
          closes.loc[:, 'close'] = closes['close'].astype(float) #Change 
          closes.loc[:, str(perp)] = closes["close"].pct_change()

          maintenance_margin = res[str(perp)]["maintenance_margin"]
          start_price = closes.iloc[-1]['close']
          new_row = {'name':str(perp), 'start_price':start_price, 'maintenance_margin': maintenance_margin}
          df2 = df2.append(new_row, ignore_index=True)

          closes = closes.drop(['close'], axis=1)
          result = pd.merge(result, closes, how='inner')
          result = result.iloc[1: , :]
     
     parameters_df = pd.merge(df2, df_size, on=["name"], how='inner')
     parameters_df['position_size_usdc'] = parameters_df['start_price'] * parameters_df['position']
     parameters_df['margin_parameter'] = abs(parameters_df['start_price'] * parameters_df['position'] * parameters_df['maintenance_margin'])
     Total_Maintenance_Margin_Requirement = parameters_df['margin_parameter'].sum()
     
     st.write("The total maintenace margin of this porfolio is: $", round(Total_Maintenance_Margin_Requirement,2))

     #st.dataframe(df2)
     #st.dataframe(df_size)
     #st.dataframe(parameters_df)


     #Initial Variables 
     hours = 24
     iterations = 100

     portfolio_paths = pd.DataFrame()
     liquidation_scenarios = pd.DataFrame()

     for x in range(0,iterations):
          #Generate Price Paths
          price_paths = np.full((hours, no_selections), float(1))
          price_paths[0] = parameters_df["start_price"]
          result1 = result.drop(['startedAt'], axis=1)
          for t in range(1, hours):
               price_paths[t] = np.array(price_paths[t-1]*(1 + result1.iloc[randrange(len(result1))]), dtype=float)

          #Calculate Maintenance Margin
          maintenance_margin_1 = price_paths * np.array(parameters_df["position"]) * np.array([parameters_df["maintenance_margin"]])
          maintenance_margin_1 = np.sum(maintenance_margin_1, axis=1)

          #Calculate Total Account Value
          Total_Account_Value = Initial_USDC + np.sum((price_paths - price_paths[0]) * np.array([parameters_df["position"]]), axis=1)
          portfolio_paths = pd.concat([portfolio_paths, pd.DataFrame(Total_Account_Value)], axis=1)
          liquidation_scenarios = pd.concat([liquidation_scenarios, pd.DataFrame(Total_Account_Value > maintenance_margin)], axis=1)

     path_headers = list(range(0, iterations))
     portfolio_paths.columns = path_headers     
     st.subheader("Historical Simulation")
     st.line_chart(portfolio_paths)
     df = liquidation_scenarios.apply(pd.Series.value_counts).T
     for x in range(0,100):
          headers = list(range(0, 100))
     
     liquidation_scenarios.columns = headers

     if Total_Maintenance_Margin_Requirement > Initial_USDC:
          st.write("It is not possible for this porfolio to have been created")
     else:
          try:
               st.write("The portfolio would have been liquidated ", df[False].count(), " times out of ", iterations)
          except KeyError:
               st.write("The portfolio was not liquidated in any simulations")
          
          st.write("The average portfolio value is: ", round(portfolio_paths.iloc[hours-1].mean()))
          st.write("The median portfolio value is: ", round(portfolio_paths.iloc[hours-1].median()))
          st.write("The maximum portfolio value is: ", round(portfolio_paths.iloc[hours-1].max()))
          st.write("The minimum portfolio value is: ", round(portfolio_paths.iloc[hours-1].min()))

          VaR = round(np.percentile(portfolio_paths.iloc[hours-1], 5, axis=0))
          ES = round(portfolio_paths.iloc[hours-1][portfolio_paths.iloc[hours-1] <= np.percentile(portfolio_paths.iloc[hours-1], 5, axis=0)].mean())

          st.write("\nPortfolio VaR: ", VaR, "\nA VaR of ", VaR, "  suggests that we are \
          95% certain that our portfolio will be greater than ", VaR, 
               "\n in the next 24 hours")

          st.write("\nExpected Shortfall: ", ES, "\nOn the condition that the 24h loss is greater than the 5th percentile" 
               " of the loss distribution, it is expected that \n the portfolio will be ", ES)

     correlations = result1.corr(method='kendall') 
     random_vals = multivariate_normal(cov=correlations).rvs(hours)
     copula = norm.cdf(random_vals)

     portfolio_paths_MC = pd.DataFrame()
     liquidation_scenarios_MC = pd.DataFrame()

     for x in range(0,100):
          maintenance_margin_list = []
          Total_Account_Value_list = []

          for perp in options:
               random_vals = multivariate_normal(cov=correlations).rvs(24)
               copula = norm.cdf(random_vals)
               
               count = 0
               distribution = norm(result1[str(perp)].mean(), result[str(perp)].std())
               copula_object = distribution.ppf(copula[:, count])
               price_paths = np.full((hours, 1), float(1))
               price_paths[0] = [parameters_df.loc[parameters_df['name'] == str(perp), 'start_price'].iloc[0]]
          
               for t in range(1, hours):
                    price_paths[t] = np.array(price_paths[t-1]*(1 + copula_object[t-1]), dtype=float)
               
               maintenance_margin = price_paths * [parameters_df.loc[parameters_df['name'] == str(perp), 'position'].iloc[0]] * \
                    [parameters_df.loc[parameters_df['name'] == str(perp), 'maintenance_margin'].iloc[0]]
               
               maintenance_margin_list.append(maintenance_margin)
               
               Total_Account_Value = ((price_paths - price_paths[0]) * [parameters_df.loc[parameters_df['name'] == str(perp), 'position'].iloc[0]])
               
               Total_Account_Value_list.append(Total_Account_Value)
               
               count += 1

          maintenance_margin = sum(maintenance_margin_list)
          Total_Account_Value_list = sum(Total_Account_Value_list) + Initial_USDC

          portfolio_paths_MC = pd.concat([portfolio_paths_MC, pd.DataFrame(Total_Account_Value_list)], axis=1)
          liquidation_scenarios_MC = pd.concat([liquidation_scenarios_MC, pd.DataFrame(Total_Account_Value_list < maintenance_margin)], axis=1)

     for x in range(0,100):
          headers = list(range(0, 100))
     portfolio_paths_MC.columns = headers

     liquidation_scenarios_MC.columns = headers
     st.subheader("Monte Carlo Simulation")
     st.line_chart(portfolio_paths_MC)
     df_1 = liquidation_scenarios_MC.apply(pd.Series.value_counts).T

     if Total_Maintenance_Margin_Requirement > Initial_USDC:
          st.write("It is not possible for this porfolio to have been created")
     else:     
          try:
               st.write("The portfolio would have been liquidated ", df_1[True].count(), " times out of ", iterations)
          except KeyError:
               st.write("The portfolio was not liquidated in any simulations")
