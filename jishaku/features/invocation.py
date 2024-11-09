# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import contextlib
import inspect
import io
import pathlib
import re
import time
import typing

import disnake
from disnake.ext import commands
from disnake.ext.commands.slash_core import (
    InvokableSlashCommand,
    SubCommandGroup,
    SubCommand
)

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.models import copy_context_with
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check

UserIDConverter = commands.IDConverter[disnake.User]


class SlimUserConverter(UserIDConverter):
    """
    Идентичный аккумулятору, но не выполняет проверки имен открытого текста.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> disnake.User:
        """Метод преобразователя"""
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]{15,20})>$', argument)

        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id) or disnake.utils.get(ctx.message.mentions, id=user_id)
            if result is None:
                try:
                    result = await ctx.bot.fetch_user(user_id)
                except disnake.HTTPException:
                    raise commands.UserNotFound(argument) from None

            return result

        raise commands.UserNotFound(argument)


class InvocationFeature(Feature):
    """
    Функция, содержащая команды, связанные с вызовами команды
    """

    OVERRIDE_SIGNATURE = typing.Union[SlimUserConverter, disnake.TextChannel, disnake.Thread]

    @Feature.Command(parent="jsk", name="override", aliases=["execute", "exec", "override!", "execute!", "exec!"])
    async def jsk_override(
        self, ctx: commands.Context,
        overrides: commands.Greedy[OVERRIDE_SIGNATURE],
        *, command_string: str
    ):
        """
        Запустите команду с другим пользователем, каналом или потоком, опционально обойдя проверки и восстановления.

        Пользователи попытаются решить с участником, но будут использовать пользователя, если он не сможет его найти.
        """

        kwargs = {
            "content": ctx.prefix + command_string.lstrip('/')
        }

        for override in overrides:
            if isinstance(override, disnake.User):
                # Это пользователь
                if ctx.guild:
                    # Попробуйте перейти на экземпляр участника
                    # Раньше это делалось с помощью профсоюзного конвертера, но делать это так делает
                    #  Команда более совместима с цепочкой, например,`jsk in .. jsk su ..`
                    target_member = None

                    with contextlib.suppress(disnake.HTTPException):
                        target_member = ctx.guild.get_member(override.id) or await ctx.guild.fetch_member(override.id)

                    kwargs["author"] = target_member or override
                else:
                    kwargs["author"] = override
            else:
                # В противном случае это текстовый канал или поток
                kwargs["channel"] = override

        alt_ctx = await copy_context_with(ctx, **kwargs)

        if alt_ctx.command is None:
            if alt_ctx.invoked_with is None:
                return await ctx.send('Этот бот был жестко настроен на игнорирование этого пользователя.')
            return await ctx.send('Команда "{alt_ctx.invoked_with}" не существует.')

        if ctx.invoked_with.endswith('!'):
            return await alt_ctx.command.reinvoke(alt_ctx)

        return await alt_ctx.command.invoke(alt_ctx)

    @Feature.Command(parent="jsk", name="repeat")
    async def jsk_repeat(self, ctx: commands.Context, times: int, *, command_string: str):
        """
        Запускает команду несколько раз подряд.

        Это действует так, как команда была вызвана несколько раз вручную, так что это подчиняется усаживанию.
        Вы можете использовать это в сочетании с `JSK Sudo`, чтобы обойти это.
        """

        with self.submit(ctx):  # Разрешить повторения быть отменены
            for _ in range(times):
                alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

                if alt_ctx.command is None:
                    return await ctx.send(f'Команда "{alt_ctx.invoked_with}" не существует.')

                await alt_ctx.command.reinvoke(alt_ctx)

    @Feature.Command(parent="jsk", name="debug", aliases=["dbg"])
    async def jsk_debug(self, ctx: commands.Context, *, command_string: str):
        """
        Запустите выполнение времени команды и улавливая исключения.
        """

        alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Команда "{alt_ctx.invoked_with}" не существует.')

        start = time.perf_counter()

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                await alt_ctx.command.invoke(alt_ctx)

        end = time.perf_counter()
        return await ctx.send(f"Команда `{alt_ctx.command.qualified_name}` выполнена за {end - start:.3f}сек.")

    def get_slash_command(
        self,
        name: str
    ) -> typing.Optional[typing.Union[InvokableSlashCommand, SubCommandGroup, SubCommand]]:
        """Работает как ``Bot.get_command``, Но для ударов.

        Параметры
        -----------
        имя: :class:`str`
            Имя команды Slash, чтобы получить.

        Возврат
        --------
        Optional[Union[:class:`InvokableSlashCommand`, :class:`SubCommandGroup`, :class:`SubCommand`]]
            Команда SLASH, которая была запрошена.Если не найдено, возвращается ``None``.
        """

        if not isinstance(name, str):
            raise TypeError(f"Ожидаемое имя должно быть str, а не {name.__class__}")

        command = name.split()
        slash = self.bot.get_slash_command(command[0])
        if slash:
            if len(command) == 1:
                return slash
            elif len(command) == 2:
                cmd = slash.children.get(command[1])
                return cmd
            elif len(command) == 3:
                group = slash.children.get(command[1])
                if isinstance(group, SubCommandGroup):
                    cmd = group.children.get(command[2])
                    return cmd

        return None

    @Feature.Command(parent="jsk", name="source", aliases=["src"])
    async def jsk_source(self, ctx: commands.Context, *, command_name: str):
        """
        Отображает исходный код для команды.
        """

        command = self.bot.get_command(command_name) or self.get_slash_command(command_name)
        if not command:
            return await ctx.send(f"Не удалось найти команду `{command_name}`.")

        try:
            source_lines, _ = inspect.getsourcelines(command.callback)
        except (TypeError, OSError):
            return await ctx.send(f"По какой-то причине не удалось получить исходный код для `{command}`.")

        filename = "source.py"

        try:
            filename = pathlib.Path(inspect.getfile(command.callback)).name
        except (TypeError, OSError):
            pass

        # Getourcelines по какой -то причине возвращается с линейными окончаниями
        source_text = ''.join(source_lines)

        if use_file_check(ctx, len(source_text)):  # Файл "Полный контент" Предел предварительного просмотра
            await ctx.send(file=disnake.File(
                filename=filename,
                fp=io.BytesIO(source_text.encode('utf-8'))
            ))
        else:
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

            paginator.add_line(source_text.replace('```', '``\N{zero width space}`'))

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)
