# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import typing

import disnake
from disnake.ext import commands

from jishaku.features.baseclass import Feature


class GuildFeature(Feature):
    """
    Функция, содержащая команды, связанные с гильдией
    """

    @staticmethod
    def apply_overwrites(permissions: dict, allow: int, deny: int, name: str):
        """
        Применяется перезаписывается к словарю разрешений (см. Permtrace),
на основе допустимой и отрицательной маски.
        """

        allow: disnake.Permissions = disnake.Permissions(allow)
        deny: disnake.Permissions = disnake.Permissions(deny)

        # Отрицает первым ..
        for key, value in dict(deny).items():
            # Убедитесь, что в этом отрицается, и это еще не опровергнуто
            # (Мы хотим показать причину отрицания самого низкого уровня)
            if value and permissions[key][0]:
                permissions[key] = (False, f"Это перезапись {name} канала")

        # Затем позволяет
        for key, value in dict(allow).items():
            # Убедитесь, что это разрешено, и это еще не разрешено
            # (Мы хотим показать причину пособия на самом низком уровне)
            if value and not permissions[key][0]:
                permissions[key] = (True, f"Это перезапись {name} канала")

    @staticmethod
    def chunks(array: list, chunk_size: int):
        """
        Кусочки списка в куски данного размера.
        Вероятно, если честно, должно быть в Utils.
        """
        for i in range(0, len(array), chunk_size):
            yield array[i:i + chunk_size]

    @Feature.Command(parent="jsk", name="permtrace")
    async def jsk_permtrace(
        self, ctx: commands.Context,
        channel: typing.Union[disnake.TextChannel, disnake.VoiceChannel],
        *targets: typing.Union[disnake.Member, disnake.Role]
    ):
        """
        Рассчитывает источник предоставленных или отклоненных разрешений.

        Это принимает канал и либо участник, либо список ролей.
        Он рассчитывает разрешения так же, как и Discord, отслеживая источник.
        """

        member_ids = {target.id: target for target in targets if isinstance(target, disnake.Member)}
        roles = []

        for target in targets:
            if isinstance(target, disnake.Member):
                roles.extend(list(target.roles))
            else:
                roles.append(target)

        # Удалить дубликаты
        roles = list(set(roles))

        # Словарь для хранения текущего состояния разрешения и разума
        # Магазины <имя перми>: (<perm разрешено>, <sonse>)
        permissions: typing.Dict[str, typing.Tuple[bool, str]] = {}

        if member_ids and channel.guild.owner_id in member_ids:
            # Владелец, имеет все пважицы
            for key in dict(disnake.Permissions.all()).keys():
                permissions[key] = (True, f"{channel.guild.owner.mention} Владеет сервером")
        else:
            # В противном случае, либо не участник, либо не владелец гильдии, рассчитывайте вручную вручную
            is_administrator = False

            # Сначала обращаться
            for key, value in dict(channel.guild.default_role.permissions).items():
                permissions[key] = (value, "Это разрешение для всего сервера.")

            for role in roles:
                for key, value in dict(role.permissions).items():
                    # Роли могут только разрешать разрешения
                    # Отказ в разрешении ничего не делает, если более низкая роль позволяет это
                    if value and not permissions[key][0]:
                        permissions[key] = (value, f"это разрешение для всего сервера {role.name}")

                # Затем управляемость администратора
                if role.permissions.administrator:
                    is_administrator = True

                    for key in dict(disnake.Permissions.all()).keys():
                        if not permissions[key][0]:
                            permissions[key] = (True, f"это разрешение предоставляется администратором на уровне всего сервера {role.name}")

            # Если администратор был предоставлен, нет причин даже выполнять разрешения на каналы
            if not is_administrator:
                # Теперь разрешения на уровне канала

                # Особый случай для @EveryOne
                try:
                    maybe_everyone = channel._overwrites[0]
                    if maybe_everyone.id == channel.guild.default_role.id:
                        self.apply_overwrites(permissions, allow=maybe_everyone.allow, deny=maybe_everyone.deny, name="@everyone")
                        remaining_overwrites = channel._overwrites[1:]
                    else:
                        remaining_overwrites = channel._overwrites
                except IndexError:
                    remaining_overwrites = channel._overwrites

                role_lookup = {r.id: r for r in roles}

                # Отрицания применяются ранее, всегда
                # Ручка отрицает
                for overwrite in remaining_overwrites:
                    if overwrite.type == 'role' and overwrite.id in role_lookup:
                        self.apply_overwrites(permissions, allow=0, deny=overwrite.deny, name=role_lookup[overwrite.id].name)

                # Ручка разрешает
                for overwrite in remaining_overwrites:
                    if overwrite.type == 'role' and overwrite.id in role_lookup:
                        self.apply_overwrites(permissions, allow=overwrite.allow, deny=0, name=role_lookup[overwrite.id].name)

                if member_ids:
                    # Обрабатывать специфичные для члена перезаписывания
                    for overwrite in remaining_overwrites:
                        if overwrite.type == 'member' and overwrite.id in member_ids:
                            self.apply_overwrites(permissions, allow=overwrite.allow, deny=overwrite.deny, name=f"{member_ids[overwrite.id].mention}")
                            break

        # Конструкция встроена
        description = f"Это расчет разрешений для следующих целевых объектов в {channel.mention}:\n"
        description += "\n".join(f"- {target.mention}" for target in targets)

        description += (
            "\nПожалуйста, обратите внимание, что указанные причины являются ** наиболее фундаментальной ** причиной, по которой разрешение является таким, какое оно есть. "
            "Могут быть и другие причины, по которым эти разрешения сохраняются, даже если вы измените отображаемые данные."
        )

        embed = disnake.Embed(color=0x00FF00, description=description)

        allows = []
        denies = []

        for key, value in permissions.items():
            if value[0]:
                allows.append(f"\N{WHITE HEAVY CHECK MARK} {key} (потому что {value[1]})")
            else:
                denies.append(f"\N{CROSS MARK} {key} (потому что {value[1]})")

        for chunk in self.chunks(sorted(allows) + sorted(denies), 8):
            embed.add_field(name="...", value="\n".join(chunk), inline=False)

        await ctx.send(embed=embed)
