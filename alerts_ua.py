__version__ = (1, 2, 0)

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
        "not_running": "ℹ️ <b>Оновлення не запущено.</b>"
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

    async def api_request(self,