#!/usr/bin/env python3
"""A bot that trades cryptocurrency sideways using a percentage difference from current price."""
#
# Python Script:: sideways_bot.py
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

import argparse
import bot_internals


def main(config_file: str, debug_mode: bool):
    """
    The main function that triggers and runs the bot functions

    Args:
    config_file: Path to the JSON file containing credentials and config options
    debug_mode: Use Sandbox APIs instead of production
    """
    # Start the Coinbase Pro cycle
    bot_internals.gemini_cycle(config_file, debug_mode)


if __name__ == '__main__':
    # This function parses and return arguments passed in
    # Assign description to the help doc
    PARSER = argparse.ArgumentParser(
        description='A bot that trades cryptocurrency sideways'
                    ' using a percentage difference from current price.')
    # Add arguments
    PARSER.add_argument(
        '-c', '--configFile', type=str, help="Path to config.json file", required=True
    )
    PARSER.add_argument(
        '-d', '--debug', help="Use sandbox APIs", required=False, action='store_true'
    )
    # Array for all arguments passed to script
    ARGS = PARSER.parse_args()
    ARG_CONFIG = ARGS.configFile
    ARG_DEBUG = ARGS.debug
    main(ARG_CONFIG, ARG_DEBUG)
