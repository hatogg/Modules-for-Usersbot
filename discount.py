__version__ = (1, 4, 0)

from telethon import events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import UsernameInvalidError, PeerIdInvalidError
import logging
import re
import asyncio

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class SaveDeleted(loader.Module):
    """Зберігає видалені та відредаговані повідомлення у приватний чат. Автор: X44TO (t.me/devx44to)"""

    strings = {
        "name": "SaveDeleted by X44TO",
        "_cls_doc": "Зберігає видалені та відредаговані повідомлення у приватний чат. Автор: X44TO (t.me/devx44to)",
        "save_chat_not_set": "❌ <b>Чат для збереження не встановлено!</b>\nВикористовуй <code>.saveon [chat_id або username або t.me/username]</code>",
        "save_chat_set": "✅ <b>Чат для збереження: {chat}</b>",
        "save_on": "🔄 <b>Увімкнено збереження для чату: {chat}</b>",
        "save_off": "🔄 <b>Вимкнено збереження для чату: {chat}</b>",
        "all_chats": "Всі чати (окрім приватних з собою)",
        "no_save_chat": "❌ <b>Чат для збереження не встановлено.</b>",
        "auto_created": "✅ <b>Автоматично створено чат для збереження: Saved Messages</b>\nТут будуть надсилатися видалені повідомлення.",
        "invalid_link": "❌ <b>Невірне посилання або ID. Спробуй username, ID або t.me/username.</b>",
    }

    def __init__(self):
        self.save_chat = None
        self.enabled_chats = []
        self.messages = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        me = await client.get_me()

        # Завантаження конфігурації
        self.save_chat = self.get("save_chat", None)
        self.enabled_chats = self.get("enabled_chats", [])

        # Налаштування чату для збереження
        if self.save_chat is None:
            self.save_chat = me.id  # Saved Messages за замовчуванням
            self.set("save_chat", self.save_chat)
            try:
                await client.send_message(self.save_chat, "🗑️ <b>SaveDeleted by X44TO активовано!</b>\nТут будуть зберігатися видалені та відредаговані повідомлення з моніторингових чатів.")
                await utils.answer(self, self.strings["auto_created"])
            except Exception as e:
                logger.error(f"Помилка при надсиланні вступного повідомлення: {e}")
        else:
            try:
                entity = await client.get_entity(self.save_chat)
                self.strings["save_chat_set"] = self.strings["save_chat_set"].format(chat=utils.escape_html(entity.title or entity.first_name or "Saved Messages"))
            except:
                self.save_chat = me.id
                self.set("save_chat", self.save_chat)
                await client.send_message(self.save_chat, "🗑️ <b>SaveDeleted by X44TO активовано!</b>\nТут будуть зберігатися видалені та відредаговані повідомлення з моніторингових чатів.")
                await utils.answer(self, self.strings["auto_created"])

    def parse_entity_arg(self, arg: str):
        """Парсить аргумент для get_entity: username, ID, t.me/username."""
        if not arg:
            return None
        arg = re.sub(r'^https?://', '', arg)
        if arg.startswith('t.me/'):
            arg = arg[5:]
        if arg.startswith('c/'):
            arg = arg.split('/')[-1]
        try:
            return int(arg)
        except ValueError:
            return arg

    @loader.command()
    async def saveon(self, message):
        """Встановлює чат для збереження видалених повідомлень. Аргумент: [chat_id або username або t.me/username]"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["save_chat_not_set"])
            return
        parsed = self.parse_entity_arg(args)
        if parsed is None:
            await utils.answer(message, self.strings["invalid_link"])
            return
        try:
            entity = await self.client.get_entity(parsed)
            self.save_chat = entity.id
            self.set("save_chat", self.save_chat)
            chat_title = entity.title or entity.first_name or "Saved Messages"
            await utils.answer(message, self.strings["save_chat_set"].format(chat=utils.escape_html(chat_title)))
        except (UsernameInvalidError, PeerIdInvalidError):
            await utils.answer(message, self.strings["invalid_link"])
        except Exception as e:
            await utils.answer(message, f"❌ <b>Помилка: {e}</b>")

    @loader.command()
    async def saveoff(self, message):
        """Вимикає збереження видалених повідомлень."""
        self.save_chat = None
        self.set("save_chat", None)
        await utils.answer(message, "✅ <b>Збереження вимкнено.</b>")

    @loader.command()
    async def watchon(self, message):
        """Увімкнути збереження для чату. Аргумент: [chat_id або username або t.me/username]"""
        args = utils.get_args_raw(message)
        if not args:
            self.enabled_chats = []
            self.set("enabled_chats", self.enabled_chats)
            await utils.answer(message, self.strings["save_off"].format(chat=self.strings["all_chats"]))
            return
        parsed = self.parse_entity_arg(args)
        if parsed is None:
            await utils.answer(message, self.strings["invalid_link"])
            return
        try:
            entity = await self.client.get_entity(parsed)
            chat_id = entity.id
            if chat_id not in self.enabled_chats:
                self.enabled_chats.append(chat_id)
                self.set("enabled_chats", self.enabled_chats)
            chat_title = entity.title or entity.first_name or "невідомий"
            await utils.answer(message, self.strings["save_on"].format(chat=utils.escape_html(chat_title)))
        except (UsernameInvalidError, PeerIdInvalidError):
            await utils.answer(message, self.strings["invalid_link"])
        except Exception as e:
            await utils.answer(message, f"❌ <b>Помилка: {e}</b>")

    @loader.command()
    async def watchoff(self, message):
        """Вимкнути збереження для чату. Аргумент: [chat_id або username або t.me/username]"""
        args = utils.get_args_raw(message)
        if not args:
            self.enabled_chats = [0]
            self.set("enabled_chats", self.enabled_chats)
            await utils.answer(message, self.strings["save_on"].format(chat=self.strings["all_chats"]))
            return
        parsed = self.parse_entity_arg(args)
        if parsed is None:
            await utils.answer(message, self.strings["invalid_link"])
            return
        try:
            entity = await self.client.get_entity(parsed)
            chat_id = entity.id
            if chat_id in self.enabled_chats:
                self.enabled_chats.remove(chat_id)
                self.set("enabled_chats", self.enabled_chats)
            chat_title = entity.title or entity.first_name or "невідомий"
            await utils.answer(message, self.strings["save_off"].format(chat=utils.escape_html(chat_title)))
        except (UsernameInvalidError, PeerIdInvalidError):
            await utils.answer(message, self.strings["invalid_link"])
        except Exception as e:
            await utils.answer(message, f"❌ <b>Помилка: {e}</b>")

    @loader.watcher("message")
    async def message_watcher(self, message):
        """Зберігає нові повідомлення для подальшого трекінгу."""
        if not self.save_chat:
            return
        chat_id = message.chat_id
        if self.enabled_chats and chat_id not in self.enabled_chats and 0 not in self.enabled_chats:
            return
        me_id = (await self.client.get_me()).id
        if chat_id == me_id:
            return

        msg_id = message.id
        if chat_id not in self.messages:
            self.messages[chat_id] = {}
        if len(self.messages[chat_id]) > 1000:
            oldest = min(self.messages[chat_id].keys())
            del self.messages[chat_id][oldest]

        self.messages[chat_id][msg_id] = message
        logger.debug(f"Збережено повідомлення {msg_id} з чату {chat_id}")

    @loader.watcher("message_deleted")
    async def deleted_watcher(self, event):
        """Обробляє видалені повідомлення."""
        if not self.save_chat:
            return
        chat_id = event.chat_id
        deleted_ids = event.deleted_ids  # Це список int/str
        if self.enabled_chats and chat_id not in self.enabled_chats and 0 not in self.enabled_chats:
            return

        for deleted_id in deleted_ids:
            msg_id = int(deleted_id) if isinstance(deleted_id, (str, int)) else deleted_id  # Виправлення для str/int
            if chat_id in self.messages and msg_id in self.messages[chat_id]:
                orig_msg = self.messages[chat_id].pop(msg_id)
                try:
                    caption = f"🗑️ <b>Видалено з чату:</b> {utils.escape_html(await self.get_chat_title(chat_id))}\n<i>ID: {msg_id}</i>"
                    if orig_msg.media:
                        await self.client.send_file(self.save_chat, orig_msg.media, caption=caption)
                    else:
                        await self.client.send_message(self.save_chat, caption + f"\n\n{orig_msg.text or ''}")
                except Exception as e:
                    logger.error(f"Помилка при збереженні видаленого: {e}")
                    await self.client.send_message(self.save_chat, f"🗑️ <b>Видалено (помилка доступу):</b> {msg_id} з {chat_id}")

    @loader.watcher("message_edited")
    async def edited_watcher(self, event):
        """Обробляє відредаговані повідомлення."""
        if not self.save_chat:
            return
        chat_id = event.chat_id
        if self.enabled_chats and chat_id not in self.enabled_chats and 0 not in self.enabled_chats:
            return

        # Виправлення: event.message може бути str (ID) або Message
        if isinstance(event.message, str) or isinstance(event.message, int):
            msg_id = int(event.message)  # Використовуємо ID напряму
            edited_msg = None  # Не маємо повного повідомлення, пропускаємо деталі
            logger.warning(f"Lightweight edit event для ID {msg_id} — неповні дані")
        else:
            msg_id = event.message.id
            edited_msg = event.message

        if chat_id in self.messages and msg_id in self.messages[chat_id]:
            orig_msg = self.messages[chat_id][msg_id]
            try:
                if edited_msg:  # Тільки якщо маємо повне редаговане повідомлення
                    caption = f"✏️ <b>Відредаговано в чаті:</b> {utils.escape_html(await self.get_chat_title(chat_id))}\n<i>ID: {msg_id}</i>\n\n<b>Оригінал:</b>\n{orig_msg.text or '[Медіа]'}"
                    if orig_msg.media:
                        await self.client.send_file(self.save_chat, orig_msg.media, caption=caption)
                    else:
                        await self.client.send_message(self.save_chat, caption)
                    # Оновлюємо збережене
                    self.messages[chat_id][msg_id] = edited_msg
                else:
                    logger.debug(f"Пропущено детальне збереження редагування для {msg_id} (lightweight event)")
            except Exception as e:
                logger.error(f"Помилка при збереженні відредагованого: {e}")

    async def get_chat_title(self, chat_id):
        """Допоміжна функція для назви чату."""
        try:
            entity = await self.client.get_entity(chat_id)
            return entity.title or entity.first_name or "невідомий"
        except:
            return f"ID {chat_id}"