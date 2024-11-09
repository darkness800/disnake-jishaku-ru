# -*- coding: utf-8 -*-

"""
Тест подклассионного джишаку 1
~~~~~~~~~~~~~~~~~~~~~~~~~~

Это действительный файл расширения для Disnake, предназначенного для
Откройте для себя странное поведение, связанное с подклассом.

Этот вариант переопределяет поведение, используя функцию.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, Смотрите лицензию для более подробной информации.

"""

from disnake.ext import commands

import jishaku


class ThirdPartyFeature(jishaku.Feature):
    """
    Переходящая функция для тестирования
    """

    @jishaku.Feature.Command(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context):
        """
        переопределить тест
        """
        return await ctx.send("Поведение этой команды было отменено сторонней функцией.")


class Magnet1(ThirdPartyFeature, *jishaku.OPTIONAL_FEATURES, *jishaku.STANDARD_FEATURES):  # pylint: disable=too-few-public-methods
    """
    Расширенная джишаку Cog
    """


def setup(bot: commands.Bot):
    """
    Функция настройки для расширенного COG
    """

    bot.add_cog(Magnet1(bot=bot))
