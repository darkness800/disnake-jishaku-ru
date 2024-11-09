# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import ast
import dis

import import_expression

from jishaku.repl.scope import Scope

CORO_CODE = """
import asyncio

import disnake
from disnake.ext import commands
from importlib import import_module as {0}

import jishaku

async def _repl_coroutine({{0}}):
    pass
""".format(import_expression.constants.IMPORTER)


def wrap_code(code: str, args: str = '') -> ast.Module:
    """
    Обертывает код для разобравания.

    Это похоже на функцию с эквивалентом jishaku.repl.compilation,
    но из -за различной структуры, необходимой для чистых разборных,
    Он реализован отдельно здесь.
    """

    user_code = import_expression.parse(code, mode='exec')
    mod = import_expression.parse(CORO_CODE.format(args), mode='exec')

    definition = mod.body[-1]  # async def ...:
    assert isinstance(definition, ast.AsyncFunctionDef)

    # Исправить код пользователя непосредственно в функцию
    definition.body = user_code.body

    ast.fix_missing_locations(mod)

    # Мы не используем здесь трансформатор ключевых слов, поскольку он может привести к вводящей в заблуждение разборке.

    is_asyncgen = any(isinstance(node, ast.Yield) for node in ast.walk(definition))
    last_expr = definition.body[-1]

    # Если последняя часть не является выражением, игнорируйте это
    if not isinstance(last_expr, ast.Expr):
        return mod

    # Если это не генератор, а последнее выражение не является возвратом
    if not is_asyncgen and not isinstance(last_expr.value, ast.Return):
        # скопировать значение выражения в возврат
        return_stmt = ast.Return(last_expr.value)
        ast.copy_location(return_stmt, last_expr)

        # Поместите возвращение, где было первоначальное выражение
        definition.body[-1] = return_stmt

    return mod


def disassemble(code: str, scope: Scope = None, arg_dict: dict = None):
    """
    Разборки асинхронный код в инструкции по байт-коду в стиле dis.dis.
    """

    # Похоже на AsyncCodeExecutor.__init__
    arg_names = list(arg_dict.keys()) if arg_dict else []

    scope = scope or Scope()

    wrapped = wrap_code(code, args=', '.join(arg_names))
    exec(compile(wrapped, '<repl>', 'exec'), scope.globals, scope.locals)

    func_def = scope.locals.get('_repl_coroutine') or scope.globals['_repl_coroutine']

    co = func_def.__code__

    for instruction in dis._get_instructions_bytes(
        co.co_code, co.co_varnames, co.co_names, co.co_consts,
        co.co_cellvars + co.co_freevars, dict(dis.findlinestarts(co)),
        line_offset=0
    ):
        if instruction.starts_line is not None and instruction.offset > 0:
            yield ''

        yield instruction._disassemble(
            4, False, 4
        )
