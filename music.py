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
    """Search music via @lytubebot. Usage: .music <song query> or inline query"""
    strings = {
        "name": "LyMusicSearch",
        "no_args": "❌ Provide a song name.",
        "searching": "🔍 Searching...",
        "error": "❌ Error: {}",
        "no_response": "❌ No response from @lytubebot.",
        "bot_unavailable": "❌ @lytubebot unavailable."
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
            logger.error(f"Query error: {e}")
            return None

    @loader.command()
    async def music(self, message: Message):
        """Search music with @lytubebot. Args: <song query>"""
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
            return await utils.answer(message, self.strings("error").format("Failed to send query"))

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
            logger.exception(f"Error: {e}")
            await utils.answer(message, self.strings("error").format(str(e)))
        finally:
            self.pending_queries.pop(sent_msg.id, None)
            try:
                await sent_msg.delete()
            except Exception:
                pass

    @loader.command()
    async def musichelp(self, message: Message):
        """Show help"""
        await utils.answer(message, """
🆘 **Usage:**
• Command: `.music <song>`
• Inline: `@<your_bot> music <song>` (if inline enabled)
Searches via @lytubebot. Start chat with it first (/start).
        """)

    @loader.inline
    async def music_inline(self, query: str, message: Message):
        """Inline music search. Args: <song query>"""
        if not query:
            return await self.inline.query_answer(message, self.strings("no_args"))

        try:
            bot = await self.client.get_entity(self.bot_username)
            sent_msg = await self._send_query(bot.id, query)
            if not sent_msg:
                return await self.inline.query_answer(message, self.strings("error").format("Failed to send query"))

            self.pending_queries[sent_msg.id] = (message.chat_id, message.id)
            try:
                response = await self.client.wait_event(
                    events.NewMessage(chats=bot.id, from_users=bot.id, incoming=True, func=lambda m: m.id > sent_msg.id),
                    timeout=self.timeout
                )
                if response:
                    return await self.inline.query_answer(message, response.text or "🎵 Music found", forward=response)
                return await self.inline.query_answer(message, self.strings("no_response"))
            except asyncio.TimeoutError:
                return await self.inline.query_answer(message, self.strings("no_response"))
            finally:
                self.pending_queries.pop(sent_msg.id, None)
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
        except UsernameNotOccupiedError:
            return await self.inline.query_answer(message, self.strings("bot_unavailable"))
        except Exception as e:
            logger.exception(f"Inline error: {e}")
            return await self.inline.query_answer(message, self.strings("error").format(str(e)))