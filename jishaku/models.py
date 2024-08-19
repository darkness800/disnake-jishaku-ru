# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import copy

import disnake
from disnake.ext import commands


async def copy_context_with(ctx: commands.Context, *, author=None, channel=None, **kwargs):
    """
    Makes a new :class:`Context` with changed message properties.
    """

    # copy the message and update the attributes
    alt_message: disnake.Message = copy.copy(ctx.message)
    alt_message._update(kwargs)

    if author is not None:
        alt_message.author = author
    if channel is not None:
        alt_message.channel = channel

    # obtain and return a context of the same type
    return await ctx.bot.get_context(alt_message, cls=type(ctx))
