# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import logging
import sys

import click
from disnake.ext import commands

LOG_FORMAT: logging.Formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
LOG_STREAM: logging.Handler = logging.StreamHandler(stream=sys.stdout)
LOG_STREAM.setFormatter(LOG_FORMAT)


@click.command()
@click.argument('token')
def entrypoint(token: str):
    """
    Входная точка доступна через `python -m jishaku <TOKEN>`
    """

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(LOG_STREAM)

    bot = commands.Bot(commands.when_mentioned)
    bot.load_extension('jishaku')
    bot.run(token)


if __name__ == '__main__':
    entrypoint()
