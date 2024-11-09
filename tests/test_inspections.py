# -*- coding: utf-8 -*-

"""
jishaku.inspections test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, Смотрите лицензию для более подробной информации.

"""

import collections  # for __iadd__ test

import disnake
import pytest
from utils import run_async

from jishaku.repl.inspections import all_inspections


@pytest.mark.parametrize(
    "target",
    [
        4,
        disnake.Client,  # Подклассы типа крышки
        tuple,  # Покрыть усечение многократного класса
        [False, 1, "2", 3.0],  # Покрыть типы контента
        collections.Counter,  # Накрыть операторов на место
        run_async  # Покрыть текущие проверки режиссера
    ]
)
def test_object_inspection(target):
    for _, _ in all_inspections(target):
        pass
