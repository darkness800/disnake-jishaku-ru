# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import ast


class KeywordTransformer(ast.NodeTransformer):
    """
    Этот трансформатор:
    - Преобразует возвращение в значение в урожайность и возврат
    - Превращает обнаженные удаления в условные глобальные всплески
    """

    def visit_FunctionDef(self, node):
        # Не влияйте на определения вложенных функций
        return node

    def visit_AsyncFunctionDef(self, node):
        # Не влияйте на определения вложенных асинхронных функций
        return node

    def visit_ClassDef(self, node):
        # Не влияйте на определения вложенных классов
        return node

    def visit_Return(self, node):
        #Не изменять бесценные возвраты
        if node.value is None:
            return node

        # В противном случае замените возврат на доход и бесценную возврат
        return ast.If(
            test=ast.NameConstant(
                value=True,  # Если правда; ака безусловный, будет оптимизирован
                lineno=node.lineno,
                col_offset=node.col_offset
            ),
            body=[
                # Получить значение, которое будет возвращено
                ast.Expr(
                    value=ast.Yield(
                        value=node.value,
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    ),
                    lineno=node.lineno,
                    col_offset=node.col_offset
                ),
                # вернуть безвредные
                ast.Return(
                    value=None,
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
            ],
            orelse=[],
            lineno=node.lineno,
            col_offset=node.col_offset
        )

    def visit_Delete(self, node):
        """
        Этот преобразователь заменяет голые удаления условными глобальными всплесками.

        Это примерно эквивалентно трансформации:

        .. code:: python

            del foobar

        into:

        .. code:: python

            if 'foobar' in globals():
                globals().pop('foobar')
            else:
                del foobar

        Таким образом, это делает удаление в режиме сохраняемых режимов более или менее, как предполагалось.
        """

        return ast.If(
            test=ast.NameConstant(
                value=True,  # Если правда;ака безусловный, будет оптимизирован
                lineno=node.lineno,
                col_offset=node.col_offset
            ),
            body=[
                ast.If(
                    # if 'x' in globals():
                    test=ast.Compare(
                        # 'x'
                        left=ast.Str(
                            s=target.id,
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        ),
                        ops=[
                            # in
                            ast.In(
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            )
                        ],
                        comparators=[
                            # globals()
                            self.globals_call(node)
                        ],
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    ),
                    body=[
                        ast.Expr(
                            # globals().pop('x')
                            value=ast.Call(
                                # globals().pop
                                func=ast.Attribute(
                                    value=self.globals_call(node),
                                    attr='pop',
                                    ctx=ast.Load(),
                                    lineno=node.lineno,
                                    col_offset=node.col_offset
                                ),
                                args=[
                                    # 'x'
                                    ast.Str(
                                        s=target.id,
                                        lineno=node.lineno,
                                        col_offset=node.col_offset
                                    )
                                ],
                                keywords=[],
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            ),
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        )
                    ],
                    # else:
                    orelse=[
                        # del x
                        ast.Delete(
                            targets=[target],
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        )
                    ],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
                if isinstance(target, ast.Name) else
                ast.Delete(
                    targets=[target],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
                # для каждой цели, которая должна быть удалена, например `del {x}, {y}, {z}`
                for target in node.targets
            ],
            orelse=[],
            lineno=node.lineno,
            col_offset=node.col_offset
        )

    def globals_call(self, node):
        """
        Создает узел AST, который называет Global().
        """

        return ast.Call(
            func=ast.Name(
                id='globals',
                ctx=ast.Load(),
                lineno=node.lineno,
                col_offset=node.col_offset
            ),
            args=[],
            keywords=[],
            lineno=node.lineno,
            col_offset=node.col_offset
        )
