# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import io
import os
import pathlib
import re

import aiohttp
import disnake
from disnake.ext import commands

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.hljs import get_language, guess_file_traits
from jishaku.paginators import PaginatorInterface, WrappedFilePaginator, use_file_check


class FilesystemFeature(Feature):
    """
    Функция, содержащая команды, связанные с файловой системой
    """

    __cat_line_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")

    @Feature.Command(parent="jsk", name="cat")
    async def jsk_cat(self, ctx: commands.Context, argument: str):
        """
        Прочитайте файл, используя синтаксис, выделение, если обнаружено.

        Линии и линии поддерживаются путем добавления «#L12» или «#L12-14» и т. Д. к концу имени файла.
        """

        match = self.__cat_line_regex.search(argument)

        if not match:  # никогда не должно случиться
            return await ctx.send("Не удалось разобрать эти входные данные.")

        path = match.group(1)

        line_span = None

        if match.group(2):
            start = int(match.group(2))
            line_span = (start, int(match.group(3) or start))

        if not os.path.exists(path) or os.path.isdir(path):
            return await ctx.send(f"`{path}`: Файла с таким именем нет.")

        size = os.path.getsize(path)

        if size <= 0:
            return await ctx.send(f"`{path}`: Трусливый отказ читать файл без данных о размере"
                                  f" (он может быть пустым, бесконечным или недоступным).")

        if size > 128 * (1024 ** 2):
            return await ctx.send(f"`{path}`: Трусливо отказывается читать файл размером >128 МБ.")

        try:
            with open(path, "rb") as file:
                if use_file_check(ctx, size):
                    if line_span:
                        content, *_ = guess_file_traits(file.read())

                        lines = content.split('\n')[line_span[0] - 1:line_span[1]]

                        await ctx.send(file=disnake.File(
                            filename=pathlib.Path(file.name).name,
                            fp=io.BytesIO('\n'.join(lines).encode('utf-8'))
                        ))
                    else:
                        await ctx.send(file=disnake.File(
                            filename=pathlib.Path(file.name).name,
                            fp=file
                        ))
                else:
                    paginator = WrappedFilePaginator(file, line_span=line_span, max_size=1985)
                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                    await interface.send_to(ctx)
        except UnicodeDecodeError:
            return await ctx.send(f"`{path}`: Не удалось определить кодировку этого файла. ")
        except ValueError as exc:
            return await ctx.send(f"`{path}`: Не удалось прочитать этот файл, {exc}")

    @Feature.Command(parent="jsk", name="curl")
    async def jsk_curl(self, ctx: commands.Context, url: str):
        """
        Загрузите и отобразите текстовый файл из Интернета.

        Эта команда похожа на JSK Cat, но принимает URL.
        """

        # Удалить встроенные маскировщики, если они присутствуют
        url = url.lstrip("<").rstrip(">")

        async with ReplResponseReactor(ctx.message):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.read()
                    hints = (
                        response.content_type,
                        url
                    )
                    code = response.status

            if not data:
                return await ctx.send(f"HTTP-ответ был пустым (status code {code}).")

            if use_file_check(ctx, len(data)):  # Файл «Полный контент» Предел предварительного просмотра
                # Обнаружение мелкого языка
                language = None

                for hint in hints:
                    language = get_language(hint)

                    if language:
                        break

                await ctx.send(file=disnake.File(
                    filename=f"ответ.{language or 'txt'}",
                    fp=io.BytesIO(data)
                ))
            else:
                try:
                    paginator = WrappedFilePaginator(io.BytesIO(data), language_hints=hints, max_size=1985)
                except UnicodeDecodeError:
                    return await ctx.send(f"Не удалось определить кодировку ответа. (status code {code})")
                except ValueError as exc:
                    return await ctx.send(f"Не удалось прочитать ответ (status code {code}), {exc}")

                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                await interface.send_to(ctx)
