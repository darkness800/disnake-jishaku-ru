# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import asyncio
import subprocess
import traceback
import typing

import disnake
from disnake.ext import commands

from jishaku.flags import Flags


async def send_traceback(destination: disnake.abc.Messageable, verbosity: int, *exc_info):
    """
    Отправляет трассировку исключения из пункта назначения.
    Используется, когда реплика не удается по любой причине.

    :param destination: Куда отправить эту информацию
    :param verbosity: Как далеко должен идти этот трассировка.0 показывает только последний стек.
    :param exc_info: Информация об этом исключении, от sys.exc_info или аналогичного.
    :return: Последнее сообщение отправлено
    """

    etype, value, trace = exc_info

    traceback_content = "".join(traceback.format_exception(etype, value, trace, verbosity)).replace("``", "`\u200b`")

    paginator = commands.Paginator(prefix='```py')
    for line in traceback_content.split('\n'):
        paginator.add_line(line)

    message = None

    for page in paginator.pages:
        message = await destination.send(page)

    return message


async def do_after_sleep(delay: float, coro, *args, **kwargs):
    """
    Выполняет действие после установленного количества времени.

    Эта функция вызывает кораку только после задержки,
    Предотвращение жалоб асинсио на разрушенные короны.

    :param delay: Время за считанные секунды
    :param coro: Coroutine для бега
    :param args: Аргументы, чтобы передать в Coroutine
    :param kwargs: Аргументы ключевого слова для перехода в Coroutine
    :return: Что бы ни вернулась коратика.
    """
    await asyncio.sleep(delay)
    return await coro(*args, **kwargs)


async def attempt_add_reaction(msg: disnake.Message, reaction: typing.Union[str, disnake.Emoji])\
        -> typing.Optional[disnake.Reaction]:
    """
    Попробуйте добавить реакцию на сообщение, игнорируя его, если оно не по какой -либо причине.
    :param msg: Сообщение, чтобы добавить реакцию.
    :param reaction: Реакция эмодзи, может быть строкой или `disnake.Emoji`
    :return: а `disnake.Reaction` или нет, в зависимости от того, не удалось или нет.
    """
    try:
        return await msg.add_reaction(reaction)
    except disnake.HTTPException:
        pass


class ReactionProcedureTimer:
    """
    Класс, который реагирует на сообщение, основанное на том, что происходит в течение его жизни.
    """
    __slots__ = ('message', 'loop', 'handle', 'raised')

    def __init__(self, message: disnake.Message, loop: typing.Optional[asyncio.BaseEventLoop] = None):
        self.message = message
        self.loop = loop or asyncio.get_event_loop()
        self.handle = None
        self.raised = False

    async def __aenter__(self):
        self.handle = self.loop.create_task(do_after_sleep(1, attempt_add_reaction, self.message,
                                                           "\N{BLACK RIGHT-POINTING TRIANGLE}"))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.handle:
            self.handle.cancel()

        # Нет исключения, отметка
        if not exc_val:
            await attempt_add_reaction(self.message, "\N{WHITE HEAVY CHECK MARK}")
            return

        self.raised = True

        if isinstance(exc_val, (asyncio.TimeoutError, subprocess.TimeoutExpired)):
            # Временный, будильник
            await attempt_add_reaction(self.message, "\N{ALARM CLOCK}")
        elif isinstance(exc_val, SyntaxError):
            # Ошибка синтаксиса, одиночная восклицательная отметка
            await attempt_add_reaction(self.message, "\N{HEAVY EXCLAMATION MARK SYMBOL}")
        else:
            # Другая ошибка, двойной восклицательный знак
            await attempt_add_reaction(self.message, "\N{DOUBLE EXCLAMATION MARK}")


class ReplResponseReactor(ReactionProcedureTimer):
    """
    Расширение реакционного процесса, которое поглощает ошибки, отправляя трассировки.
    """

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)

        # Ничто не пошло не так, кого это волнует, лол
        if not exc_val:
            return

        if isinstance(exc_val, (SyntaxError, asyncio.TimeoutError, subprocess.TimeoutExpired)):
            # Короткий след, отправить на канал
            await send_traceback(self.message.channel, 0, exc_type, exc_val, exc_tb)
        else:
            # Этот след, вероятно, нуждается в большей информации, поэтому увеличивайте многословие, и вместо этого DM.
            await send_traceback(
                self.message.channel if Flags.NO_DM_TRACEBACK else self.message.author,
                8, exc_type, exc_val, exc_tb
            )

        return True  # исключение было обработано
