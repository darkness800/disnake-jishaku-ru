# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import ast
import asyncio
import inspect
import linecache

import import_expression

from jishaku.functools import AsyncSender
from jishaku.repl.scope import Scope
from jishaku.repl.walkers import KeywordTransformer

CORO_CODE = """
async def _repl_coroutine({{0}}):
    import asyncio
    from importlib import import_module as {0}

    import aiohttp
    import disnake
    from disnake.ext import commands

    try:
        import jishaku
    except ImportError:
        jishaku = None  # keep working even if in panic recovery mode

    try:
        pass
    finally:
        _async_executor.scope.globals.update(locals())
""".format(import_expression.constants.IMPORTER)


def wrap_code(code: str, args: str = '') -> ast.Module:
    """
    Компилируют код Python в асинхронную функцию или генератор,
    и автоматически добавляет возврат, если корпус функции является единственной оценкой.
    Также добавляет встроенную поддержку выражения импорта.
    """

    user_code = import_expression.parse(code, mode='exec')
    mod = import_expression.parse(CORO_CODE.format(args), mode='exec')

    definition = mod.body[-1]  # async def ...:
    assert isinstance(definition, ast.AsyncFunctionDef)

    try_block = definition.body[-1]  # try:
    assert isinstance(try_block, ast.Try)

    try_block.body.extend(user_code.body)

    ast.fix_missing_locations(mod)

    KeywordTransformer().generic_visit(try_block)

    last_expr = try_block.body[-1]

    # Если последняя часть не является выражением, игнорируйте это
    if not isinstance(last_expr, ast.Expr):
        return mod

    # Если последнее выражение не является урожайностью
    if not isinstance(last_expr.value, ast.Yield):
        # скопировать значение выражения в выход
        yield_stmt = ast.Yield(last_expr.value)
        ast.copy_location(yield_stmt, last_expr)
        # Поместите урожай в собственное выражение
        yield_expr = ast.Expr(yield_stmt)
        ast.copy_location(yield_expr, last_expr)

        # Поместите урожай, где было первоначальное выражение
        try_block.body[-1] = yield_expr

    return mod


class AsyncCodeExecutor:
    """
    Выполняет/оценивает код Python внутри асинхронной функции или генератора.

    Пример
    -------

    .. code:: python3

        total = 0

        # prints 1, 2 and 3
        async for x in AsyncCodeExecutor('yield 1; yield 2; yield 3'):
            total += x
            print(x)

        # prints 6
        print(total)
    """

    __slots__ = ('args', 'arg_names', 'code', 'loop', 'scope', 'source')

    def __init__(self, code: str, scope: Scope = None, arg_dict: dict = None, loop: asyncio.BaseEventLoop = None):
        self.args = [self]
        self.arg_names = ['_async_executor']

        if arg_dict:
            for key, value in arg_dict.items():
                self.arg_names.append(key)
                self.args.append(value)

        self.source = code
        self.code = wrap_code(code, args=', '.join(self.arg_names))
        self.scope = scope or Scope()
        self.loop = loop or asyncio.get_event_loop()

    def __aiter__(self):
        exec(compile(self.code, '<repl>', 'exec'), self.scope.globals, self.scope.locals)
        func_def = self.scope.locals.get('_repl_coroutine') or self.scope.globals['_repl_coroutine']

        return self.traverse(func_def)

    async def traverse(self, func):
        """
        Пересекает асинхронную функцию или генератор, давая каждый результат.

        Эта функция частная.Класс должен использоваться в качестве итератора вместо использования этого метода.
        """

        try:
            if inspect.isasyncgenfunction(func):
                async for send, result in AsyncSender(func(*self.args)):
                    send((yield result))
            else:
                yield await func(*self.args)
        except Exception:
            # Ложно заполняем линейный линий, чтобы линия реплики появилась в Tracebacks
            linecache.cache['<repl>'] = (
                len(self.source),  # Длина источника
                None,  # Время изменено (ни один обходной
                [line + '\n' for line in self.source.splitlines()],  # Список строки
                '<repl>'  # «Истинное» имя файла
            )

            raise
