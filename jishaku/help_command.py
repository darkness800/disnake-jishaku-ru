# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from disnake.ext import commands

from jishaku.paginators import PaginatorEmbedInterface, PaginatorInterface


class DefaultPaginatorHelp(commands.DefaultHelpCommand):
    """
    Подкласс: класс: `commands.defaulthelpcommand`, который использует PaginatorInterface для страниц.
    """

    def __init__(self, **options):
        paginator = options.pop('paginator', commands.Paginator(max_size=1985))

        super().__init__(paginator=paginator, **options)

    async def send_pages(self):
        destination = self.get_destination()

        interface = PaginatorInterface(self.context.bot, self.paginator, owner=self.context.author)
        await interface.send_to(destination)


class DefaultEmbedPaginatorHelp(commands.DefaultHelpCommand):
    """
    Подкласс: класс: `commands.defaulthelpcommand`, который использует Paginatorembedinterface для страниц.
    """

    async def send_pages(self):
        destination = self.get_destination()

        interface = PaginatorEmbedInterface(self.context.bot, self.paginator, owner=self.context.author)
        await interface.send_to(destination)


class MinimalPaginatorHelp(commands.MinimalHelpCommand):
    """
    Подкласс: класс: `commands.minimalhelpcommand`, который использует PaginatorInterface для страниц.
    """

    def __init__(self, **options):
        paginator = options.pop('paginator', commands.Paginator(prefix=None, suffix=None, max_size=1985))

        super().__init__(paginator=paginator, **options)

    async def send_pages(self):
        destination = self.get_destination()

        interface = PaginatorInterface(self.context.bot, self.paginator, owner=self.context.author)
        await interface.send_to(destination)


class MinimalEmbedPaginatorHelp(commands.MinimalHelpCommand):
    """
    Подкласс: класс: `commands.minimalhelpcommand`, который использует Paginatorembedinterface для страниц.
    """

    async def send_pages(self):
        destination = self.get_destination()

        interface = PaginatorEmbedInterface(self.context.bot, self.paginator, owner=self.context.author)
        await interface.send_to(destination)
