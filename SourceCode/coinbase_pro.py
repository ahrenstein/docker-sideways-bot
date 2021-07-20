#!/usr/bin/env python3
"""Functions to use with Coinbase Pro"""
#
# Python Script:: coinbase_pro.py
#
# Linter:: pylint
#
# Copyright 2021, Matthew Ahrenstein, All Rights Reserved.
#
# Maintainers:
# - Matthew Ahrenstein: matt@ahrenstein.com
#
# See LICENSE
#

import base64
import json
import time
import hmac
import hashlib
import requests
from requests.auth import AuthBase
import aws_functions


# Create custom authentication for CoinbasePro
# as per https://docs.pro.coinbase.com/?python#creating-a-request
class CoinbaseProAuth(AuthBase):
    """
        Coinbase Pro provided authentication method with minor fixes
        """
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        try:
            message = timestamp + request.method + request.path_url + (request.body or b'').decode()
        except:
            message = timestamp + request.method + request.path_url + (request.body or b'')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request


def get_cbpro_creds_from_file(config_file: str) -> [str, str, str]:
    """Open a JSON file and get Coinbase Pro credentials out of it
    Args:
        config_file: Path to the JSON file containing credentials and config options

    Returns:
        cbpro_api_key: An API key for Coinbase Pro
        cbpro_api_secret: An API secret for Coinbase Pro
        cbpro_api_passphrase: An API passphrase for Coinbase Pro
    """
    with open(config_file) as creds_file:
        data = json.load(creds_file)
    cbpro_api_key = data['coinbase']['api_key']
    cbpro_api_secret = data['coinbase']['api_secret']
    cbpro_api_passphrase = data['coinbase']['passphrase']
    return cbpro_api_key, cbpro_api_secret, cbpro_api_passphrase


def get_decimal_max(api_url: str, config_file: str, currency: str) -> int:
    """Get the maximum amount of decimals permitted for a currency

    Args:
    api_url: The API URL for the Coinbase PRO Exchange
    config_file: Path to the JSON file containing credentials and config options
    currency: The cryptocurrency the bot is monitoring

    Returns:
    tick_size: An integer of decimal places permitted
    """
    # Instantiate Coinbase API and query the price
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    api_query = "currencies/%s" % currency.upper()
    tick_size = -1
    try:
        result = requests.get(api_url + api_query, auth=coinbase_auth)
        tick_size = str(result.json()['max_precision'])[2:].find('1')+1
    except Exception as err:
        print(err)
    return int(tick_size)


def get_fee_rate(api_url: str, config_file: str) -> float:
    """Get the current fee structure for taker fees

    Args:
    api_url: The API URL for the Coinbase PRO Exchange
    config_file: Path to the JSON file containing credentials and config options

    Returns:
    fee_rate: An integer of decimal places permitted
    """
    # Instantiate Coinbase API and query the price
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    api_query = "fees"
    fee_rate = -1
    try:
        result = requests.get(api_url + api_query, auth=coinbase_auth)
        fee_rate = result.json()['taker_fee_rate']
    except Exception as err:
        print("ERROR: %s" % err)
    return float(fee_rate)


def get_coin_price(api_url: str, config_file: str, currency: str) -> float:
    """
    Get the USD price of a coin from Coinbase Pro

    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        currency: The cryptocurrency the bot is monitoring

    Returns:
        coin_price: The price the coin currently holds in USD
    """
    # Instantiate Coinbase API and query the price
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    api_query = "products/%s-USD/ticker" % currency
    result = requests.get(api_url + api_query, auth=coinbase_auth)
    coin_price = float(result.json()['price'])
    return coin_price


def check_balances(api_url: str, config_file: str, currency: str) -> [float, float]:
    """Return the account balances of the coin and the USD balance
    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        currency: The crypto currency we are trading with

    Returns:
        coin_balance: The balance of the coin we are trading
        usd_balance: The balance of USD
    """
    # Instantiate Coinbase API and query the price
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    api_query = "accounts"
    coin_balance = -1
    usd_balance = -1
    result = requests.get(api_url + api_query, auth=coinbase_auth).json()
    try:
        for account in result:
            if account['currency'] == "USD":
                usd_balance = float(account['balance'])
            if account['currency'] == currency:
                coin_balance = float(account['balance'])
    except Exception as err:
        print("ERROR: Unable to get current balance!")
        print(err)
        return coin_balance, usd_balance
    return coin_balance, usd_balance


