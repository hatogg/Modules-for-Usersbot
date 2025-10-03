__version__ = (1, 3, 0)

import aiohttp
import logging
import time
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
        self.alert_task = None  # Для циклу оновлення
        self.alert_msg_id = None  # ID повідомлення для редагування
        self.alert_chat_id = None  # ID чату для редагування

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.token = self.get("token", None)
        if not self.token:
            await utils.answer(self, self.strings["no_token"])

    def get_cached(self, endpoint: str):
        """Повертає кешовані дані або None, якщо застаріло."""
        if endpoint in self.cache:
            cached = self.cache[endpoint]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                logger.debug(f"Використано кеш для {endpoint}")
                return cached["data"]
            else:
                del self.cache[endpoint]
        return None

    async def api_request(self, endpoint: str):
        """Загальний запит до API з кешуванням."""
        if not self.token:
            return None
        cached = self.get_cached(endpoint)
        if cached is not None:
            return cached

        url = f"https://api.alerts.in.ua{endpoint}?token={self.token}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.cache[endpoint] = {"data": data, "timestamp": time.time()}
                        return data
                    elif resp.status == 429:
                        logger.warning("Ліміт запитів перевищено")
                        return {"error": "Забагато запитів"}
                    else:
                        return {"error": f"HTTP {resp.status}"}
            except Exception as e:
                logger.error(f"Помилка API: {e}")
                return {"error": str(e)}

    async def get_active_alerts(self):
        """Отримує активні тривоги."""
        data = await self.api_request("/v1/alerts/active.json")
        if "error" in data:
            return data
        return data.get("alerts", [])

    async def get_oblasts_status(self):
        """Статус по областях (A/P/N)."""
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
        return status_map

    async def get_specific_status(self, uid: str):
        """Статус для конкретної локації."""
        data = await self.api_request(f"/v1/iot/active_air_raid_alerts/{uid}.json")
        if "error" in data or isinstance(data, str):
            return data
        status = data
        status_desc = {"A": "🔔 Активна", "P": "⚠️ Часткова", "N": "✅ Немає"}.get(status, "❓ Невідомо")
        self.cache[f"/v1/iot/active_air_raid_alerts/{uid}.json"] = {"data": status_desc, "timestamp": time.time()}
        return status_desc

    async def get_history(self, uid: str):
        """Історія тривог за місяць."""
        data = await self.api_request(f"/v1/regions/{uid}/alerts/month_ago.json")
        if "error" in data:
            return data
        return data.get("alerts", [])

    async def update_alerts(self):
        """Цикл оновлення тривог у повідомленні."""
        while True:
            if not self.token or not self.alert_chat_id or not self.alert_msg_id:
                logger.error("Немає даних для оновлення тривог")
                await self.client.send_message(self.alert_chat_id or (await self.client.get_me()).id, self.strings["alert_init_failed"])
                break
            try:
                alerts = await self.get_active_alerts()
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
            except Exception as e:
                logger.error(f"Помилка оновлення тривог: {e}")
                await self.client.send_message(self.alert_chat_id, f"❌ <b>Помилка оновлення: {e}</b>")
                break
            await asyncio.sleep(60)  # Оновлення кожні 60 секунд

    @loader.command()
    async def settoken(self, message):
        """Встановлює API токен. Аргумент: [токен]"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_token"])
            return
        self.token = args.strip()
        self.set("token", self.token)
        await utils.answer(message, self.strings["set_token"])

    @loader.command()
    async def alerts(self, message):
        """Показує активні тривоги."""
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            return
        await utils.answer(message, self.strings["checking"])
        alerts = await self.get_active_alerts()
        if isinstance(alerts, dict) and "error" in alerts:
            await utils.answer(message, self.strings["error"].format(error=alerts["error"]))
            return
        if not alerts:
            await utils.answer(message, self.strings["no_alerts"])
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

    @loader.command()
    async def startalerts(self, message):
        """Запускає оновлення тривог кожні хвилину в одному повідомленні."""
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            return
        if self.alert_task and not self.alert_task.done():
            await utils.answer(message, self.strings["already_running"])
            return
        await utils.answer(message, self.strings["checking"])
        alerts = await self.get_active_alerts()
        if isinstance(alerts, dict) and "error" in alerts:
            await utils.answer(message, self.strings["error"].format(error=alerts["error"]))
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
        await utils.answer(message, self.strings["start_alerts"])

    @loader.command()
    async def stopalerts(self, message):
        """Зупиняє оновлення тривог."""
        if not self.alert_task or self.alert_task.done():
            await utils.answer(message, self.strings["not_running"])
            return
        try:
            self.alert_task.cancel()
            self.alert_task = None
            self.alert_msg_id = None
            self.alert_chat_id = None
            await utils.answer(message, self.strings["stop_alerts"])
        except Exception as e:
            logger.error(f"Помилка зупинки оновлення: {e}")
            await utils.answer(message, self.strings["error"].format(error="Не вдалося зупинити оновлення"))

    @loader.command()
    async def oblasts(self, message):
        """Показує статус тривог по областях."""
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            return
        await utils.answer(message, self.strings["checking"])
        status = await self.get_oblasts_status()
        if isinstance(status, dict) and "error" in status:
            await utils.answer(message, self.strings["error"].format(error=status["error"]))
            return
        status_list = "\n".join([
            self.strings["status_item"].format(oblast=oblast, status=status_desc)
            for oblast, status_desc in status.items()
        ])
        text = self.strings["status_oblast"].format(status=status_list)
        await utils.answer(message, text)

    @loader.command()
    async def alertstatus(self, message):
        """Статус тривоги для області. Аргумент: [UID або назва області]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "❌ <b>Вкажи UID або назву області.</b>")
            return
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            return
        await utils.answer(message, self.strings["checking"])
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
            return
        status = await self.get_specific_status(uid)
        if isinstance(status, dict) and "error" in status:
            await utils.answer(message, self.strings["error"].format(error=status["error"]))
            return
        location_name = next((name for name in self.oblasts if args.lower() in name.lower()), "Область")
        text = self.strings["specific_status"].format(location=location_name, status=status)
        await utils.answer(message, text)

    @loader.command()
    async def alerthistory(self, message):
        """Історія тривог за місяць. Аргумент: [UID або назва області]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "❌ <b>Вкажи UID або назву області.</b>")
            return
        if not self.token:
            await utils.answer(message, self.strings["no_token"])
            return
        await utils.answer(message, self.strings["checking"])
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
            return
        history = await self.get_history(uid)
        if isinstance(history, dict) and "error" in history:
            await utils.answer(message, self.strings["error"].format(error=history["error"]))
            return
        if not history:
            await utils.answer(message, "📜 <b>Історія порожня.</b>")
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

    def config(self):
        return {"token": None}