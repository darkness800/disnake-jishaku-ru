# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from disnake.ext import commands

from jishaku.flags import Flags
from jishaku.hljs import get_language, guess_file_traits
from jishaku.shim.paginator_base import EmojiSettings

from jishaku.shim.paginator_200 import PaginatorEmbedInterface, PaginatorInterface

__all__ = ('EmojiSettings', 'PaginatorInterface', 'PaginatorEmbedInterface',
           'WrappedPaginator', 'FilePaginator', 'use_file_check')


class WrappedPaginator(commands.Paginator):
    """
    Плаватор, который позволяет автоматическому обертыванию линий, если они не подходят.

    Это полезно при страничном непредсказуемом выходе,
    так как это позволяет расщеплять линии на большие куски данных.

    Разделители приоритеты в порядке их кортежа.

    Параметры
    -----------
    обернуть: tuple
        Круп с обертывающими делимитерами.
    Включить: bool
        Должно ли включать разделитель в начале новой оберщенной линии.
    принудительнаяОбертка: bool
        Если это правда, линии будут разделены на их максимальные точки
        с любым предоставленным разделителем.
    """

    def __init__(self, *args, wrap_on=('\n', ' '), include_wrapped=True, force_wrap=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.wrap_on = wrap_on
        self.include_wrapped = include_wrapped
        self.force_wrap = force_wrap

    def add_line(self, line='', *, empty=False):
        true_max_size = self.max_size - self._prefix_len - self._suffix_len - 2
        original_length = len(line)

        while len(line) > true_max_size:
            search_string = line[0:true_max_size - 1]
            wrapped = False

            for delimiter in self.wrap_on:
                position = search_string.rfind(delimiter)

                if position > 0:
                    super().add_line(line[0:position], empty=empty)
                    wrapped = True

                    if self.include_wrapped:
                        line = line[position:]
                    else:
                        line = line[position + len(delimiter):]

                    break

            if not wrapped:
                if self.force_wrap:
                    super().add_line(line[0:true_max_size - 1])
                    line = line[true_max_size - 1:]
                else:
                    raise ValueError(
                        f"Line of length {original_length} had sequence of {len(line)} characters"
                        f" (max is {true_max_size}) that WrappedPaginator could not wrap with"
                        f" delimiters: {self.wrap_on}"
                    )

        super().add_line(line, empty=empty)


class FilePaginator(commands.Paginator):
    """
    Парень из кодовых блоков с синтаксисом, прочитанным из файла, подобного файлу.

    Parameters
    -----------
    fp
        Файл, подобный (реализации ``fp.read``) Чтобы прочитать данные для этого пагинтора от.
    линейный промежуток: Optional[Tuple[int, int]]
        LineSpan для чтения из файла.Если нет, читает весь файл.
    language_hints: Tuple[str]
        Кортеж из струн, который может намекнуть на язык этого файла.
        Это может включать в себя имена файлов, типов MIME или шебанга.
        Шебанг, присутствующий в фактическом файле, всегда будет приоритетным из -за этого.
    """

    def __init__(self, fp, line_span=None, language_hints=(), **kwargs):
        language = ''

        for hint in language_hints:
            language = get_language(hint)

            if language:
                break

        if not language:
            try:
                language = get_language(fp.name)
            except AttributeError:
                pass

        content, _, file_language = guess_file_traits(fp.read())

        language = file_language or language
        lines = content.split('\n')

        super().__init__(prefix=f'```{language}', suffix='```', **kwargs)

        if line_span:
            line_span = sorted(line_span)

            if min(line_span) < 1 or max(line_span) > len(lines):
                raise ValueError("Linespan goes out of bounds.")

            lines = lines[line_span[0] - 1:line_span[1]]

        for line in lines:
            self.add_line(line)


class WrappedFilePaginator(FilePaginator, WrappedPaginator):
    """
    Комбинация FilePaginator и обернутого пагинтора.
    Другими словами, FilePaginator, который поддерживает обертывание линии.
    """


def use_file_check(ctx: commands.Context, size: int) -> bool:
    """
    Проверка, чтобы определить, является ли загрузка файла и полагаться на предварительный просмотр файла Discord, приемлемо по сравнению с PaginatorInterface.
    """

    return all([
        size < 50_000,  # Проверьте, что текст находится под точкой отсечения раздора;
        not Flags.FORCE_PAGINATOR,  # Проверьте, что пользователь явно не отключил это;
        (not ctx.author.is_on_mobile() if ctx.guild and ctx.bot.intents.presences else True)  # Убедитесь, что пользователь не на мобильном
    ])
