# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import collections

__all__ = ('Codeblock', 'codeblock_converter')

Codeblock = collections.namedtuple('Codeblock', 'language content')


def codeblock_converter(argument):
    """
    Преобразователь, который лишает отметку кода, если он существует.

    Возвращает название (language, content).

    :attr:`Codeblock.language` это пустая строка, если с этим кодовым блоком не было дано.
    Это ``None`` Если ввод не был полным блоком кода.
    """
    if not argument.startswith('`'):
        return Codeblock(None, argument)

    # Держите небольшой буфер из последних очагов, которые мы видели
    last = collections.deque(maxlen=3)
    backticks = 0
    in_language = False
    in_code = False
    language = []
    code = []

    for char in argument:
        if char == '`' and not in_code and not in_language:
            backticks += 1  # Чтобы помочь отслеживать закрытие бэктиков
        if last and last[-1] == '`' and char != '`' or in_code and ''.join(last) != '`' * backticks:
            in_code = True
            code.append(char)
        if char == '\n':  # \ n делиминации язык и код
            in_language = False
            in_code = True
        # Мы еще не видим новую линию, но мы также прошли открытие ```
        elif ''.join(last) == '`' * 3 and char != '`':
            in_language = True
            language.append(char)
        elif in_language:  # Мы на языке после первого небакового персонажа
            if char != '\n':
                language.append(char)

        last.append(char)

    if not code and not language:
        code[:] = last

    return Codeblock(''.join(language), ''.join(code[len(language):-backticks]))
