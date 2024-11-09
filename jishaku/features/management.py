# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import itertools
import math
import time
import traceback
from urllib.parse import urlencode
import os
import sys

import disnake
from disnake.ext import commands

from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.modules import ExtensionConverter
from jishaku.paginators import WrappedPaginator


class ManagementFeature(Feature):
    """
    Feature containing the extension and bot control commands
    """

    @Feature.Command(parent="jsk", name="load", aliases=["reload"])
    async def jsk_load(self, ctx: commands.Context, *extensions: ExtensionConverter):
        """
        Loads or reloads the given extension names.

        Reports any extensions that failed to load.
        """

        paginator = WrappedPaginator(prefix='', suffix='')

        # 'jsk reload' on its own just reloads jishaku
        if ctx.invoked_with == 'reload' and not extensions:
            extensions = [['jishaku']]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                method(extension)
            except Exception as exc:
                traceback_data = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @Feature.Command(parent="jsk", name="unload")
    async def jsk_unload(self, ctx: commands.Context, *extensions: ExtensionConverter):
        """
        Unloads the given extension names.

        Reports any extensions that failed to unload.
        """

        paginator = WrappedPaginator(prefix='', suffix='')
        icon = "\N{OUTBOX TRAY}"

        for extension in itertools.chain(*extensions):
            try:
                self.bot.unload_extension(extension)
            except Exception as exc:
                traceback_data = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @Feature.Command(parent="jsk", name="shutdown", aliases=["logout"])
    async def jsk_shutdown(self, ctx: commands.Context):
        """
        Logs this bot out.
        """

        ellipse_character = "\N{BRAILLE PATTERN DOTS-356}" if Flags.USE_BRAILLE_J else "\N{HORIZONTAL ELLIPSIS}"

        await ctx.send(f"Выход из системы...{ellipse_character}")
        await ctx.bot.close()

    @Feature.Command(parent="jsk", name="restart", aliases=["reboot"])
    async def jsk_reboot(self, ctx: commands.Context):
        """
        reboot.
        """

        ellipse_character = "\N{BRAILLE PATTERN DOTS-356}" if Flags.USE_BRAILLE_J else "\N{HORIZONTAL ELLIPSIS}"

        await ctx.send(f"Перезагрузка...{ellipse_character}")
        await ctx.bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)
        await ctx.send("Перезагрузка завершена.")

    @Feature.Command(parent="jsk", name="invite")
    async def jsk_invite(self, ctx: commands.Context, *perms: str):
        """
        Retrieve the invite URL for this bot.

        If the names of permissions are provided, they are requested as part of the invite.
        """

        scopes = ('bot', 'applications.commands')
        permissions = disnake.Permissions()

        for perm in perms:
            if perm not in dict(permissions):
                raise commands.BadArgument(f"Недопустимое разрешение: {perm}")

            setattr(permissions, perm, True)

        application_info = await self.bot.application_info()

        query = {
            "client_id": application_info.id,
            "scope": "+".join(scopes),
            "permissions": permissions.value
        }

        return await ctx.send(
            f"Ссылка на добавление бота:\n<https://discordapp.com/oauth2/authorize?{urlencode(query, safe='+')}>"
        )

    @Feature.Command(parent="jsk", name="rtt", aliases=["ping"])
    async def jsk_rtt(self, ctx: commands.Context):
        """
        Calculates Round-Trip Time to the API.
        """

        message = None

        # We'll show each of these readings as well as an average and standard deviation.
        api_readings = []
        # We'll also record websocket readings, but we'll only provide the average.
        websocket_readings = []

        # We do 6 iterations here.
        # This gives us 5 visible readings, because a request can't include the stats for itself.
        for _ in range(6):
            # First generate the text
            text = "Расчет времени в пути туда и обратно...\n\n"
            text += "\n".join(f"Чтение {index + 1}: {reading * 1000:.2f}ms" for index, reading in enumerate(api_readings))

            if api_readings:
                average = sum(api_readings) / len(api_readings)

                if len(api_readings) > 1:
                    stddev = math.sqrt(sum(math.pow(reading - average, 2) for reading in api_readings) / (len(api_readings) - 1))
                else:
                    stddev = 0.0

                text += f"\n\nСреднее: {average * 1000:.2f} \N{PLUS-MINUS SIGN} {stddev * 1000:.2f}ms"
            else:
                text += "\n\nПоказаний пока нет."

            if websocket_readings:
                average = sum(websocket_readings) / len(websocket_readings)

                text += f"\nЗадержка вебсокета: {average * 1000:.2f}ms"
            else:
                text += f"\nЗадержка вебсокета: {self.bot.latency * 1000:.2f}ms"

            # Now do the actual request and reading
            if message:
                before = time.perf_counter()
                await message.edit(content=text)
                after = time.perf_counter()

                api_readings.append(after - before)
            else:
                before = time.perf_counter()
                message = await ctx.send(content=text)
                after = time.perf_counter()

                api_readings.append(after - before)

            # Ignore websocket latencies that are 0 or negative because they usually mean we've got bad heartbeats
            if self.bot.latency > 0.0:
                websocket_readings.append(self.bot.latency)

    @Feature.Command(parent="jsk", name="help", aliases=["commands"])
    async def jsk_help(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Список доступных команд в категории jsk.
        """

        commands_info = {
            "cancel": "Отменяет задачу с указанным индексом.",
            "cat": "Читает файл, используя подсветку синтаксиса.",
            "curl": "Скачивает и отображает текстовый файл из интернета.",
            "debug": "Запускает команду, измеряя время выполнения.",
            "dis": "Дизассемблирует код Python в байт-код.",
            "git": "Сокращение для 'jsk sh git'. Вызывает системную оболочку.",
            "hide": "Скрывает Jishaku из команды help.",
            "invite": "Получает URL-адрес приглашения для этого бота.",
            "load": "Загружает или перезагружает указанные имена расширений.",
            "override": "Запускает команду от имени другого пользователя, канала или потока, с до... ",
            "permtrace": "Вычисляет источник предоставленных или отклоненных разрешений.",
            "pip": "Сокращение для 'jsk sh pip'. Вызывает системную оболочку.",
            "py": "Прямая оценка кода Python.",
            "py_inspect": "Оценка кода Python с информацией о проверке.",
            "repeat": "Запускает команду несколько раз подряд.",
            "retain": "Включает или отключает сохранение переменных для REPL.",
            "rtt": "Вычисляет время двусторонней передачи данных до API.",
            "shell": "Выполняет команды в системной оболочке.",
            "show": "Показывает Jishaku в команде help.",
            "shutdown": "Выводит этого бота из системы.",
            "source": "Отображает исходный код для команды.",
            "tasks": "Показывает запущенные задачи jishaku.",
            "unload": "Отключает указанные имена расширений.",
            "voice": "Команды, связанные с голосом.",
        }

        commands_list = list(commands_info.items())
        mid_index = len(commands_list) // 2
        page1_commands = commands_list[:mid_index]
        page2_commands = commands_list[mid_index:]

        is_embedded = os.environ.get('JISHAKU_EMBEDDED_JSK', 'false').lower() == 'true'
        
        current_page = 1  # Текущая страница

        if is_embedded:
            embed = disnake.Embed(title="Команды | 1 Страница", description="Список доступных команд")
            for command, description in page1_commands:
                embed.add_field(name=command, value=description, inline=False)
            message = await ctx.send(embed=embed)
        else:
            text_response = "Команды | 1 Страница:\n" + "\n".join(f"**{command}**: {description}" for command, description in page1_commands)
            message = await ctx.send(text_response)

        button_page1 = disnake.ui.Button(label="<—", style=disnake.ButtonStyle.secondary, disabled=True)
        button_page2 = disnake.ui.Button(label="—>", style=disnake.ButtonStyle.secondary)

        view = disnake.ui.View()
        view.add_item(button_page1)
        view.add_item(button_page2)

        async def update_message(page):
            nonlocal current_page
            current_page = page

            if current_page == 1:
                button_page1.disabled = True
                button_page2.disabled = False
                commands_to_display = page1_commands
            else:
                button_page1.disabled = False
                button_page2.disabled = True
                commands_to_display = page2_commands

            if is_embedded:
                embed.title = f"Команды | {current_page} Страница"  # Обновляем заголовок
                embed.clear_fields()
                for command, description in commands_to_display:
                    embed.add_field(name=command, value=description, inline=False)
                await message.edit(embed=embed, view=view)
            else:
                text_response = f"Команды | {current_page} Страница:\n" + "\n".join(f"**{command}**: {description}" for command, description in commands_to_display)
                await message.edit(content=text_response, view=view)

        async def button_page1_callback(interaction: disnake.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Это не ваша кнопка!", ephemeral=True)
                return
            await update_message(1)
            await interaction.response.defer()

        async def button_page2_callback(interaction: disnake.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Это не ваша кнопка!", ephemeral=True)
                return
            await update_message(2)
            await interaction.response.defer()

        button_page1.callback = button_page1_callback
        button_page2.callback = button_page2_callback

        await message.edit(view=view)
