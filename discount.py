__version__ = (1, 0, 0)

import aiohttp
import logging
from telethon import events
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class SteamDiscounts(loader.Module):
    """Виводить список популярних ігор зі знижками в Steam (Україна, UAH). Автор: X44TO (t.me/devx44to)"""

    strings = {
        "name": "SteamDiscounts by X44TO",
        "_cls_doc": "Виводить список популярних ігор зі знижками в Steam (Україна, UAH). Автор: X44TO (t.me/devx44to)",
        "no_discounts": "ℹ️ <b>Немає ігор зі знижками наразі.</b>",
        "error": "❌ <b>Помилка: {error}</b>",
        "checking": "🔄 <b>Перевіряю знижки...</b>",
        "discount_list": "🛒 <b>Популярні ігри зі знижками (Україна):</b>\n\n{list}"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def get_popular_discounts(self):
        """Отримує список популярних ігор зі знижками в UAH."""
        async with aiohttp.ClientSession() as session:
            url = "https://store.steampowered.com/api/featured?cc=ua&l=ukrainian"
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    discounts = []
                    for game in data.get("featured_win", []):
                        if game.get("discount_percent", 0) > 0:
                            discounts.append({
                                "name": game.get("name", "Unknown"),
                                "original_price": game.get("original_price", 0) / 100,  # У копійках
                                "final_price": game.get("final_price", 0) / 100,  # У копійках
                                "discount_percent": game.get("discount_percent", 0),
                                "appid": game.get("id", 0)
                            })
                    return discounts
            except Exception as e:
                logger.error(f"Помилка API: {e}")
                return None

    @loader.command()
    async def discounts(self, message):
        """Виводить список популярних ігор зі знижками в UAH."""
        await utils.answer(message, self.strings["checking"])
        discounts = await self.get_popular_discounts()
        if not discounts:
            await utils.answer(message, self.strings["no_discounts"])
            return
        discount_list = "\n".join([
            f"• {game['name']}\n"
            f"   💰 Без знижки: {game['original_price']:.2f} грн\n"
            f"   💸 Зі знижкою: {game['final_price']:.2f} грн\n"
            f"   📉 Знижка: {game['discount_percent']}%\n"
            f"   🔗 https://store.steampowered.com/app/{game['appid']}"
            for game in discounts
        ])
        text = self.strings["discount_list"].format(list=discount_list)
        await utils.answer(message, text, parse_mode="HTML")