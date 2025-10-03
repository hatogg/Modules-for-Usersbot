# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Dict, Tuple

from hikkatl import events
from hikkatl.errors import FloodWaitError, UsernameNotOccupiedError
from hikkatl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class LyMusicSearch(loader.Module):
    """Search music via @lytubebot. Usage: .music <song query>"""
    strings = {
        "name": "LyMusicSearch",
        "no_args": "❌ Вкажіть назву пісні.",
        "searching": "🔍 Пошук...",
        "error": "❌ Помилка: {}",
        "no_response": "❌ Немає відповіді від @lytubebot.",
        "bot_unavailable": "❌ @lytubebot недоступний."
    }

    def __init__(self):
        self.pending_queries: Dict[int, Tuple[int, Message]] = {}
        self.bot_username = "lytubebot"
        self.timeout = 30.0

    async def client_ready(self, client, db):
        self.client = client

    async def _send_query(self, bot_id: int, query: str) -> Message:
        try:
            return await self.client.send_message(bot_id, query)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            return None
        except Exception as e:
            logger.error(f"Помилка запиту: {e}")
            return None

    @loader.command()
    async def music(self, message: Message):
        """Пошук музики через @lytubebot. Аргументи: <запит>"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings("no_args"))

        await utils.answer(message, self.strings("searching"))
        try:
            bot = await self.client.get_entity(self.bot_username)
        except UsernameNotOccupiedError:
            return await utils.answer(message, self.strings("bot_unavailable"))

        sent_msg = await self._send_query(bot.id, args)
        if not sent_msg:
            return await utils.answer(message, self.strings("error").format("Не вдалося надіслати запит"))

        self.pending_queries[sent_msg.id] = (message.chat_id, message.id)
        try:
            response = await self.client.wait_event(
                events.NewMessage(chats=bot.id, from_users=bot.id, incoming=True, func=lambda m: m.id > sent_msg.id),
                timeout=self.timeout
            )
            if response:
                await self.client.forward_messages(message.chat_id, response)
            else:
                await utils.answer(message, self.strings("no_response"))
        except asyncio.TimeoutError:
            await utils.answer(message, self.strings("no_response"))
        except Exception as e:
            logger.exception(f"Помилка: {e}")
            await utils.answer(message, self.strings("error").format(str(e)))
        finally:
            self.pending_queries.pop(sent_msg.id, None)
            try:
                await sent_msg.delete()
            except Exception:
                pass

    @loader.command()
    async def musichelp(self, message: Message):
        """Довідка"""
        await utils.answer(message, """
🆘 **Використання:** `.music <пісня>`
Шукає музику через @lytubebot. Спочатку надішліть /start боту @lytubebot.
        """)