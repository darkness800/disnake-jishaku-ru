# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, Смотрите лицензию для более подробной информации.

"""

import asyncio
import inspect
from io import BytesIO

import disnake
import pytest
import utils
from disnake.ext import commands

from jishaku.paginators import FilePaginator, PaginatorEmbedInterface, PaginatorInterface, WrappedPaginator


def test_file_paginator():

    base_text = inspect.cleandoc("""
    #!/usr/bin/env python
    # -*- coding: utf-8 -*-
    pass  # \u3088\u308d\u3057\u304f
    """)

    # Проверьте стандартное кодирование
    pages = FilePaginator(BytesIO(base_text.encode("utf-8"))).pages

    assert len(pages) == 1
    assert pages[0] == f"```python\n{base_text}\n```"

    # Тестовые линии
    pages = FilePaginator(BytesIO(base_text.encode("utf-8")), line_span=(2, 2)).pages

    assert len(pages) == 1
    assert pages[0] == "```python\n# -*- coding: utf-8 -*-\n```"

    # тестовый прием для кодирования подсказки
    base_text = inspect.cleandoc("""
    #!/usr/bin/env python
    # -*- coding: cp932 -*-
    pass  # \u3088\u308d\u3057\u304f
    """)

    pages = FilePaginator(BytesIO(base_text.encode("cp932"))).pages

    assert len(pages) == 1
    assert pages[0] == f"```python\n{base_text}\n```"

    # тест без кодирования подсказки
    with pytest.raises(UnicodeDecodeError):
        FilePaginator(BytesIO("\u3088\u308d\u3057\u304f".encode("cp932")))

    # Проверка с неправильным подсказкой
    with pytest.raises(UnicodeDecodeError):
        FilePaginator(BytesIO("-*- coding: utf-8 -*-\n\u3088\u308d\u3057\u304f".encode("cp932")))

    # Проверка ооб
    with pytest.raises(ValueError):
        FilePaginator(BytesIO("one\ntwo\nthree\nfour".encode('utf-8')), line_span=(-1, 20))


def test_wrapped_paginator():
    paginator = WrappedPaginator(max_size=200)
    paginator.add_line("abcde " * 50)
    assert len(paginator.pages) == 2

    paginator = WrappedPaginator(max_size=200, include_wrapped=False)
    paginator.add_line("abcde " * 50)
    assert len(paginator.pages) == 2


@pytest.mark.skipif(
    disnake.version_info >= (2, 0, 0),
    reason="Тесты с реакционной моделью границы раздела Paginator"
)
@utils.run_async
async def test_paginator_interface_reactions():
    bot = commands.Bot('?')

    with open(__file__, 'rb') as file:
        paginator = FilePaginator(file, max_size=200)

    interface = PaginatorInterface(bot, paginator)

    assert interface.pages == paginator.pages
    assert interface.page_count == len(paginator.pages)

    assert interface.page_size > 200
    assert interface.page_size < interface.max_page_size

    send_kwargs = interface.send_kwargs

    assert isinstance(send_kwargs, dict)
    assert 'content' in send_kwargs

    content = send_kwargs['content']

    assert isinstance(content, str)
    assert len(content) <= interface.page_size

    assert interface.display_page == 0

    # Страницы были закрыты, поэтому добавление строки должно сделать новую страницу
    old_page_count = interface.page_count

    await interface.add_line('a' * 150)

    assert interface.page_count > old_page_count

    # подтолкнуть страницу до конца (округлено на границы)
    interface.display_page = 999
    old_display_page = interface.display_page

    assert interface.pages == paginator.pages

    # Страница закрыта, поэтому создайте новую страницу
    await interface.add_line('b' * 150)

    # Убедитесь, что страница следовала за хвостом
    assert interface.display_page > old_display_page

    # Тестирование с помощью интерфейса встроенного
    embed_interface = PaginatorEmbedInterface(bot, paginator)

    assert embed_interface.pages[0] == interface.pages[0]

    send_kwargs = embed_interface.send_kwargs

    assert isinstance(send_kwargs, dict)
    assert 'embed' in send_kwargs

    embed = send_kwargs['embed']

    assert isinstance(embed, disnake.Embed)

    description = embed.description

    assert content.startswith(description)

    # Проверьте, чтобы получить повышение слишком большого размера страницы
    with pytest.raises(ValueError):
        PaginatorInterface(None, commands.Paginator(max_size=2000))

    # Проверьте на повышение на не-пагинаторе
    with pytest.raises(TypeError):
        PaginatorInterface(None, 4)

    paginator = commands.Paginator(max_size=100)
    for _ in range(100):
        paginator.add_line("test text")

    # тест взаимодействия
    with utils.mock_ctx(bot) as ctx:
        interface = PaginatorInterface(bot, paginator)

        assert not interface.closed

        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        assert interface.page_count > 1
        assert not interface.closed

        interface.message.id = utils.sentinel()

        current_page = interface.display_page

        payload = {
            'message_id': interface.message.id,
            'user_id': ctx.author.id,
            'channel_id': ctx.channel.id,
            'guild_id': ctx.guild.id
        }

        # Нажмите правую кнопку
        emoji = disnake.PartialEmoji(
            animated=False,
            name="\N{BLACK RIGHT-POINTING TRIANGLE}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            disnake.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if disnake.version_info >= (1, 3) else
            disnake.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page > current_page
        assert not interface.closed

        current_page = interface.display_page

        # Нажмите на левую кнопку
        emoji = disnake.PartialEmoji(
            animated=False,
            name="\N{BLACK LEFT-POINTING TRIANGLE}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            disnake.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if disnake.version_info >= (1, 3) else
            disnake.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page < current_page
        assert not interface.closed

        # Нажмите кнопку последней страницы
        emoji = disnake.PartialEmoji(
            animated=False,
            name="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            disnake.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if disnake.version_info >= (1, 3) else
            disnake.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page == interface.page_count - 1
        assert not interface.closed

        # Нажмите кнопку первой страницы
        emoji = disnake.PartialEmoji(
            animated=False,
            name="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            disnake.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if disnake.version_info >= (1, 3) else
            disnake.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page == 0
        assert not interface.closed

        # Нажмите кнопку закрытия
        emoji = disnake.PartialEmoji(
            animated=False,
            name="\N{BLACK SQUARE FOR STOP}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            disnake.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if disnake.version_info >= (1, 3) else
            disnake.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.closed
        ctx.send.coro.return_value.delete.assert_called_once()

    # тестировать повторную работу, без удаления
    with utils.mock_ctx(bot) as ctx:
        interface = PaginatorInterface(bot, paginator)

        assert not interface.closed

        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        assert interface.page_count > 1
        assert not interface.closed

        # приезжать
        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        ctx.send.coro.return_value.delete.assert_not_called()

        interface.task.cancel()
        await asyncio.sleep(0.1)

        assert interface.closed

    # Тестирование повторно, удалите
    with utils.mock_ctx(bot) as ctx:
        interface = PaginatorInterface(bot, paginator, delete_message=True)

        assert not interface.closed

        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        assert interface.page_count > 1
        assert not interface.closed

        # приезжать
        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        ctx.send.coro.return_value.delete.assert_called_once()

        interface.task.cancel()
        await asyncio.sleep(0.1)

        assert interface.closed

# TODO: Написать тест на интерфейс на основе взаимодействий на основе взаимодействий
