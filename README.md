Crypto Sideways Bot
===================
This bot is designed to buy and sell cryptocurrency on Coinbase Pro using a USD prefunded portfolio in a sideways fashion.

USE AT YOUR OWN RISK
--------------------
I run this bot full time against my own personal Coinbase Pro account, however I make no warranties that
the bot will function. It could crash and miss some price movement, or it could detect and buy at the wrong prices. So far
it has done well for me, but your mileage may vary.  
As with any open source code: **USE THIS BOT AT YOUR OWN RISK!**

Limitations
-----------
The logic behind price setting is very basic. This code was written assuming a dedicated Coinbase Pro profile that will buy/sell all
of the currency pair only with this bot. Manually touching things may corrupt the bot's plan!

Sideways Movement Method
------------------------
When the bot detects USD in the portfolio it will set a limit order to buy the currency of choice at the specified percentage less than
the current price. It will also store the current price plus the specified percentage in a file in the config folder of the container for selling.
When the bot detects any amount of the currency of choice in the portfolio it will read the sell price file and set a limit order to sell at that price.

Running The Bot
---------------
To run the bot you will need Docker and docker-compose installed on your computer.  

    docker-compose up -d

Config File
-----------
You will need the following:

1. Coinbase Pro credentials tied to the portfolio you want to run the bot against
2. Sideways logic parameters:
    1. The cryptocurrency you want to transact in. (It must support being paired against USD in Coinbase Pro)
    2. The price movement percentage as an integer

The following sections are optional.

1. Time variables in the bot config
   1. Check cycle frequency in minutes (Default: 15)
2. AWS credentials:
   1. AWS API keys
   2. SNS topic ARN (us-east-1 only for now)
3. Optionally you can override the bot name

These settings should be in a configuration file named `config.json` and placed in `./config`.
Additionally, you can override the volume mount to a new path if you prefer.
The file should look like this:

```json
{
  "bot": {
    "currency": "ETH",
    "movement_percentage": 2.5,
     "cycle_time_minutes": 5,
     "name": "Sideways-Bot"
  },
  "coinbase": {
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "passphrase": "YOUR_API_PASSPHRASE"
  },
   "aws": {
    "access_key": "YOUR_API_KEY",
    "secret_access_key": "YOUR_API_SECRET",
    "sns_arn": "arn:aws:sns:us-east-1:012345678901:dip_alerts"
  }
}
```

Running outside of Docker
-------------------------
You can run the bot outside of Docker pretty easily.

```bash
python SourceCode/sideways_bot.py -c /path/to/config.json
```

Logs
----
The bot will log activity to stdout, so you can review it with `docker logs`

Donations
---------
Any and all donations are greatly appreciated.  
I have GitHub Sponsors configured however I happily prefer cryptocurrency:

ETH/DAI: ahrenstein.eth (0x288f3d3df1c719176f0f6e5549c2a3928d27d1c1)  
BTC: 3HrVPPwTmPG8LKBt84jbQrVjeqDbM1KyEb
