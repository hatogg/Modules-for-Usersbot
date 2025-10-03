__version__ = (1, 2, 0)

import aiohttp
import logging
from telethon import events
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class SteamDiscounts(loader.Module):
    """Виводить список ігор зі знижками в Steam (Україна, UAH). Автор: X44TO (t.me/devx44to)"""

    strings = {
        "name": "SteamDiscounts by X44TO",
        "_cls_doc": "Виводить список ігор зі знижок у Steam (Україна, UAH). Автор: X44TO (t.me/devx44to)",
        "no_discounts": "ℹ️ <b>Немає ігор зі знижками наразі.</b>",
        "error": "❌ <b>Помилка: {error}</b>",
        "checking": "🔄 <b>Перевіряю знижки...</b>",
        "discount_list": "🛒 <b>Ігри зі знижками (Україна, до 10):</b>\n\n{list}",
        "no_results": "❌ <b>Нічого не знайдено за запитом.</b>",
        "specific_discount": "🛒 <b>Знижка на {name}:</b>\n💰 Без знижки: {original_price:.2f} грн\n💸 Зі знижкою: {final_price:.2f} грн\n📉 Знижка: {discount_percent}%\n🔗 https://store.steampowered.com/app/{appid}",
        "invalid_genre": "❌ <b>Невірний жанр. Спробуй: RPG, Action, Shooter тощо.</b>"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def get_popular_games(self):
        """Отримує список AppID популярних ігор зі знижками."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://store.steampowered.com/api/featured?cc=ua&l=ukrainian") as resp:
                    if resp.status != 200:
                        logger.error(f"Помилка API: Статус {resp.status}")
                        return []
                    data = await resp.json()
                    # Беремо лише ігри зі знижками
                    appids = [
                        str(game["id"]) for game in data.get("featured_win", [])
                        if game.get("discount_percent", 0) > 0
                    ]
                    return appids[:10]  # Обмеження до 10
            except Exception as e:
                logger.error(f"Помилка при отриманні популярних ігор: {e}")
                return []

    async def get_game_details(self, appid: str):
        """Отримує деталі гри, включаючи жанри."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=ua") as resp:
                    if resp.status != 200:
                        logger.error(f"Помилка API для {appid}: Статус {resp.status}")
                        return None
                    data = await resp.json()
                    game_data = data.get(appid, {}).get("data", {})
                    if game_data and "price_overview" in game_data and game_data.get("discount_percent", 0) > 0:
                        price_overview = game_data["price_overview"]
                        genres = ", ".join([genre["description"] for genre in game_data.get("genres", [])]) or "Unknown"
                        return {
                            "name": game_data.get("name", "Unknown"),
                            "original_price": price_overview.get("initial", 0) / 100,
                            "final_price": price_overview.get("final", 0) / 100,
                            "discount_percent": game_data.get("discount_percent", 0),
                            "appid": appid,
                            "genres": genres
                        }
                    return None
            except Exception as e:
                logger.error(f"Помилка деталізації гри {appid}: {e}")
                return None

    async def filter_by_genre(self,