def check_if_open_orders(api_url: str, config_file: str) -> bool:
    """Check if existing limit orders exist and return True if the do

    Args:
    api_url: The API URL for the Coinbase PRO Exchange
    config_file: Path to the JSON file containing credentials and config options

    Returns:
    open_orders: A bool if orders are open
    """
    # Instantiate Coinbase API and query the price
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    api_query = "orders"
    try:
        results = requests.get(api_url + api_query, auth=coinbase_auth).json()
    except Exception as err:
        print("ERROR: Unable to get list of orders!")
        print(err)
    if not results:
        return False
    return True


def limit_buy_currency(api_url: str, config_file: str, currency: str,
                       buy_amount: float, buy_price: float, aws_alerts=False) -> bool:
    """
    Conduct a limit buy on Coinbase Pro to trade a currency with USD

    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        currency: The cryptocurrency the bot is monitoring
        buy_amount: The amount of $USD the bot plans to spend
        buy_price: The limit price of the currency we are interested in
        aws_alerts: Use AWS alerts (default: False)

    Returns:
        trade_success: A bool that is true if the trade succeeded
    """
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    # Instantiate Coinbase API and query the price
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    buy_query = 'orders'
    order_config = json.dumps({'type': 'limit', 'side': 'buy',
                               'size': buy_amount, 'price': buy_price,
                               'time_in_force': "GTC", 'product_id': '%s-USD' % currency})
    buy_result = requests.post(api_url + buy_query, data=order_config, auth=coinbase_auth).json()
    print(order_config)
    print(buy_result)
    if 'message' in buy_result:
        sns_message = "Buy order failed.\n Reason: %s" % buy_result['message']
        print("LOG: %s" % sns_message)
        if aws_alerts:
            aws_creds = aws_functions.get_aws_creds_from_file(config_file)
            aws_functions.post_to_sns(aws_creds[0],
                                      aws_creds[1], aws_creds[2], "Sideways Bot Error", sns_message)
        return False
    else:
        print("LOG: Buy order succeeded.")
        print("LOG: Buy Results: %s" % json.dumps(buy_result, indent=2))
        return True


def limit_sell_currency(api_url: str, config_file: str, currency: str,
                        sell_amount: float, sell_price: float, aws_alerts=False) -> bool:
    """
    Conduct a limit sell on Coinbase Pro to trade a currency with USD

    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        currency: The cryptocurrency the bot is monitoring
        sell_amount: The amount of the currency the bot plans to sell
        sell_price: The limit price of the currency we are interested in
        aws_alerts: Use AWS alerts (default: False)

    Returns:
        trade_success: A bool that is true if the trade succeeded
    """
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    # Instantiate Coinbase API and query the price
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    # Coinbase Pro denominates purchases in the coin amount not USD so we have to do math
    sell_query = 'orders'
    order_config = json.dumps({'type': 'limit', 'side': 'sell',
                               'size': sell_amount, 'price': sell_price,
                               'time_in_force': "GTC", 'product_id': '%s-USD' % currency})
    sell_result = requests.post(api_url + sell_query, data=order_config, auth=coinbase_auth).json()
    if 'message' in sell_result:
        sns_message = "Sell order failed.\n Reason: %s" % sell_result['message']
        print("LOG: %s" % sns_message)
        if aws_alerts:
            aws_creds = aws_functions.get_aws_creds_from_file(config_file)
            aws_functions.post_to_sns(aws_creds[0],
                                      aws_creds[1], aws_creds[2], "Sideways Bot Error", sns_message)
        return False
    else:
        print("LOG: Sell order succeeded.")
        print("LOG: Sell Results: %s" % json.dumps(sell_result, indent=2))
        return True
