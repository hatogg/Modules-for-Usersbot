__version__ = (1, 4, 0)

import aiohttp
import logging
import time
from telethon import events
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class AlertsUa(loader.Module):
    """Модуль для статусу повітряних тривог в Україні. Автор: X44TO (t.me/devx44to)"""

    strings = {
        "name": "AlertsUa by X44TO",
        "_cls_doc": "Модуль для статусу повітряних тривог в Україні. Автор: X44TO (t.me/devx44to)",
        "no_token": "❌ <b>API токен не встановлено!</b>\nВикористовуй <code>.settoken [токен]</code>",
        "checking": "🔄 <b>Перевіряю тривоги...</b>",
        "no_alerts": "✅ <b>Немає активних тривог.</b>",
        "active_alerts": "🔔 <b>Активні тривоги (оновлено о {time}):</b>\n\n{list}",
        "alert_item": "📍 {location}\n   🕐 Початок: {started_at}\n   📝 Причина: {notes}\n   Тип: {type}",
        "status_oblast": "📊 <b>Статус по областях:</b>\n{status}",
        "status_item": "📍 {oblast}: {status}",
        "specific_status": "📍 <b>Статус для {location}:</b> {status}",
        "history": "📜 <b>Історія тривог за місяць для {location}:</b>\n\n{list}",
        "history_item": "🔔 {started_at} - {finished_at or 'Триває'} ({type})",
        "error": "❌ <b>Помилка: {error}</b>",
        "set_token": "✅ <b>Токен встановлено.</b>",
        "invalid_uid": "❌ <b>Невірний UID або назва області.</b>",
        "using_cache": "ℹ️ <b>Використано кешовані дані.</b>",
        "start_alerts": "▶️ <b>Розпочато оновлення тривог кожні хвилину.</b>",
        "stop_alerts": "⏹️ <b>Оновлення тривог зупинено.</b>",
        "already_running": "ℹ️ <b>Оновлення вже запущено.</b>",
        "not_running": "ℹ️ <b>Оновлення не запущено.</b>",
        "alert_init_failed": "❌ <b>Не вдалося ініціалізувати оновлення тривог.</b>"
    }

    def __init__(self):
        self.token = None
        self.oblasts = [
            "Автономна Республіка Крим", "Волинська область", "Вінницька область", "Дніпропетровська область",
            "Донецька область", "Житомирська область", "Закарпатська область", "Запорізька область",
            "Івано-Франківська область", "м. Київ", "Київська область", "Кіровоградська область",
            "Луганська область", "Львівська область", "Миколаївська область", "Одеська область",
            "Полтавська область", "Рівненська область", "м. Севастополь", "Сумська область",
            "Тернопільська область", "Харківська область", "Херсонська область", "Хмельницька область",
            "Черкаська область", "Чернівецька область", "Чернігівська область"
        ]
        self.uid_map = {name: i+1 for i, name in enumerate(self.oblasts)}
        self.cache = {}  # {endpoint: {"data": data, "timestamp": time}}
        self.cache_ttl = 300  # 5 хвилин
        self.alert_task = None
        self.alert_msg_id = None
        self.alert_chat_id = None

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.token = self.get("token", None)
        logger.info("Модуль AlertsUa ініціалізовано")
        if not self.token:
            logger.warning("Токен не встановлено")
            await utils.answer(self, self.strings["no_token"])

    def get_cached(self, endpoint: str):
        if endpoint in self.cache:
            cached = self.cache[endpoint]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                logger.debug(f"Використано кеш для {endpoint}")
                return cached["data"]
            else:
                logger.debug(f"Кеш для {endpoint} застарів, видалено")
                del self.cache[endpoint]
        return None

    async def api_request(self, endpoint: str):
        if not self.token:
            logger.error("Токен відсутній")
            return None
        cached = self.get_cached(endpoint)
        if cached is not None:
            logger.info(f"Повернуто кеш для {endpoint}")
            await utils.answer(self, self.strings["using_cache"])
            return cached

        logger.debug(f"Виконую запит до {endpoint}")
        url = f"https://api.alerts.in.ua{endpoint}?token={self.token}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    logger.debug(f"Отримана відповідь від {url} зі статусом {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        self.cache[endpoint] = {"data": data, "timestamp": time.time()}
                        logger.info(f"Успішно кешовано дані для {endpoint}")
                        return data
                    elif resp.status == 429:
                        logger.warning(f"Ліміт запитів перевищено для {endpoint}")
                        return {"error": "Забагато запитів"}
                    else:
                        logger.error(f"Помилка HTTP {resp.status} для {endpoint}")
                        return {"error": f"HTTP {resp.status}"}
            except Exception as e:
                logger.error(f"Помилка API для {endpoint}: {e}")
                return {"error": str(e)}

    async def get_active_alerts(self):
        data = await self.api_request("/v1/alerts/active.json")
        if "error" in data:
            return data
        return data.get("alerts", [])

    async def get_oblasts_status(self):
        data = await self.api_request("/v1/iot/active_air_raid_alerts_by_oblast.json")
        if "error" in data or isinstance(data, str):
            return data
        status_str = data
        status_map = {}
        for i, status in enumerate(status_str):
            oblast = self.oblasts[i]
            status_desc = {"A": "🔔 Активна", "P": "⚠️ Часткова", "N": "✅ Немає"}.get(status, "❓ Невідомо")
            status_map[oblast] = status_desc
        self.cache["/v1/iot/active_air_raid_alerts_by_oblast.json"] = {"data": status_map, "timestamp": time.time()}
        logger.debug(f"Оброблено статус по областях: {len(status_map)} записів")
        return status_map

    async def get_specific_status(self, uid: str):
        data = await self.api_request(f"/v1/iot/active_air_raid_alerts/{uid}.json")
        if "error" in data or isinstance(data, str):
            return data
        status = data
        status_desc = {"A": "🔔 Активна", "P": "⚠️ Часткова", "N": "✅ Немає"}.get(status, "❓ Невідомо")
        self.cache[f"/v1/iot/active_air_raid_alerts/{uid}.json"] = {"data": status_desc, "timestamp": time.time()}
        logger.debug(f"Статус для UID {uid}: {status_desc}")
        return status_desc

    async def get_history(self, uid: str):
        data = await self.api_request(f"/v1/regions/{uid}/alerts/month_ago.json")
        if "error" in data:
            return data
        return data.get("alerts", [])

    async def update_alerts(self):
        logger.info("Розпочато цикл оновлення тривог")
        while True:
            if not self.token or not self.alert_chat_id or not self.alert_msg_id:
                logger.error("Немає даних для оновлення тривог")
                await self.client.send_message(self.alert_chat_id or (await self.client.get_me()).id, self.strings["alert_init_failed"])
                break
            try:
                alerts = await self.get_active_alerts()
                logger.debug(f"Отримані тривоги: {len(alerts)} записів")
                if isinstance(alerts, dict) and "error" in alerts:
                    await self.client.edit_message(self.alert_chat_id, self.alert_msg_id, self.strings["error"].format(error=alerts["error"]))
                elif not alerts:
                    await self.client.edit_message(self.alert_chat_id, self.alert_msg_id, self.strings["no_alerts"])
                else:
                    alert_list = "\n\n".join([
                        self.strings["alert_item"].format(
                            location=item["location_title"],
                            started_at=item["started_at"][11:16] if item["started_at"] else "Невідомо",
                            notes=item.get("notes", "Немає"),
                            type={"air_raid": "Повітряна тривога", "artillery_shelling": "Артилерійський обстріл", "urban_fights": "Міські бої", "chemical": "Хімічна загроза", "nuclear": "Ядерна загроза"}.get(item["alert_type"], item["alert_type"])
                        ) for item in alerts
                    ])
                    current_time = time.strftime("%H:%M", time.localtime())
                    text = self.strings["active_alerts"].format(list=alert_list, time=current_time)
                    await self.client.edit_message(self.alert_chat_id, self.alert_msg_id, text)
                    logger.info(f"Оновлено тривоги о {current_time}")
            except Exception as e:
                logger.error(f"Помилка оновлення тривог: {e}")
                await self.client.send_message(self.alert_chat_id, f"❌ <b>Помилка оновлення: {e}</b>")
                break
            await asyncio.sleep(60)

    @loader.command()
    async def settoken(self, message):
        """Встановлює API токен. Аргумент: [токен]"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_token"])
            logger.warning("Спроба встановлення токена без аргументу")
            return
        self.token = args.strip()
        self.set("token", self.token)
        logger.info("Токен успішно встановлено")
        await utils.answer(message, self.strings["set_token"])

    @loader.command()
    async def alerts(self, message):
        """Показує активні тривоги."""
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            logger.error("Відсутній токен")
            return
        await utils.answer(message, self.strings["checking"])
        logger.debug("Початок отримання активних тривог")
        alerts = await self.get_active_alerts()
        if isinstance(alerts, dict) and "error" in alerts:
            await utils.answer(message, self.strings["error"].format(error=alerts["error"]))
            logger.error(f"Помилка API: {alerts['error']}")
            return
        if not alerts:
            await utils.answer(message, self.strings["no_alerts"])
            logger.info("Немає активних тривог")
            return
        alert_list = "\n\n".join([
            self.strings["alert_item"].format(
                location=item["location_title"],
                started_at=item["started_at"][11:16] if item["started_at"] else "Невідомо",
                notes=item.get("notes", "Немає"),
                type={"air_raid": "Повітряна тривога", "artillery_shelling": "Артилерійський обстріл", "urban_fights": "Міські бої", "chemical": "Хімічна загроза", "nuclear": "Ядерна загроза"}.get(item["alert_type"], item["alert_type"])
            ) for item in alerts
        ])
        current_time = time.strftime("%H:%M", time.localtime())
        text = self.strings["active_alerts"].format(list=alert_list, time=current_time)
        msg = await utils.answer(message, text)
        self.alert_msg_id = msg.id
        self.alert_chat_id = message.chat_id
        logger.debug(f"Надіслано початкове повідомлення з ID {self.alert_msg_id}")

    @loader.command()
    async def startalerts(self, message):
        """Запускає оновлення тривог кожні хвилину в одному повідомленні."""
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            logger.error("Відсутній токен при старті оновлення")
            return
        if self.alert_task and not self.alert_task.done():
            await utils.answer(message, self.strings["already_running"])
            logger.info("Оновлення вже запущено")
            return
        await utils.answer(message, self.strings["checking"])
        logger.debug("Початок ініціалізації оновлення тривог")
        alerts = await self.get_active_alerts()
        if isinstance(alerts, dict) and "error" in alerts:
            await utils.answer(message, self.strings["error"].format(error=alerts["error"]))
            logger.error(f"Помилка API при старті: {alerts['error']}")
            return
        alert_list = "\n\n".join([
            self.strings["alert_item"].format(
                location=item["location_title"],
                started_at=item["started_at"][11:16] if item["started_at"] else "Невідомо",
                notes=item.get("notes", "Немає"),
                type={"air_raid": "Повітряна тривога", "artillery_shelling": "Артилерійський обстріл", "urban_fights": "Міські бої", "chemical": "Хімічна загроза", "nuclear": "Ядерна загроза"}.get(item["alert_type"], item["alert_type"])
            ) for item in alerts
        ]) if alerts else self.strings["no_alerts"]
        current_time = time.strftime("%H:%M", time.localtime())
        text = self.strings["active_alerts"].format(list=alert_list, time=current_time)
        msg = await utils.answer(message, text)
        self.alert_msg_id = msg.id
        self.alert_chat_id = message.chat_id
        self.alert_task = asyncio.create_task(self.update_alerts())
        logger.info(f"Оновлення тривог запущено для повідомлення {self.alert_msg_id}")
        await utils.answer(message, self.strings["start_alerts"])

    @loader.command()
    async def stopalerts(self, message):
        """Зупиняє оновлення тривог."""
        if not self.alert_task or self.alert_task.done():
            await utils.answer(message, self.strings["not_running"])
            logger.info("Оновлення не запущено")
            return
        try:
            logger.debug("Спроба зупинити оновлення тривог")
            self.alert_task.cancel()
            await asyncio.sleep(0.1)  # Даємо час на завершення
            self.alert_task = None
            self.alert_msg_id = None
            self.alert_chat_id = None
            logger.info("Оновлення тривог зупинено")
            await utils.answer(message, self.strings["stop_alerts"])
        except Exception as e:
            logger.error(f"Помилка зупинки оновлення: {e}")
            await utils.answer(message, self.strings["error"].format(error="Не вдалося зупинити оновлення"))

    @loader.command()
    async def oblasts(self, message):
        """Показує статус тривог по областях."""
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            logger.error("Відсутній токен")
            return
        await utils.answer(message, self.strings["checking"])
        logger.debug("Отримую статус по областях")
        status = await self.get_oblasts_status()
        if isinstance(status, dict) and "error" in status:
            await utils.answer(message, self.strings["error"].format(error=status["error"]))
            logger.error(f"Помилка API: {status['error']}")
            return
        status_list = "\n".join([
            self.strings["status_item"].format(oblast=oblast, status=status_desc)
            for oblast, status_desc in status.items()
        ])
        text = self.strings["status_oblast"].format(status=status_list)
        await utils.answer(message, text)
        logger.debug("Статус по областях успішно відображено")

    @loader.command()
    async def alertstatus(self, message):
        """Статус тривоги для області. Аргумент: [UID або назва області]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "❌ <b>Вкажи UID або назву області.</b>")
            logger.warning("Відсутній аргумент для alertstatus")
            return
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            logger.error("Відсутній токен")
            return
        await utils.answer(message, self.strings["checking"])
        logger.debug(f"Перевірка статусу для {args}")
        uid = None
        try:
            uid = str(int(args))
        except ValueError:
            for name, u in self.uid_map.items():
                if args.lower() in name.lower():
                    uid = str(u)
                    break
        if not uid:
            await utils.answer(message, self.strings["invalid_uid"])
            logger.warning(f"Невірний UID або назва: {args}")
            return
        status = await self.get_specific_status(uid)
        if isinstance(status, dict) and "error" in status:
            await utils.answer(message, self.strings["error"].format(error=status["error"]))
            logger.error(f"Помилка API для UID {uid}: {status['error']}")
            return
        location_name = next((name for name in self.oblasts if args.lower() in name.lower()), "Область")
        text = self.strings["specific_status"].format(location=location_name, status=status)
        await utils.answer(message, text)
        logger.debug(f"Статус для {location_name}: {status}")

    @loader.command()
    async def alerthistory(self, message):
        """Історія тривог за місяць. Аргумент: [UID або назва області]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "❌ <b>Вкажи UID або назву області.</b>")
            logger.warning("Відсутній аргумент для alerthistory")
            return
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            logger.error("Відсутній токен")
            return
        await utils.answer(message, self.strings["checking"])
        logger.debug(f"Отримую історію для {args}")
        uid = None
        try:
            uid = str(int(args))
        except ValueError:
            for name, u in self.uid_map.items():
                if args.lower() in name.lower():
                    uid = str(u)
                    break
        if not uid:
            await utils.answer(message, self.strings["invalid_uid"])
            logger.warning(f"Невірний UID або назва: {args}")
            return
        history = await self.get_history(uid)
        if isinstance(history, dict) and "error" in history:
            await utils.answer(message, self.strings["error"].format(error=history["error"]))
            logger.error(f"Помилка API для UID {uid}: {history['error']}")
            return
        if not history:
            await utils.answer(message, "📜 <b>Історія порожня.</b>")
            logger.info(f"Історія для {uid} порожня")
            return
        location_name = next((name for name in self.oblasts if args.lower() in name.lower()), "Область")
        history_list = "\n".join([
            self.strings["history_item"].format(
                started_at=item["started_at"][:16],
                finished_at=item["finished_at"][:16] if item["finished_at"] else "Триває",
                type={"air_raid": "Повітряна тривога", "artillery_shelling": "Обстріл", "urban_fights": "Міські бої", "chemical": "Хімічна", "nuclear": "Ядерна"}.get(item["alert_type"], item["alert_type"])
            ) for item in history
        ])
        text = self.strings["history"].format(location=location_name, list=history_list)
        await utils.answer(message, text)
        logger.debug(f"Історія для {location_name} успішно відображена")

    def config(self):
        return {"token": None}