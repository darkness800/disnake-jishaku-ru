# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from disnake.ext import commands

from jishaku.features.filesystem import FilesystemFeature
from jishaku.features.guild import GuildFeature
from jishaku.features.invocation import InvocationFeature
from jishaku.features.management import ManagementFeature
from jishaku.features.python import PythonFeature
from jishaku.features.root_command import RootCommand
from jishaku.features.shell import ShellFeature
from jishaku.features.voice import VoiceFeature

__all__ = (
    "Jishaku",
    "STANDARD_FEATURES",
    "OPTIONAL_FEATURES",
    "setup",
)

STANDARD_FEATURES = (VoiceFeature, GuildFeature, FilesystemFeature, InvocationFeature, ShellFeature, PythonFeature, ManagementFeature, RootCommand)

OPTIONAL_FEATURES = []

try:
    from jishaku.features.youtube import YouTubeFeature
except ImportError:
    pass
else:
    OPTIONAL_FEATURES.insert(0, YouTubeFeature)


class Jishaku(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """
    Подкласс Frontend, который смешивается, чтобы сформировать последний Cog Jishaku.
    """


def setup(bot: commands.Bot):
    """
    Функция настройки, определяющая расширения Jishaku.cog и Jishaku.
    """

    bot.add_cog(Jishaku(bot=bot))
