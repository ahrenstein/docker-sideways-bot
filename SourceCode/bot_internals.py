#!/usr/bin/env python3
"""Internal functions the bot uses"""
#
# Python Script:: bot_internals.py
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

from itertools import count
import json
import datetime
import time
import aws_functions
import coinbase_pro


def read_bot_config(config_file: str) -> [str, int, bool, int, str]:
    """Open a JSON file and get the bot configuration
    Args:
        config_file: Path to the JSON file containing credentials and config options

    Returns:
        crypto_currency: The cryptocurrency that will be monitored
        movement_percentage: The percentage of the price movement from current price
        aws_loaded: A bool to determine if AWS configuration options exist
        cycle_time_minutes: The cycle interval in minutes
        bot-name: The name of the bot
    """
    with open(config_file) as creds_file:
        data = json.load(creds_file)
        creds_file.close()
    crypto_currency = data['bot']['currency']
    movement_percentage = data['bot']['movement_percentage']
    aws_loaded = bool('aws' in data)
    if 'cycle_time_minutes' in data['bot']:
        cycle_time_minutes = data['bot']['cycle_time_minutes']
    else:
        cycle_time_minutes = 15
    if 'name' in data['bot']:
        bot_name = data['bot']['name']
    else:
        bot_name = "Coinbase-" + crypto_currency + "-sideways-bot"
    return crypto_currency, movement_percentage,\
        aws_loaded, cycle_time_minutes, bot_name


def set_price_file(price: float, percent: int):
    """Save the value of the current price up and down by the same percentage
    to a file

    Args:
    price: The price to check a dip percentage against
    percent: the dip percentage we care about
    """
    buy_price = round(price * (1 - percent / 100), 2)
    sell_price = round(price * (1 + percent / 100), 2)
    json_data = {"buy_price": buy_price, "sell_price": sell_price}
    with open("/config/pricing.json", 'w') as prices_file:
        prices_file.write(json.dumps(json_data))
        prices_file.close()


def check_price_file() -> [float,float]:
    """Check the buy and sell prices from the price file

    Returns:
        buy_price: The buy price we will use
        sell_price: The sell price we will use
    """
    with open("/config/pricing.json") as prices_file:
        data = json.load(prices_file)
        prices_file.close()
    return data['buy_price'], data['sell_price']


def coinbase_cycle(config_file: str, debug_mode: bool) -> None:
    """Perform bot cycles using Coinbase Pro as the exchange

        Args:
        config_file: Path to the JSON file containing credentials
        debug_mode: Are we running in debugging mode?
        """
    # Load the configuration file
    config_params = read_bot_config(config_file)
    if config_params[2]:
        aws_config = aws_functions.get_aws_creds_from_file(config_file)
        message = "%s has been started" % config_params[4]
        aws_functions.post_to_sns(aws_config[0], aws_config[1], aws_config[2], message, message)
    # Set API URLs
    if debug_mode:
        coinbase_pro_api_url = "https://api-public.sandbox.pro.coinbase.com/"
    else:
        coinbase_pro_api_url = "https://api.pro.coinbase.com/"
    print("LOG: Starting bot...\nLOG: Monitoring %s"
          " on Coinbase Pro to trade across %s%% changes"
          % (config_params[0], config_params[1]))
    for cycle in count():
        now = datetime.datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
        print("LOG: Cycle %s: %s" % (cycle, now))
        # Check if the API is working
        coin_current_price = coinbase_pro.get_coin_price(coinbase_pro_api_url,
                                                         config_file, config_params[0])
        if coin_current_price == -1:
            message = "ERROR: Coin price invalid. This could be an API issue. Ending cycle"
            print(message)
            subject = "Coinbase-%s-Coin price invalid" % config_params[0]
            if config_params[2]:
                aws_functions.post_to_sns(aws_config[0], aws_config[1], aws_config[2],
                                          subject, message)
            time.sleep(config_params[3] * 60)
            continue
        # Get the decimal precision that Coinbase Pro permits for this currency
        tick_size = coinbase_pro.get_decimal_max(coinbase_pro_api_url,
                                                 config_file, config_params[0])
        # Get the fee structure we are working with
        fee_rate = coinbase_pro.get_fee_rate(coinbase_pro_api_url, config_file)
        # Check if are waiting on a sell
        currency_balances = coinbase_pro.check_balances(coinbase_pro_api_url,
                                                        config_file, config_params[0])
        if coinbase_pro.check_if_open_orders(coinbase_pro_api_url, config_file, config_params[0]):
            print("LOG: There are current limit orders open on the profile. Doing nothing.")
            # Sleep for the specified cycle interval
            time.sleep(config_params[3] * 60)
            continue
        if currency_balances[0] >= 0.001:
            message = "More than .001 %s so we are in SELL mode" % config_params[0]
            print("LOG: %s" % message)
            print(currency_balances[0])
            tx_prices = check_price_file()
            # Round the currency sell amount correctly and factor in the fee
            sell_amount = round(currency_balances[0], tick_size)
            coinbase_pro.limit_sell_currency(coinbase_pro_api_url,
                                             config_file, config_params[0],
                                             sell_amount, tx_prices[1], config_params[2])
            time.sleep(config_params[3] * 60)
        # Check if we can buy
        elif currency_balances[1] >= 100:
            message = "More than $100 USD so we are in BUY mode"
            print("LOG: %s" % message)
            print("Recording prices to file")
            coin_current_price = coinbase_pro.get_coin_price\
                (coinbase_pro_api_url, config_file, config_params[0])
            set_price_file(coin_current_price, config_params[1])
            tx_prices = check_price_file()
            # Round the currency buy amount correctly and factor in the fee
            buy_amount = round((currency_balances[1] - (currency_balances[1] * fee_rate)) /
                               coin_current_price, tick_size)
            print("Buy amount: %s" % buy_amount)
            coinbase_pro.limit_buy_currency(coinbase_pro_api_url, config_file, config_params[0],
                                            buy_amount, tx_prices[0], config_params[2])
        else:
            print("LOG: Neither %s nor USD have a high enough balance."
                  " Most likely a limit order is on the books right now" % config_params[0])
        # Sleep for the specified cycle interval
        time.sleep(config_params[3] * 60)
