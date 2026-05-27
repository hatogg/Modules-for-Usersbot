# meta developer: @ttx44to
import aiohttp
from .. import loader, utils

@loader.tds
class AirAlertsMod(loader.Module):
    """Модуль для відстеження тривог по містах/областях та їх причин 🚨"""
    strings = {"name": "AirAlerts"}

    CITY_TO_REGION = {
        "луцьк": "Волинська",
        "ужгород": "Закарпатська",
        "мукачево": "Закарпатська",
        "івано-франківськ": "Івано-Франківська",
        "кропивницький": "Кіровоградська",
        "олександрія": "Кіровоградська",
        "дніпро": "Дніпропетровська",
        "кривий ріг": "Дніпропетровська",
        "кам'янське": "Дніпропетровська",
        "маріуполь": "Донецька",
        "краматорськ": "Донецька",
        "донецьк": "Донецька",
        "мелітополь": "Запорізька",
        "запоріжжя": "Запорізька",
        "кременчук": "Полтавська",
        "полтава": "Полтавська",
        "біла церква": "Київська",
        "бровари": "Київська",
        "київ": "м. Київ",
        "умань": "Черкаська",
        "черкаси": "Черкаська",
        "подільськ": "Одеська",
        "ізмаїл": "Одеська",
        "одеса": "Одеська",
        "рівне": "Рівненська",
        "тернопіль": "Тернопільська",
        "хмельницький": "Хмельницька",
        "кам'янець-подільський": "Хмельницька",
        "вінниця": "Вінницька",
        "житомир": "Житомирська",
        "чернігів": "Чернігівська",
        "суми": "Сумська",
        "харків": "Харківська",
        "миколаїв": "Миколаївська",
        "херсон": "Херсонська",
        "чернівці": "Чернівецька",
        "луганськ": "Луганська",
        "львів": "Львівська",
        "крим": "Крим"
    }

    @loader.command(uk_doc="[місто/область] - дізнатись статус тривоги та причину")
    async def alertcmd(self, message):
        """[місто/область] - перевірити тривогу за локацією та дізнатися причину"""
        args = utils.get_args_raw(message)
        await utils.answer(message, "<i>⏳ Оновлюю дані радару...</i>")
        
        region_text = ""
        
        if args:
            search_query = args.lower()
            
            for city, region in self.CITY_TO_REGION.items():
                base_city = city[:-1] if len(city) > 4 else city
                if search_query.startswith(base_city) or city in search_query:
                    search_query = region.lower()
                    break
                    
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://ubilling.net.ua/aerialalerts/") as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            states = data.get("states", {})
                            
                            found = False
                            for state, alert_data in states.items():
                                if search_query in state.lower():
                                    
                                   
                                    is_active = False
                                    if isinstance(alert_data, dict):
                                        is_active = alert_data.get('alertnow', False) or alert_data.get('status', False)
                                    else:
                                        
                                        is_active = str(alert_data).strip().lower() not in ['false', '0', 'null', 'none', '', 'no']
                                        
                                    status_icon = "🔴 <b>ТРИВОГА</b>" if is_active else "🟢 <b>Відбій / Немає тривоги</b>"
                                    
                                    if args.lower() != search_query and args.lower() not in state.lower():
                                        loc_display = f"{args.capitalize()} <i>({state})</i>"
                                    else:
                                        loc_display = state
                                        
                                    region_text = f"📍 <b>Локація:</b> {loc_display}\n🛡 <b>Статус:</b> {status_icon}\n➖➖➖➖➖➖➖➖➖➖\n"
                                    found = True
                                    break
                            
                            if not found:
                                region_text = f"📍 <b>Локація:</b> {args} <i>(не знайдено в базі)</i>\n➖➖➖➖➖➖➖➖➖➖\n"
            except Exception as e:
                region_text = f"📍 <b>Локація:</b> {args}\n❌ <i>Не вдалося перевірити статус: {e}</i>\n➖➖➖➖➖➖➖➖➖➖\n"

        try:
            messages = await message.client.get_messages("kpszsu", limit=2)
            reasons = []
            
            for msg in messages:
                if msg.text:
                    text = msg.text[:200] + ("..." if len(msg.text) > 200 else "")
                    reasons.append(f"🔸 <b>{text}</b>")
                    
            if reasons:
                reasons_text = "\n\n".join(reasons)
            else:
                reasons_text = "🔸 Немає свіжих текстових сповіщень."
                
        except Exception as e:
            reasons_text = f"❌ Помилка зчитування каналу ПС ЗСУ: {e}"

        text = (
            "🚨 <b>Повітряна ситуація:</b>\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            f"{region_text}"
            f"⚠️ <b>Останні сповіщення (причини):</b>\n\n{reasons_text}\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "<i>👇 Швидкі посилання для моніторингу:</i>"
        )

        buttons = [
            [
                {"text": "🗺 Мапа тривог", "url": "https://alerts.in.ua/"},
                {"text": "✈️ ПС ЗСУ", "url": "https://t.me/kpszsu"}
            ],
            [
                {"text": "📡 Радар / Монітор", "url": "https://t.me/monitorwarr"},
                {"text": "🍉 Ванек", "url": "https://t.me/vanek_nikolaev"}
            ]
        ]

        if hasattr(self, 'inline') and self.inline.init_complete:
            await self.inline.form(
                message=message,
                text=text,
                reply_markup=buttons
            )
        else:
            fallback_text = text + "\n\n<i>(💡 Щоб тут з'явилися кнопки, увімкніть inline-бота)</i>"
            await utils.answer(message, fallback_text)