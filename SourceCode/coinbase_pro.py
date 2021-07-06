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


def check_balance(api_url: str, config_file: str, coin="USD") -> [bool, float]:
    """Check if a balance of a specific coin exists
    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        coin: The coin we are checking against

    Returns:
        all_clear: A bool that returns true if there is .001 or more of a coin (5.0 if USD)
        balance: A float of the balance
    """
    # Instantiate Coinbase API and query the price
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    api_query = "accounts"
    result = requests.get(api_url + api_query, auth=coinbase_auth).json()
    try:
        for account in result:
            if coin == "USD":
                min_value = 50
            else:
                min_value = .001
            if account['currency'] == coin:
                if float(account['balance']) >= min_value:
                    if float(account['hold']) == 0:
                        print("yes")
                        return True, float(account['balance'])
    except Exception as err:
        print("ERROR: Unable to get current balance!")
        print(err)
        return False, float(account['balance'])
    # Return false by default
    return False, float(account['balance'])


def limit_buy_currency(api_url: str, config_file: str, currency: str, buy_amount: float, buy_price: float) -> bool:
    """
    Conduct a limit buy on Coinbase Pro to trade a currency with USD

    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        currency: The cryptocurrency the bot is monitoring
        buy_amount: The amount of $USD the bot plans to spend
        buy_price: The limit price of the currency we are interested in

    Returns:
        trade_success: A bool that is true if the trade succeeded
    """
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    # Instantiate Coinbase API and query the price
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    # Coinbase Pro denominates purchases in the coin amount not USD so we have to do math
    coin_current_price = get_coin_price(api_url, config_file, currency)
    coin_amount = round(buy_amount / coin_current_price, 3)
    buy_query = 'orders'
    order_config = json.dumps({'type': 'limit', 'side': 'buy',
                               'size': coin_amount, 'price': buy_price,
                               'time_in_force': "GTC", 'product_id': '%s-USD' % currency})
    buy_result = requests.post(api_url + buy_query, data=order_config, auth=coinbase_auth).json()
    print(order_config)
    print(buy_result)
    if 'message' in buy_result:
        print("LOG: Buy order failed.")
        print("LOG: Reason: %s" % buy_result['message'])
        return False
    else:
        print("LOG: Buy order succeeded.")
        print("LOG: Buy Results: %s" % json.dumps(buy_result, indent=2))
        return True


def limit_sell_currency(api_url: str, config_file: str, currency: str, sell_price: float) -> bool:
    """
    Conduct a limit sell on Coinbase Pro to trade a currency with USD

    Args:
        api_url: The API URL for Coinbase Pro
        config_file: Path to the JSON file containing credentials and config options
        currency: The cryptocurrency the bot is monitoring
        sell_price: The limit price of the currency we are interested in

    Returns:
        trade_success: A bool that is true if the trade succeeded
    """
    coinbase_creds = get_cbpro_creds_from_file(config_file)
    # Instantiate Coinbase API and query the price
    coinbase_auth = CoinbaseProAuth(coinbase_creds[0], coinbase_creds[1], coinbase_creds[2])
    # Coinbase Pro denominates purchases in the coin amount not USD so we have to do math
    sell_amount = check_balance(api_url, config_file, currency)[1]
    sell_query = 'orders'
    order_config = json.dumps({'type': 'limit', 'side': 'sell',
                               'size': sell_amount, 'price': sell_price,
                               'time_in_force': "GTC", 'product_id': '%s-USD' % currency})
    sell_result = requests.post(api_url + sell_query, data=order_config, auth=coinbase_auth).json()
    if 'message' in sell_result:
        print("LOG: Sell order failed.")
        print("LOG: Reason: %s" % sell_result['message'])
        return False
    else:
        print("LOG: Sell order succeeded.")
        print("LOG: Sell Results: %s" % json.dumps(sell_result, indent=2))
        return True
