# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import asyncio
import collections
import contextlib
import typing
from datetime import datetime, timezone

from disnake.ext import commands

__all__ = (
    'Feature',
    'CommandTask'
)


CommandTask = collections.namedtuple("CommandTask", "index ctx task")


class Feature(commands.Cog):
    """
    Базовый определяющий функции компонентов Jishaku Cog.
    """

    class Command:
        """
        Промежуточный класс для команд функций.
        Экземпляры этого класса будут преобразованы в commands.command или commands.

        : param Parent: Чем должна быть основана эта команда.
        : PARAM STANDALONE_OK: должна ли команда быть разрешена быть автономной, если ее родитель не найден.
        """

        def __init__(self, parent: str = None, standalone_ok: bool = False, **kwargs):
            self.parent: typing.Union[str, Feature.Command] = parent
            self.standalone_ok = standalone_ok
            self.kwargs = kwargs
            self.callback = None
            self.depth: int = 0
            self.has_children: bool = False

        def __call__(self, callback: typing.Callable):
            self.callback = callback
            return self

    load_time: datetime = datetime.utcnow().replace(tzinfo=timezone.utc)

    def __init__(self, *args, **kwargs):
        self.bot: commands.Bot = kwargs.pop('bot')
        self.start_time: datetime = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.tasks = collections.deque()
        self.task_count: int = 0

        # Генерировать и прикрепить команды
        command_lookup = {}

        for kls in reversed(type(self).__mro__):
            for key, cmd in kls.__dict__.items():
                if isinstance(cmd, Feature.Command):
                    command_lookup[key] = cmd

        command_set = list(command_lookup.items())

        # Попробуйте связать каждую родительскую команду со своим родителем
        for key, cmd in command_set:
            cmd.parent_instance = None
            cmd.depth = 0

            if cmd.parent and isinstance(cmd.parent, str):
                if cmd.standalone_ok:
                    cmd.parent_instance = command_lookup.get(cmd.parent, None)
                else:
                    try:
                        cmd.parent_instance = command_lookup[cmd.parent]
                    except KeyError as exception:
                        raise RuntimeError(
                            f"Не удалось связать функциональную команду {ключ} с ее родительской командой {cmd.parent}"
                        ) from exception
            # Также поднимите, если какой -либо команды не хватает обратного вызова
            if cmd.callback is None:
                raise RuntimeError(f"В функциональной команде {key} отсутствует обратный вызов")

        # Назначьте глубину и has_children
        for key, cmd in command_set:
            parent = cmd.parent_instance
            # Повторяют родителей, увеличивая глубину, пока мы не достигнем вершины
            while parent:
                parent.has_children = True
                cmd.depth += 1
                parent = parent.parent_instance

        # Сортировать по глубине
        command_set.sort(key=lambda c: c[1].depth)
        association_map = {}

        self.feature_commands = {}

        for key, cmd in command_set:
            if cmd.parent:
                parent = association_map[cmd.parent_instance]
                command_type = parent.group if cmd.has_children else parent.command
            else:
                command_type = commands.group if cmd.has_children else commands.command

            association_map[cmd] = target_cmd = command_type(**cmd.kwargs)(cmd.callback)
            target_cmd.cog = self
            self.feature_commands[key] = target_cmd
            setattr(self, key, target_cmd)

        self.__cog_commands__ = (*self.__cog_commands__, *self.feature_commands.values())

        # Не думайте, что это много, но все равно инициирует.
        super().__init__(*args, **kwargs)

    async def cog_check(self, ctx: commands.Context):
        """
        Локальная проверка, делает все команды в полученных Cogs только владельца
        """

        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner("Вы должны владеть этим ботом, чтобы использовать Jishaku.")
        return True

    @contextlib.contextmanager
    def submit(self, ctx: commands.Context):
        """
        Контекст-менеджер, который передает текущую задачу в список задач Джишаку
и удаляет его потом.

        Параметры
        -----------
        ctx: commands.Context
            Контекстный объект, используемый для получения информации об этой командной задаче.
        """

        self.task_count += 1

        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            # asyncio.current_task не документирует, что он может повысить время выполнения, но это так.
            # Он распространяется из asyncio.get_running_loop (), так что это происходит, когда не работает цикл.
            # Неясно, является ли это регрессией или преднамеренным изменением, поскольку в 3.6
            # asyncio.task.current_task () только не вернул бы в этом случае.
            current_task = None

        cmdtask = CommandTask(self.task_count, ctx, current_task)

        self.tasks.append(cmdtask)

        try:
            yield cmdtask
        finally:
            if cmdtask in self.tasks:
                self.tasks.remove(cmdtask)
