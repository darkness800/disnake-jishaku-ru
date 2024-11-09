# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import pathlib
import typing

import pkg_resources
from braceexpand import UnbalancedBracesError, braceexpand
from disnake.ext import commands

__all__ = ('find_extensions_in', 'resolve_extensions', 'package_version', 'ExtensionConverter')


def find_extensions_in(path: typing.Union[str, pathlib.Path]) -> list:
    """
    Пытается найти вещи, которые выглядят как расширения бота в каталоге.
    """

    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)

    if not path.is_dir():
        return []

    extension_names = []

    # Найдите расширения непосредственно в этой папке
    for subpath in path.glob('*.py'):
        parts = subpath.with_suffix('').parts
        if parts[0] == '.':
            parts = parts[1:]

        extension_names.append('.'.join(parts))

    # Найдите расширения как модули подпапки
    for subpath in path.glob('*/__init__.py'):
        parts = subpath.parent.parts
        if parts[0] == '.':
            parts = parts[1:]

        extension_names.append('.'.join(parts))

    return extension_names


def resolve_extensions(bot: commands.Bot, name: str) -> list:
    """
    Пытается разрешить удлинительные запросы в список имен расширения.
    """

    exts = []
    for ext in braceexpand(name):
        if ext.endswith('.*'):
            module_parts = ext[:-2].split('.')
            path = pathlib.Path(*module_parts)
            exts.extend(find_extensions_in(path))
        elif ext == '~':
            exts.extend(bot.extensions)
        else:
            exts.append(ext)

    return exts


def package_version(package_name: str) -> typing.Optional[str]:
    """
    Возвращает версию пакета в виде строки, или нет, если ее нельзя найти.
    """

    try:
        return pkg_resources.get_distribution(package_name).version
    except (pkg_resources.DistributionNotFound, AttributeError):
        return None


class ExtensionConverter(commands.Converter):
    """
    Интерфейс преобразователя для Resolve_extensions, чтобы соответствовать расширениям от пользователей.
    """

    async def convert(self, ctx: commands.Context, argument) -> list:
        try:
            return resolve_extensions(ctx.bot, argument)
        except UnbalancedBracesError as exc:
            raise commands.BadArgument(str(exc))
