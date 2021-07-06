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
        bot_name = "CoinbasePro-" + crypto_currency + "-sideways-bot"
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
    #with open("/Users/ahrenstein/Scratch/pricing.json", 'w') as prices_file:
        prices_file.write(json.dumps(json_data))
        prices_file.close()


def check_price_file() -> [float,float]:
    """Check the buy and sell prices from the price file

    Returns:
        buy_price: The buy price we will use
        sell_price: The sell price we will use
    """
    with open("/config/pricing.json") as prices_file:
    #with open("/Users/ahrenstein/Scratch/pricing.json") as prices_file:
        data = json.load(prices_file)
        prices_file.close()
    return data['buy_price'], data['sell_price']


def coinbase_pro_cycle(config_file: str, debug_mode: bool) -> None:
    """Perform bot cycles using Coinbase Pro as the exchange

        Args:
        config_file: Path to the JSON file containing credentials
        debug_mode: Are we running in debugging mode?
        """
    # Load the configuration file
    config_params = read_bot_config(config_file)
    if config_params[2]:
        aws_config = aws_functions.get_aws_creds_from_file(config_file)
        message = "%s has been started" % config_params[8]
        aws_functions.post_to_sns(aws_config[0], aws_config[1], aws_config[2], message, message)
    # Set API URLs
    if debug_mode:
        coinbase_pro_api_url = "https://api-public.sandbox.pro.coinbase.com/"
    else:
        coinbase_pro_api_url = "https://api.pro.coinbase.com/"
    print("LOG: Starting bot...\nLOG: Monitoring %s on Coinbase Pro to trade across %s%% changes"
          % (config_params[0], config_params[1]))
    for cycle in count():
        now = datetime.datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
        print("LOG: Cycle %s: %s" % (cycle, now))
        # Check if are waiting on a sell
        if coinbase_pro.check_balance(coinbase_pro_api_url, config_file, config_params[0])[0]:
            message = "More than .001 %s so we are in SELL mode" % config_params[0]
            print("LOG: %s" % message)
            tx_prices = check_price_file()
            coinbase_pro.limit_sell_currency(coinbase_pro_api_url,
                                             config_file, config_params[0], tx_prices[1])
        # Check if we can buy
        if coinbase_pro.check_balance(coinbase_pro_api_url, config_file)[0]:
            message = "More than $50 USD so we are in BUY mode"
            print("LOG: %s" % message)
            print("Recording prices to file")
            coin_current_price = coinbase_pro.get_coin_price \
                (coinbase_pro_api_url, config_file, config_params[0])
            set_price_file(coin_current_price, config_params[1])
            usd_available = coinbase_pro.check_balance(coinbase_pro_api_url, config_file)[1]
            # Reducing available balance by .05% to cover transaction fees
            usd_available = round(usd_available * (1 - .05 / 100), 2)
            tx_prices = check_price_file()
            coinbase_pro.limit_buy_currency(coinbase_pro_api_url, config_file, config_params[0],
                                            usd_available, tx_prices[0])
        # Sleep for the specified cycle interval
        time.sleep(config_params[3] * 60)
