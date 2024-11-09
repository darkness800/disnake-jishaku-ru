# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import dataclasses
import inspect
import os
import typing

ENABLED_SYMBOLS = ("true", "t", "yes", "y", "on", "1")
DISABLED_SYMBOLS = ("false", "f", "no", "n", "off", "0")


@dataclasses.dataclass
class Flag:
    """
    DataClass, который представляет состояние флага Джишаку.Только для внутреннего использования.
    """

    name: str
    flag_type: type
    default: typing.Callable = None
    override: typing.Any = None

    def resolve(self, flags):
        """
        Установите этот флаг.Только для внутреннего использования.
        """

        # Переопределение ручного, игнорируйте окружающую среду в этом случае
        if self.override is not None:
            return self.override

        # Решить из окружающей среды
        env_value = os.getenv(f"JISHAKU_{self.name}", "").strip()

        if env_value:
            if self.flag_type is bool:
                if env_value.lower() in ENABLED_SYMBOLS:
                    return True
                if env_value.lower() in DISABLED_SYMBOLS:
                    return False
            else:
                return self.flag_type(env_value)

        # Запасной, если не разрешается резольвации от окружающей среды
        if self.default is not None:
            if inspect.isfunction(self.default):
                return self.default(flags)

            return self.default

        return self.flag_type()


class FlagMeta(type):
    """
    Metaclass для флагов.
    Это обрабатывает справедливую оценку флагов, позволяя переопределить их во время исполнения.
    """

    def __new__(cls, name, base, attrs):
        attrs['flag_map'] = {}

        for flag_name, flag_type in attrs['__annotations__'].items():
            attrs['flag_map'][flag_name] = Flag(flag_name, flag_type, attrs.pop(flag_name, None))

        return super(FlagMeta, cls).__new__(cls, name, base, attrs)

    def __getattr__(cls, name: str):
        if hasattr(cls, 'flag_map') and name in cls.flag_map:
            return cls.flag_map[name].resolve(cls)

        return super().__getattribute__(name)

    def __setattr__(cls, name: str, value):
        if name in cls.flag_map:
            flag = cls.flag_map[name]

            if not isinstance(value, flag.flag_type):
                raise ValueError(f"Попытка установить флаг {name} наведите {type(value).__name__} (должен быть {flag.flag_type.__name__})")

            flag.override = value
        else:
            super().__setattr__(name, value)


class Flags(metaclass=FlagMeta):
    """
    Флаги для Джишаку.

    Вы можете переопределить их либо через окружающую среду, например:
        export JISHAKU_HIDE=1
    Или вы можете переопределить их программно:
        jishaku.Flags.HIDE = True
    """

    # Флаг, чтобы указать, что группа командной команды Jishaku должна быть спрятана
    HIDE: bool

    # Флаг, чтобы указать, что режим удержания для Repl должен быть включен по умолчанию
    RETAIN: bool

    # Флаг, чтобы указать, что мета -переменные в Repl не следует префикс с подчеркиванием.
    NO_UNDERSCORE: bool

    # Префикс применения, то есть префикс, который появляется перед встроенными переменными Джишаку в сессиях.
    # Рекомендуется установить это программно.
    SCOPE_PREFIX: str = lambda flags: '' if flags.NO_UNDERSCORE else '_'

    # Флаг, чтобы указать, всегда ли использовать Paginators, а не предварительный просмотр файлов Discord
    FORCE_PAGINATOR: bool

    # Флаг, чтобы указать на многословную ошибку трассировки следует отправлять на канал вызова, а не через прямое сообщение.
    NO_DM_TRACEBACK: bool

    # Флаг, чтобы указать использование Braille J в команде выключения
    USE_BRAILLE_J: bool
