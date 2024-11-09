# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import asyncio
import functools
import typing


def executor_function(sync_function: typing.Callable):
    """Декоратор, который окутает функцию синхронизации в исполнителе, превращая ее в асинхронную функцию.

    Это позволяет обернуть и использовать и использовать функции обработки в качестве асинхронной функции.

    Примеры
    ---------

    Проталкивание обработки с помощью библиотеки изображений Python в исполнителя:

    .. code-block:: python3

        from io import BytesIO
        from PIL import Image

        from jishaku.functools import executor_function


        @executor_function
        def color_processing(color: disnake.Color):
            with Image.new('RGB', (64, 64), color.to_rgb()) as im:
                buff = BytesIO()
                im.save(buff, 'png')

            buff.seek(0)
            return buff

        @bot.command()
        async def color(ctx: commands.Context, color: disnake.Color=None):
            color = color or ctx.author.color
            buff = await color_processing(color=color)

            await ctx.send(file=disnake.File(fp=buff, filename='color.png'))
    """

    @functools.wraps(sync_function)
    async def sync_wrapper(*args, **kwargs):
        """
        Асинхронная функция, которая завершает функцию синхронизации с исполнителем.
        """

        loop = asyncio.get_event_loop()
        internal_function = functools.partial(sync_function, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return sync_wrapper


class AsyncSender:
    """
    Класс потока хранения и управления, который позволяет более красиво отправлять в асинхронные итераторы.

    Пример
    --------

    .. code:: python3

        async def foo():
            print("foo yielding 1")
            x = yield 1
            print(f"foo received {x}")
            yield 3

        async for send, result in AsyncSender(foo()):
            print(f"asyncsender received {result}")
            send(2)

    Produces:

    .. code::

        foo yielding 1
        asyncsender received 1
        foo received 2
        asyncsender received 3
    """

    __slots__ = ('iterator', 'send_value')

    def __init__(self, iterator):
        self.iterator = iterator
        self.send_value = None

    def __aiter__(self):
        return self._internal(self.iterator.__aiter__())

    async def _internal(self, base):
        try:
            while True:
                # Send the last value to the iterator
                value = await base.asend(self.send_value)
                # Reset it incase one is not sent next iteration
                self.send_value = None
                # Yield sender and iterator value
                yield self.set_send_value, value
        except StopAsyncIteration:
            pass

    def set_send_value(self, value):
        """
        Устанавливает следующее значение, которое будет отправлено в итератор.

        Это обеспечивается итерацией этого класса и должно
        не называться напрямую.
        """

        self.send_value = value
