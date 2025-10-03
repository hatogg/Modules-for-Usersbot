__version__ = (1, 3, 0)

import aiohttp
import logging
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class SteamDiscounts(loader.Module):
    """Виводить топ 20 ігор зі знижками в Steam (Україна, UAH) та пошук за назвою. Автор: X44TO (t.me/devx44to)"""

    strings = {
        "name": "SteamDiscounts by X44TO",
        "_cls_doc": "Виводить топ 20 ігор зі знижками в Steam (Україна, UAH) та пошук за назвою. Автор: X44TO (t.me/devx44to)",
        "no_discounts": "ℹ️ <b>Немає ігор зі знижками наразі.</b>",
        "error": "❌ <b>Помилка: {error}</b>",
        "checking": "🔄 <b>Перевіряю знижки...</b>",
        "discount_list": "🛒 <b>Топ 20 ігор зі знижками (Україна):</b>\n\n{list}",
        "no_results": "❌ <b>Гру не знайдено за назвою '{query}'.</b>",
        "specific_discount": "🛒 <b>Знижка на {name}:</b>\n💰 Без знижки: {original_price:.2f} грн\n💸 Зі знижкою: {final_price:.2f} грн\n📉 Знижка: {discount_percent}%\n🔗 https://store.steampowered.com/app/{appid}"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def get_top_discounts(self):
        """Отримує топ 20 ігор зі знижками в UAH."""
        async with aiohttp.ClientSession() as session:
            url = "https://store.steampowered.com/api/featured?cc=ua&l=ukrainian"
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Помилка API: Статус {resp.status}")
                        return None
                    data = await resp.json()
                    discounts = []
                    for game in data.get("featured_win", [])[:20]:  # Топ 20
                        if game.get("discount_percent", 0) > 0:
                            discounts.append({
                                "name": game.get("name", "Unknown"),
                                "original_price": game.get("original_price", 0) / 100,
                                "final_price": game.get("final_price", 0) / 100,
                                "discount_percent": game.get("discount_percent", 0),
                                "appid": game.get("id", 0)
                            })
                    return discounts
            except Exception as e:
                logger.error(f"Помилка API: {e}")
                return None

    @loader.command()
    async def discounts(self, message):
        """Виводить топ 20 ігор зі знижками в UAH."""
        await utils.answer(message, self.strings["checking"])
        discounts = await self.get_top_discounts()
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

    @loader.command()
    async def discount(self, message):
        """Перевіряє знижку на гру за назвою. Аргумент: [назва гри]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "❌ <b>Вкажи назву гри.</b>")
            return
        await utils.answer(message, self.strings["checking"])
        query = args.lower()
        discounts = await self.get_top_discounts()
        if not discounts:
            await utils.answer(message, self.strings["no_discounts"])
            return
        for game in discounts:
            if query in game["name"].lower():
                text = self.strings["specific_discount"].format(
                    name=game["name"],
                    original_price=game["original_price"],
                    final_price=game["final_price"],
                    discount_percent=game["discount_percent"],
                    appid=game["appid"]
                )
                await utils.answer(message, text, parse_mode="HTML")
                return
        await utils.answer(message, self.strings["no_results"].format(query=query))