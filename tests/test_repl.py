# -*- coding: utf-8 -*-

"""
jishaku.repl internal test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, Смотрите лицензию для более подробной информации.

"""

import inspect
import random
import sys

import pytest
from utils import mock_ctx, run_async

from jishaku.repl import AsyncCodeExecutor, Scope, get_parent_var, get_var_dict_from_ctx


def upper_method():
    return get_parent_var('hidden_variable')


async def add_numbers(one, two):
    return one + two


@pytest.fixture(scope="module")
def scope():
    return Scope(
        {
            "add_numbers": add_numbers,
            "placement": 81
        },
        {
            "placement_local": 18
        }
    )


def test_scope_var():
    for _ in range(10):
        hidden_variable = random.randint(0, 1000000)
        test = upper_method()

        assert hidden_variable == test

        del hidden_variable

        test = upper_method()
        assert test is None

        assert get_parent_var('pytest', global_ok=True) == pytest


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ('3 + 4', [7]),
        ('return 3 + 9', [12]),
        ('yield 30; yield 40', [30, 40]),
        ('yield 60; 70', [60, 70]),
        ('90; 100', [100]),
        pytest.param(
            'eval("""\n77 + 22\n""")', [99],
            marks=pytest.mark.skipif(
                sys.version_info < (3, 7),
                reason="3.6 Требуется функция брони, поэтому не может справиться с отступами"
            )
        )
    ]
)
@run_async
async def test_executor_basic(code, expected):
    return_data = []
    async for result in AsyncCodeExecutor(code):
        return_data.append(result)

    assert len(return_data) == len(expected)
    for a, b in zip(return_data, expected):
        assert a == b


@pytest.mark.parametrize(
    ("code", "expected", "arg_dict"),
    [
        ("", [None], None),
        ("# this is a comment", [None], None),
        ("b = 12 + 82", [None], None),
        ("b", [94], None),
        ("c = placement + 7; c", [88], None),
        (
            "_cool_data + _not_so_cool",
            [445],
            {
                '_cool_data': 45,
                '_not_so_cool': 400
            }
        ),
        pytest.param(
            "_cool_data", [45], None,
            marks=pytest.mark.xfail(raises=NameError, strict=True)
        ),
        ("await add_numbers(10, 12)", [22], None)
    ]
)
@run_async
async def test_executor_advanced(code, expected, arg_dict, scope):

    return_data = []
    async for result in AsyncCodeExecutor(code, scope, arg_dict=arg_dict):
        return_data.append(result)

    assert len(return_data) == len(expected)
    for a, b in zip(return_data, expected):
        assert a == b

    if arg_dict:
        scope.clear_intersection(arg_dict)


@run_async
async def test_scope_copy(scope):
    scope2 = Scope()
    scope2.update(scope)

    assert scope.globals == scope2.globals, "Проверка сфера областей глобалов скопирована"
    assert scope.locals == scope2.locals, "Проверка прицела местных жителей скопирована"

    insert_dict = {'e': 7}
    scope.update_locals(insert_dict)

    assert 'e' in scope.locals, "Проверка обновления местных жителей"
    assert 'e' not in scope2.locals, "Проверка областей клона. Местные жители не обновлены"

    scope.clear_intersection(insert_dict)

    assert 'e' not in scope.locals, "Проверка пересечения местных жителей очищено"

    scope.update_globals(insert_dict)

    assert 'e' in scope.globals, "Проверка обновленных глобальных областей"
    assert 'e' not in scope2.globals, "Проверка областей клонов Globals не обновлена"

    scope.clear_intersection(insert_dict)

    assert 'e' not in scope.globals, "Проверка перекрестка Globals очищено"


@run_async
async def test_executor_builtins(scope):
    codeblock = inspect.cleandoc("""
    def ensure_builtins():
        return ValueError
    """)

    return_data = []
    async for result in AsyncCodeExecutor(codeblock, scope):
        return_data.append(result)

    assert len(return_data) == 1
    assert return_data[0] is None

    assert 'ensure_builtins' in scope.globals, "Проверка функции остается определенной"
    assert callable(scope.globals['ensure_builtins']), "Проверка определенной"
    assert scope.globals['ensure_builtins']() == ValueError, "Проверка определенного возврата согласованной"


def test_var_dict(scope):
    with mock_ctx() as ctx:
        scope.update_globals(get_var_dict_from_ctx(ctx))

        assert scope.globals['_ctx'] is ctx
        assert scope.globals['_bot'] is ctx.bot
        assert scope.globals['_message'] is ctx.message
