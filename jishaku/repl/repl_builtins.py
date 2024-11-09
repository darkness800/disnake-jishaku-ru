# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import aiohttp
import disnake
from disnake.ext import commands


async def http_get_bytes(*args, **kwargs) -> bytes:
    """
    Выполняет запрос HTTP GET против URL -адреса, возвращая полезную нагрузку ответа в качестве байтов.

    Аргументы, которые должны пройти, такие же, как :func:`aiohttp.ClientSession.get`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.get(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.read()


async def http_get_json(*args, **kwargs) -> dict:
    """
    Выполняет запрос на http get против URL,
    Возврат полезной нагрузки ответа в качестве словаря полезной нагрузки ответа, интерпретируемой как JSON.

    Аргументы, которые должны пройти, такие же, как :func:`aiohttp.ClientSession.get`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.get(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.json()


async def http_post_bytes(*args, **kwargs) -> bytes:
    """
    Выполняет запрос на почту HTTP против URL, возвращая полезную нагрузку ответа в качестве байтов.

    Аргументы, которые должны пройти, такие же, как :func:`aiohttp.ClientSession.post`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.read()


async def http_post_json(*args, **kwargs) -> dict:
    """
    Выполняет запрос на http post против URL,
    Возврат полезной нагрузки ответа в качестве словаря полезной нагрузки ответа, интерпретируемой как JSON.

    Аргументы, которые должны пройти, такие же, как :func:`aiohttp.ClientSession.post`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.json()


def get_var_dict_from_ctx(ctx: commands.Context, prefix: str = '_'):
    """
    Возвращает дикт, который будет использоваться в Repl для данного контекста.
    """

    raw_var_dict = {
        'author': ctx.author,
        'bot': ctx.bot,
        'channel': ctx.channel,
        'ctx': ctx,
        'find': disnake.utils.find,
        'get': disnake.utils.get,
        'guild': ctx.guild,
        'http_get_bytes': http_get_bytes,
        'http_get_json': http_get_json,
        'http_post_bytes': http_post_bytes,
        'http_post_json': http_post_json,
        'message': ctx.message,
        'msg': ctx.message
    }

    return {f'{prefix}{k}': v for k, v in raw_var_dict.items()}
