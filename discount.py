__version__ = (1, 1, 0)

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
        "_cls_doc": "Виводить список ігор зі знижками в Steam (Україна, UAH). Автор: X44TO (t.me/devx44to)",
        "no_discounts": "ℹ️ <b>Немає ігор зі знижками наразі.</b>",
        "error": "❌ <b>Помилка: {error}</b>",
        "checking": "🔄 <b>Перевіряю знижки...</b>",
        "discount_list": "🛒 <b>Ігри зі знижками (Україна, до 10):</b>\n\n{list}",
        "no_results": "❌ <b>Нічого не знайдено за запитом.</b>",
        "specific_discount": "🛒 <b>Знижка на {name}:</b>\n💰 Без знижки: {original_price:.2f} грн\n💸 Зі знижкою: {final_price:.2f} грн\n📉 Знижка: {discount_percent}%\n🔗 https://store.steampowered.com/app/{appid}"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def get_popular_games(self):
        """Отримує список популярних ігор зі знижками."""
        async with aiohttp.ClientSession() as session:
            url = "https://store.steampowered.com/api/featured?cc=ua&l=ukrainian"
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error("Помилка статусу відповіді від Steam API")
                        return []
                    data = await resp.json()
                    appids = [str(game["id"]) for game in data.get("featured_win", []) if game.get("discount_percent", 0) > 0]
                    return appids[:10]  # Обмеження до 10 ігор
            except Exception as e:
                logger.error(f"Помилка API: {e}")
                return []

    async def get_game_details(self, appid: str):
        """Отримує деталі гри, включаючи жанри."""
        async with aiohttp.ClientSession() as session:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=ua"
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
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

    async def get_games_by_genre(self, genre: str, appids: list):
        """Фільтрує ігри за жанром."""
        details = await asyncio.gather(*(self.get_game_details(appid) for appid in appids))
        return [game for game in details if game and genre.lower() in game["genres"].lower()][:10]

    @loader.command()
    async def discounts(self, message):
        """Виводить список ігор зі знижками (до 10). Аргумент: [жанр, наприклад 'RPG' або 'Action']"""
        args = utils.get_args_raw(message).strip()
        await utils.answer(message, self.strings["checking"])
        appids = await self.get_popular_games()
        if not appids:
            await utils.answer(message, self.strings["no_discounts"])
            return

        if args:
            genre = args
            games = await self.get_games_by_genre(genre, appids)
        else:
            games = await asyncio.gather(*(self.get_game_details(appid) for appid in appids))
            games = [game for game in games if game][:10]

        if not games:
            await utils.answer(message, self.strings["no_discounts"])
            return

        discount_list = "\n".join([
            f"• {game['name']} ({game['genres']})\n"
            f"   💰 Без знижки: {game['original_price']:.2f} грн\n"
            f"   💸 Зі знижкою: {game['final_price']:.2f} грн\n"
            f"   📉 Знижка: {game['discount_percent']}%\n"
            f"   🔗 https://store.steampowered.com/app/{game['appid']}"
            for game in games
        ])
        text = self.strings["discount_list"].format(list=discount_list)
        await utils.answer(message, text, parse_mode="HTML")

    @loader.command()
    async def discount(self, message):
        """Перевіряє знижку на конкретну гру. Аргумент: [назва гри]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "❌ <b>Вкажи назву гри.</b>")
            return
        await utils.answer(message, self.strings["checking"])
        query = args.lower()
        appids = await self.get_popular_games()
        for appid in appids:
            game = await self.get_game_details(appid)
            if game and query in game["name"].lower():
                text = self.strings["specific_discount"].format(
                    name=game["name"],
                    original_price=game["original_price"],
                    final_price=game["final_price"],
                    discount_percent=game["discount_percent"],
                    appid=game["appid"]
                )
                await utils.answer(message, text, parse_mode="HTML")
                return
        await utils.answer(message, self.strings["no_results"])