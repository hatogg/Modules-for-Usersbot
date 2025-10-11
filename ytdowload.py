# power by https://t.me/devx44to

from .. import loader, utils
import yt_dlp
import os
import asyncio
from telethon.tl.types import DocumentAttributeAudio

@loader.tds
class YoutubeToMP3(loader.Module):
    """Модуль для конвертации видео с YouTube в MP3 и отправки в чат"""

    strings = {
        "name": "YoutubeToMP3",
        "downloading": "<b>Скачиваю и конвертирую...</b>",
        "no_url": "<b>Укажите URL видео с YouTube</b>",
        "error": "<b>Ошибка:</b> {error}",
    }

    @loader.command()
    async def ytmp3(self, message):
        """<url> - Конвертировать видео с YouTube в MP3 и отправить в чат"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_url"])
            return

        await utils.answer(message, self.strings["downloading"])

        loop = asyncio.get_event_loop()

        def download_audio():
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': '%(title)s.%(ext)s',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(args, download=True)
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + '.mp3'
                return filename, info

        try:
            filename, info = await loop.run_in_executor(None, download_audio)
            duration = int(info.get('duration', 0))
            title = info.get('title', 'Unknown')
            performer = info.get('uploader', 'Unknown')

            await message.client.send_file(
                message.to_id,
                filename,
                attributes=[DocumentAttributeAudio(duration=duration, title=title, performer=performer)],
                reply_to=message.reply_to_msg_id if message.is_reply else None,
                supports_streaming=True,
            )
            os.remove(filename)
            await message.delete()
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(error=str(e)))