# -*- coding: utf-8 -*-

"""
Джишаку подклассный тест 2
~~~~~~~~~~~~~~~~~~~~~~~~~~

Это действительный файл расширения для Disnake, предназначенного для
Откройте для себя странное поведение, связанное с подклассом.

Этот вариант переопределяет поведение напрямую.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, Смотрите лицензию для более подробной информации.

"""

from disnake.ext import commands

import jishaku


class Magnet2(*jishaku.OPTIONAL_FEATURES, *jishaku.STANDARD_FEATURES):  # pylint: disable=too-few-public-methods
    """
    Расширенная джишаку Cog
    """

    @jishaku.Feature.Command(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context):
        """
        переопределить тест
        """
        return await ctx.send("Поведение этой команды было переопределено напрямую.")


def setup(bot: commands.Bot):
    """
    Функция настройки для расширенного COG
    """

    bot.add_cog(Magnet2(bot=bot))
