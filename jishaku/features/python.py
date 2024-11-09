# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import io
import os

import disnake
from disnake.ext import commands

from jishaku.codeblocks import codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags, DISABLED_SYMBOLS
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, Scope, all_inspections, disassemble, get_var_dict_from_ctx


class PythonFeature(Feature):
    """
    Функция, содержащая команды, связанные с Python
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scope = Scope()
        self.retain = Flags.RETAIN
        self.last_result = None

    @property
    def scope(self):
        """
        Получает пример для использования в Repl.

        Если удержание включено, это внутренняя сохраненная область,
        В противном случае это всегда новая сфера.
        """

        if self.retain:
            return self._scope
        return Scope()

    @Feature.Command(parent="jsk", name="retain")
    async def jsk_retain(self, ctx: commands.Context, *, toggle: bool = None):
        """
        Поверните переменную удержание для Repl On или Off.

        Не указывать аргументации для текущего статуса.
        """

        if toggle is None:
            if self.retain:
                return await ctx.send("Удержание переменной установлено на ON")

            return await ctx.send("Удержание переменной установлено на OFF")

        if toggle:
            if self.retain:
                return await ctx.send("Удержание переменной уже установлено на ON.")

            self.retain = True
            self._scope = Scope()
            return await ctx.send("Удержание переменной включена. Будущие сеансы Reply сохранят свои действия.")

        if not self.retain:
            return await ctx.send("Удержание переменной уже установлено на OFF.")

        self.retain = False
        return await ctx.send("Удержание переменной выключена. Будущие сессии Reply избавят свои возможности, когда закончите.")

    async def jsk_python_result_handling(self, ctx: commands.Context, result):
        """
        Determines what is done with a result when it comes out of jsk py.
        This allows you to override how this is done without having to rewrite the command itself.
        What you return is what gets stored in the temporary _ variable.
        """

        handle = os.getenv('JISHAKU_PY_RES', 'true')

        if handle not in DISABLED_SYMBOLS:
            if isinstance(result, disnake.Message):
                return await ctx.send(f"<Сообщение <{result.jump_url}>>")

            if isinstance(result, disnake.File):
                return await ctx.send(file=result)

            if isinstance(result, disnake.Embed):
                return await ctx.send(embed=result)

            if isinstance(result, PaginatorInterface):
                return await result.send_to(ctx)

            if not isinstance(result, str):
                # Решить все не-стряхи
                result = repr(result)

        if isinstance(result, str):
            if len(result) <= 2000:
                if result.strip() == '':
                    result = "\u200b"

                return await ctx.send(result.replace(self.bot.http.token, "[token omitted]"))

            if use_file_check(ctx, len(result)):  # Файл "Полный контент" Предел предварительного просмотра
                # Discord's Desktop и веб -клиент теперь поддерживают интерактивный файловый контент
                #  отображать для файлов, кодируемых в UTF-8.
                # Поскольку это избегает проблем с побегом и является более интуитивно понятным, чем страниц для
                #  длинные результаты, теперь он будет расставлен в приоритет по PaginatorInterface, если
                #  Результирующий контент ниже порога размера файлов
                return await ctx.send(file=disnake.File(
                    filename="output.py",
                    fp=io.BytesIO(result.encode('utf-8'))
                ))

            # несоответствие здесь, результаты обернуты в кодовые блоки, когда они слишком большие
            #  Но не так ли, если они нет.Вероятно, не так уж и плохо, но отмечая для последующего обзора
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

            paginator.add_line(result)

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            return await interface.send_to(ctx)

    @Feature.Command(parent="jsk", name="py", aliases=["python"])
    async def jsk_python(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Прямая оценка кода Python.
        """

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict["_"] = self.last_result

        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):
                        if result is None:
                            continue

                        self.last_result = result

                        send(await self.jsk_python_result_handling(ctx, result))

        finally:
            scope.clear_intersection(arg_dict)

    @Feature.Command(parent="jsk", name="py_inspect", aliases=["pyi", "python_inspect", "pythoninspect"])
    async def jsk_python_inspect(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Оценка кода Python с проверкой информации.
        """

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict["_"] = self.last_result

        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):
                        self.last_result = result

                        header = repr(result).replace("``", "`\u200b`").replace(self.bot.http.token, "[token omitted]")

                        if len(header) > 485:
                            header = header[0:482] + "..."

                        lines = [f"=== {header} ===", ""]

                        for name, res in all_inspections(result):
                            lines.append(f"{name:16.16} :: {res}")

                        text = "\n".join(lines)

                        if use_file_check(ctx, len(text)):  # Файл "Полный контент" Предел предварительного просмотра
                            send(await ctx.send(file=disnake.File(
                                filename="inspection.prolog",
                                fp=io.BytesIO(text.encode('utf-8'))
                            )))
                        else:
                            paginator = WrappedPaginator(prefix="```prolog", max_size=1985)

                            paginator.add_line(text)

                            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                            send(await interface.send_to(ctx))
        finally:
            scope.clear_intersection(arg_dict)

    @Feature.Command(parent="jsk", name="dis", aliases=["disassemble"])
    async def jsk_disassemble(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Разберите код Python в Bytecode.
        """

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)

        async with ReplResponseReactor(ctx.message):
            text = "\n".join(disassemble(argument.content, arg_dict=arg_dict))

            if use_file_check(ctx, len(text)):  # Файл "Полный контент" Предел предварительного просмотра
                await ctx.send(file=disnake.File(
                    filename="dis.py",
                    fp=io.BytesIO(text.encode('utf-8'))
                ))
            else:
                paginator = WrappedPaginator(prefix='```py', max_size=1985)

                paginator.add_line(text)

                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                await interface.send_to(ctx)
