# created by https://t.me/devx44to

from .. import loader, utils
from telethon import events

@loader.tds
class AutoBold(loader.Module):
    """Модуль для автоматичного форматування тексту в жирний шрифт у вихідних повідомленнях"""

    strings = {
        "name": "AutoBold",
        "enabled": "<b>Автоматичний жирний шрифт увімкнено</b>",
        "disabled": "<b>Автоматичний жирний шрифт вимкнено</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                True,
                lambda: "Чи увімкнено автоматичний жирний шрифт",
                validator=loader.validators.Boolean(),
            )
        )

    @loader.command()
    async def autoboldtoggle(self, message):
        """Увімкнути/вимкнути автоматичний жирний шрифт"""
        self.config["enabled"] = not self.config["enabled"]
        if self.config["enabled"]:
            await utils.answer(message, self.strings["enabled"])
        else:
            await utils.answer(message, self.strings["disabled"])

    @loader.watcher(out=True, no_commands=True)
    async def watcher(self, message):
        if not self.config["enabled"]:
            return
        if message.raw_text and not message.entities:
            bold_text = f"**{message.raw_text}**"
            await message.edit(bold_text, parse_mode="md")