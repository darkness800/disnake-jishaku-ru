# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import inspect
import typing


class Scope:
    """
    Класс, который представляет глобальный и локальный объем как для осмотра, так и для творения.

    Многие функции Repl ожидают или возвращают этот класс.

    .. code:: python3

        scope = Scope()  # пустая область прицела

        scope = Scope(globals(), locals())  # Область, имитирующая текущую, реальную область.

        scope = Scope({'a': 3})  # Применение с ранее существовавшим глобальным ключом по объему и пустой локальной областью.
    """

    __slots__ = ('globals', 'locals')

    def __init__(self, globals_: dict = None, locals_: dict = None):
        self.globals: dict = globals_ or {}
        self.locals: dict = locals_ or {}

    def clear_intersection(self, other_dict):
        """
        Очищает местных жителей и глобалов из этой области, где совпадает пара клавишных значений
        с другим_диктом.

        Это позволяет очистить временные переменные, которые могли промыться в это
        Объем.

        Параметры
        -----------
        Другое_Дикт: :class:`dict`
            Словарь, который будет использоваться для определения очистки объема.

            Если ключ из этого дикта соответствует записи в глобальных или местных жителях этой области,
            и значение идентично, оно удаляется из области.

        Возврат
        -------
        Объем
            Обновленная область (я).
        """

        for key, value in other_dict.items():
            if key in self.globals and self.globals[key] is value:
                del self.globals[key]
            if key in self.locals and self.locals[key] is value:
                del self.locals[key]

        return self

    def update(self, other):
        """
        Обновляет эту область с помощью содержания другой области.

        Parameters
        ---------
        other: :class:`Scope`
            Область наложения на это.
        Возврат
        -------
        Объем
            Обновленная область (я).
        """

        self.globals.update(other.globals)
        self.locals.update(other.locals)
        return self

    def update_globals(self, other: dict):
        """
        Обновляют глобалы этой области диктом.

        Параметры
        -----------
        другой: :class:`dict`
            Словарь, который должен быть объединен в эту область.

        Возврат
        -------
        Объем
            Обновленная область (я).
        """

        self.globals.update(other)
        return self

    def update_locals(self, other: dict):
        """
        Обновляет местных жителей этой области диктом.

        Параметры
        -----------
        другой: :class:`dict`
            Словарь, который должен быть объединен в эту область.

        Возврат
        -------
        Объем
            Обновленная область (я).
        """

        self.locals.update(other)
        return self


def get_parent_scope_from_var(name, global_ok=False, skip_frames=0) -> typing.Optional[Scope]:
    """
    Отражает стек кадров в поисках кадра, содержащей заданное имя переменной.

    Возврат
    --------
    Необязательно [Scope]
        Соответствующий: класс: `recope` или нет
    """

    stack = inspect.stack()
    try:
        for frame_info in stack[skip_frames + 1:]:
            frame = None

            try:
                frame = frame_info.frame

                if name in frame.f_locals or (global_ok and name in frame.f_globals):
                    return Scope(globals_=frame.f_globals, locals_=frame.f_locals)
            finally:
                del frame
    finally:
        del stack

    return None


def get_parent_var(name, global_ok=False, default=None, skip_frames=0):
    """
    Непосредственно получает переменную от родительской кадры.

    Возврат
    --------
    Любой
        Содержание переменной, найденной данным именем, или нет.
    """

    scope = get_parent_scope_from_var(name, global_ok=global_ok, skip_frames=skip_frames + 1)

    if not scope:
        return default

    if name in scope.locals:
        return scope.locals.get(name, default)

    return scope.globals.get(name, default)
