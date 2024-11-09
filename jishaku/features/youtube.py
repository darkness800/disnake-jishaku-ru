# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# [!] Требует обновления

import disnake
import youtube_dl
from disnake.ext import commands

from jishaku.features.baseclass import Feature
from jishaku.features.voice import VoiceFeature

BASIC_OPTS = {
    'format': 'webm[abr>0]/bestaudio/best',
    'prefer_ffmpeg': True,
    'quiet': True
}


class BasicYouTubeDLSource(disnake.FFmpegPCMAudio):
    """
    Основной аудио источник для URL-адреса YouTube_DL.
    """

    def __init__(self, url, download: bool = False):
        ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)
        info = ytdl.extract_info(url, download=download)
        super().__init__(info['url'])


class YouTubeFeature(Feature):
    """
    Функция, содержащая команду YouTube-DL
    """

    @Feature.Command(parent="jsk_voice", name="youtube_dl", aliases=["youtubedl", "ytdl", "yt"])
    async def jsk_vc_youtube_dl(self, ctx: commands.Context, *, url: str):
        """
        Играет звук из YouTube_DL-совместимых источников.
        """

        if await VoiceFeature.connected_check(ctx):
            return

        if not youtube_dl:
            return await ctx.send("youtube_dl не установлен.")

        voice = ctx.guild.voice_client

        if voice.is_playing():
            voice.stop()

        # Удалить встроенные маскировщики, если они присутствуют
        url = url.lstrip("<").rstrip(">")

        voice.play(disnake.PCMVolumeTransformer(BasicYouTubeDLSource(url)))
        await ctx.send(f"Играет в {voice.channel.name}.")
