# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import asyncio

import disnake
from disnake import ui
from disnake.ext import commands

from jishaku.shim.paginator_base import EMOJI_DEFAULT


class PaginatorInterface(ui.View):
    """
    Интерфейс на основе сообщений и реакции для пагинаторов.

    Это позволяет пользователям интерактивно ориентироваться в страницах Paginator и поддерживает живые выводы.

    Пример того, как использовать это со стандартным язычником:

    .. code:: python3

        from disnake.ext import commands

        from jishaku.paginators import PaginatorInterface

        # Где -то в команде ...
            # Паниторы должны иметь уменьшенный MAX_SIZE, чтобы приспособить дополнительный текст, добавленный интерфейсом.
            paginator = commands.Paginator(max_size=1900)

            # Заполнить пагинатора некоторой информацией
            for line in range(100):
                paginator.add_line(f"Line {line + 1}")

            # Создать и отправить интерфейс.
            # Поле «владельца» определяет, кто может взаимодействовать с этим интерфейсом.Если это не так, кто -нибудь может использовать его.
            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)

            # send_to создает задачу и возвращает поток управления.
            # Он поднимется, если интерфейс не может быть создан, например, если в канале нет разрешения на реакцию.
            # После того, как интерфейс был отправлен, дополнения линии должны быть сделаны асинхронно, поэтому интерфейс можно обновить.
            await interface.add_line("My, the Earth sure is full of things!")

            # Вы также можете проверить, закрыт ли он, используя свойство «закрыто».
            if not interface.closed:
                await interface.add_line("I'm still here!")
    """

    def __init__(self, bot: commands.Bot, paginator: commands.Paginator, **kwargs):
        if not isinstance(paginator, commands.Paginator):
            raise TypeError('Пагинатор должен быть командами.')

        self._display_page = 0

        self.bot = bot

        self.message = None
        self.paginator = paginator

        self.owner = kwargs.pop('owner', None)
        self.emojis = kwargs.pop('emoji', EMOJI_DEFAULT)
        self.timeout = kwargs.pop('timeout', 7200)
        self.delete_message = kwargs.pop('delete_message', False)

        self.sent_page_reactions = False

        self.task: asyncio.Task = None
        self.send_lock: asyncio.Event = asyncio.Event()

        self.close_exception: Exception = None

        if self.page_size > self.max_page_size:
            raise ValueError(
                f'Парень с патентором имеет слишком большой размер страницы для этого интерфейса. '
                f'({self.page_size} > {self.max_page_size})'
            )

        super().__init__(timeout=self.timeout)

    @property
    def pages(self):
        """
        Возвращает страницы Paginator без преждевременного закрытия активной страницы.
        """
        # Защищенный доступ должен быть разрешен здесь, чтобы не закрывать страницы пагинатора

        paginator_pages = list(self.paginator._pages)
        if len(self.paginator._current_page) > 1:
            paginator_pages.append('\n'.join(self.paginator._current_page) + '\n' + (self.paginator.suffix or ''))

        return paginator_pages

    @property
    def page_count(self):
        """
        Возвращает количество страниц внутреннего пагинатора.
        """

        return len(self.pages)

    @property
    def display_page(self):
        """
        Возвращает текущую страницу. Включен интерфейс Paginator.
        """

        self._display_page = max(0, min(self.page_count - 1, self._display_page))
        return self._display_page

    @display_page.setter
    def display_page(self, value):
        """
        Устанавливает текущую страницу, включенная на пенсионере.Автоматически выдвигает значения входящих.
        """

        self._display_page = max(0, min(self.page_count - 1, value))

    max_page_size = 2000

    @property
    def page_size(self) -> int:
        """
        Свойство, которое возвращает, насколько большая страница, рассчитанная на основе свойств.

        Если это превышает `max_page_size`, исключение поднимается при экземпляре.
        """
        page_count = self.page_count
        return self.paginator.max_size + len(f'\nPage {page_count}/{page_count}')

    @property
    def send_kwargs(self) -> dict:
        """
        Свойство, которое возвращает Kwargs, отправленные для отправки/редактирования при обновлении страницы.

        Поскольку это должно быть совместимо с обоими `disnake.TextChannel.send` и `disnake.Message.edit`,
        это должен быть дикт, содержащий 'content', 'embed' или оба.
        """

        content = self.pages[self.display_page]
        return {'content': content, 'view': self}

    def update_view(self):
        """
        Обновления кнопок просмотра, соответствующие современному состоянию интерфейса.
        Это используется внутри.
        """

        self.button_start.label = f"1 \u200b {self.emojis.start}"
        self.button_previous.label = self.emojis.back
        self.button_current.label = str(self.display_page + 1)
        self.button_next.label = self.emojis.forward
        self.button_last.label = f"{self.emojis.end} \u200b {self.page_count}"
        self.button_close.label = f"{self.emojis.close} \u200b Закрыть пагинатор"

    async def add_line(self, *args, **kwargs):
        """
        Прокси -функция, которая позволяет этому PaginatorInterface оставаться заблокированной на последнюю страницу
        Если это уже на нем.
        """

        display_page = self.display_page
        page_count = self.page_count

        self.paginator.add_line(*args, **kwargs)

        new_page_count = self.page_count

        if display_page + 1 == page_count:
            # Чтобы сохранить позицию фиксированной в конце, обновить позицию на новую последнюю страницу и обновить сообщение.
            self._display_page = new_page_count

        # Безоговорочно установленные отправить блокировку, чтобы попробовать и гарантировать обновления страницы на нефокусированных страницах
        self.send_lock.set()

    async def send_to(self, destination: disnake.abc.Messageable):
        """
        Отправляет сообщение в заданный пункт назначения с этим интерфейсом.

        Это автоматически создает задачу ответа для вас.
        """

        self.message = await destination.send(**self.send_kwargs)

        self.send_lock.set()

        if self.task:
            self.task.cancel()

        self.task = self.bot.loop.create_task(self.wait_loop())

        return self

    @property
    def closed(self):
        """
        Этот интерфейс закрыт?
        """

        if not self.task:
            return False
        return self.task.done()

    async def send_lock_delayed(self):
        """
        Корука, которая возвращается через 1 секунду после выпуска блокировки отправки
        Это помогает уменьшить выброс спама, который быстро достигает ограничений.
        """

        gathered = await self.send_lock.wait()
        self.send_lock.clear()
        await asyncio.sleep(1)
        return gathered

    async def wait_loop(self):
        """
        Ждет в цикле для обновлений в интерфейсе.Это не следует называть вручную - это обрабатывается `send_to`.
        """

        try:
            while not self.bot.is_closed():
                await asyncio.wait_for(self.send_lock_delayed(), timeout=self.timeout)

                self.update_view()

                try:
                    await self.message.edit(**self.send_kwargs)
                except disnake.NotFound:
                    # произошло что -то ужасное
                    return

        except (asyncio.CancelledError, asyncio.TimeoutError) as exception:
            self.close_exception = exception

            if self.bot.is_closed():
                # Ничего не могу сделать с сообщениями, так что просто закройте, чтобы избежать шумной ошибки
                return

            # Если сообщение уже было удалено, эта часть не нужна
            if not self.message:
                return

            if self.delete_message:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    async def interaction_check(self, interaction: disnake.Interaction):
        """Проверьте, что определяет, должно ли это взаимодействие"""
        return not self.owner or interaction.user.id == self.owner.id

    @ui.button(label="1 \u200b \N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", style=disnake.ButtonStyle.secondary)
    async def button_start(self, button: ui.Button, interaction: disnake.Interaction):
        """Кнопка для отправки интерфейса на первую страницу"""

        self._display_page = 0
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK LEFT-POINTING TRIANGLE}", style=disnake.ButtonStyle.secondary)
    async def button_previous(self, button: ui.Button, interaction: disnake.Interaction):
        """Кнопка для отправки интерфейса на предыдущую страницу"""

        self._display_page -= 1
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="1", style=disnake.ButtonStyle.primary)
    async def button_current(self, button: ui.Button, interaction: disnake.Interaction):
        """Кнопка, чтобы обновить интерфейс"""

        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK RIGHT-POINTING TRIANGLE}", style=disnake.ButtonStyle.secondary)
    async def button_next(self, button: ui.Button, interaction: disnake.Interaction):
        """Кнопка для отправки интерфейса на следующую страницу"""

        self._display_page += 1
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR} \u200b 1", style=disnake.ButtonStyle.secondary)
    async def button_last(self, button: ui.Button, interaction: disnake.Interaction):
        """Кнопка для отправки интерфейса на последнюю страницу"""

        self._display_page = self.page_count - 1
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK SQUARE FOR STOP} \u200b Закрыть пагинатор", style=disnake.ButtonStyle.danger)
    async def button_close(self, button: ui.Button, interaction: disnake.Interaction):
        """Кнопка для закрытия интерфейса"""

        message = self.message
        self.message = None
        self.task.cancel()
        self.stop()
        await message.delete()


class PaginatorEmbedInterface(PaginatorInterface):
    """
    Подкласс :class:`PaginatorInterface` Это заключает содержание во вставку.
    """

    def __init__(self, *args, **kwargs):
        self._embed = kwargs.pop('embed', None) or disnake.Embed()
        super().__init__(*args, **kwargs)

    @property
    def send_kwargs(self) -> dict:
        self._embed.description = self.pages[self.display_page]
        return {'embed': self._embed, 'view': self}

    max_page_size = 2048

    @property
    def page_size(self) -> int:
        return self.paginator.max_size
