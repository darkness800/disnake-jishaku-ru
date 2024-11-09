# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import typing

import disnake
import disnake.opus
import disnake.voice_client
from disnake.ext import commands

from jishaku.features.baseclass import Feature


class VoiceFeature(Feature):
    """
    Функция, содержащая основные команды, связанные с голосом
    """

    @staticmethod
    async def voice_check(ctx: commands.Context):
        """
        Проверьте, доступен ли VC в этом боте.
        """

        if not disnake.voice_client.has_nacl:
            return await ctx.send("Голос не может быть использован, так как PyNaCl не загружен.")

        if not disnake.opus.is_loaded():
            if hasattr(disnake.opus, '_load_default'):
                if not disnake.opus._load_default():
                    return await ctx.send(
                        "Невозможно использовать Voice, поскольку libopus не загружен, а попытка загрузить значение по умолчанию завершилась неудачей."
                    )
            else:
                return await ctx.send("Голос не может быть использован, так как libopus не загружен.")

    @staticmethod
    async def connected_check(ctx: commands.Context):
        """
        Проверьте, связаны ли мы с VC в этой гильдии.
        """

        voice = ctx.guild.voice_client

        if not voice or not voice.is_connected():
            return await ctx.send("Не подключен к голосовому каналу в этой гильдии. ")

    @staticmethod
    async def playing_check(ctx: commands.Context):
        """
        Проверяет, играем ли мы аудио в VC в этой гильдии.

        Это удваивается как проверка соединения.
        """

        check = await VoiceFeature.connected_check(ctx)
        if check:
            return check

        if not ctx.guild.voice_client.is_playing():
            return await ctx.send("Голосовой клиент в этой гильдии ни во что не играет.")

    @Feature.Command(parent="jsk", name="voice", aliases=["vc"],
                     invoke_without_command=True, ignore_extra=False)
    async def jsk_voice(self, ctx: commands.Context):
        """
        Связанные с голосом команды.

        Если призван без подкоманда, передает текущее состояние голоса.
        """

        if await self.voice_check(ctx):
            return

        # Дайте информацию о текущем голосовом клиенте, если есть один
        voice = ctx.guild.voice_client

        if not voice or not voice.is_connected():
            return await ctx.send("Не подключен.")

        await ctx.send(f"Подключен к {voice.channel.name}, "
                       f"{'остановлен' if voice.is_paused() else 'играет' if voice.is_playing() else 'праздный'}.")

    @Feature.Command(parent="jsk_voice", name="join", aliases=["connect"])
    async def jsk_vc_join(self, ctx: commands.Context, *,
                          destination: typing.Union[disnake.VoiceChannel, disnake.Member] = None):
        """
        Соединяет голосовой канал или перемещается к нему, если уже подключен.

        Прохождение голосового канала использует этот голосовой канал.
        Прохождение участника будет использовать текущий голосовой канал этого участника.
        Передача ничего не будет использовать голосовой канал автора.
        """

        if await self.voice_check(ctx):
            return

        destination = destination or ctx.author

        if isinstance(destination, disnake.Member):
            if destination.voice and destination.voice.channel:
                destination = destination.voice.channel
            else:
                return await ctx.send("У участника нет голосового канала.")

        voice = ctx.guild.voice_client

        if voice:
            await voice.move_to(destination)
        else:
            await destination.connect(reconnect=True)

        await ctx.send(f"Подключен к {destination.name}.")

    @Feature.Command(parent="jsk_voice", name="disconnect", aliases=["dc"])
    async def jsk_vc_disconnect(self, ctx: commands.Context):
        """
        Отключается от голосового канала в этой гильдии, если он есть.
        """

        if await self.connected_check(ctx):
            return

        voice = ctx.guild.voice_client

        await voice.disconnect()
        await ctx.send(f"Отключен от {voice.channel.name}.")

    @Feature.Command(parent="jsk_voice", name="stop")
    async def jsk_vc_stop(self, ctx: commands.Context):
        """
        Прекращает запуск аудио источника, если есть.
        """

        if await self.playing_check(ctx):
            return

        voice = ctx.guild.voice_client

        voice.stop()
        await ctx.send(f"Прекратилось воспроизведение звука в {voice.channel.name}.")

    @Feature.Command(parent="jsk_voice", name="pause")
    async def jsk_vc_pause(self, ctx: commands.Context):
        """
        Паузу используется источник аудио, если он есть.
        """

        if await self.playing_check(ctx):
            return

        voice = ctx.guild.voice_client

        if voice.is_paused():
            return await ctx.send("Звук уже поставлен на паузу.")

        voice.pause()
        await ctx.send(f"Приостановлено воспроизведение звука в {voice.channel.name}.")

    @Feature.Command(parent="jsk_voice", name="resume")
    async def jsk_vc_resume(self, ctx: commands.Context):
        """
        Возобновляет работающий аудио источник, если он есть.
        """

        if await self.playing_check(ctx):
            return

        voice = ctx.guild.voice_client

        if not voice.is_paused():
            return await ctx.send("Звук не на паузе.")

        voice.resume()
        await ctx.send(f"Возобновлено воспроизведение звука в {voice.channel.name}.")

    @Feature.Command(parent="jsk_voice", name="volume")
    async def jsk_vc_volume(self, ctx: commands.Context, *, percentage: float):
        """
        Регулирует объем аудио источника, если он поддерживается.
        """

        if await self.playing_check(ctx):
            return

        volume = max(0.0, min(1.0, percentage / 100))

        source = ctx.guild.voice_client.source

        if not isinstance(source, disnake.PCMVolumeTransformer):
            return await ctx.send("Этот источник не поддерживает регулировку громкости или "
                                  "интерфейс для этого не доступен.")

        source.volume = volume

        await ctx.send(f"Громкость установлена на {volume * 100:.2f}%")

    @Feature.Command(parent="jsk_voice", name="play", aliases=["play_local"])
    async def jsk_vc_play(self, ctx: commands.Context, *, uri: str):
        """
        Играет аудио напрямую из URI.

        Может быть либо локальный файл, либо аудио-ресурс в Интернете.
        """

        if await self.connected_check(ctx):
            return

        voice = ctx.guild.voice_client

        if voice.is_playing():
            voice.stop()

        # Удалить встроенные маскировщики, если они присутствуют
        uri = uri.lstrip("<").rstrip(">")

        voice.play(disnake.PCMVolumeTransformer(disnake.FFmpegPCMAudio(uri)))
        await ctx.send(f"Играет в {voice.channel.name}.")
