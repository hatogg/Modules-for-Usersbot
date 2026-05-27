# meta developer: @your_username
import aiohttp
import re
from .. import loader, utils

@loader.tds
class AirAlertsMod(loader.Module):
    """Модуль для відстеження тривог по містах/областях та їх причин 🚨"""
    strings = {"name": "AirAlerts"}

    CITY_TO_REGION = {
        "луцьк": "Волинська", "ужгород": "Закарпатська", "мукачево": "Закарпатська",
        "івано-франківськ": "Івано-Франківська", "кропивницький": "Кіровоградська",
        "олександрія": "Кіровоградська", "дніпро": "Дніпропетровська", "кривий ріг": "Дніпропетровська",
        "кам'янське": "Дніпропетровська", "маріуполь": "Донецька", "краматорськ": "Донецька",
        "донецьк": "Донецька", "мелітополь": "Запорізька", "запоріжжя": "Запорізька",
        "кременчук": "Полтавська", "полтава": "Полтавська", "біла церква": "Київська",
        "бровари": "Київська", "київ": "м. Київ", "умань": "Черкаська",
        "черкаси": "Черкаська", "подільськ": "Одеська", "ізмаїл": "Одеська",
        "одеса": "Одеська", "рівне": "Рівненська", "тернопіль": "Тернопільська",
        "хмельницький": "Хмельницька", "кам'янець-подільський": "Хмельницька",
        "вінниця": "Вінницька", "житомир": "Житомирська", "чернігів": "Чернігівська",
        "суми": "Сумська", "харків": "Харківська", "миколаїв": "Миколаївська",
        "херсон": "Херсонська", "чернівці": "Чернівецька", "луганськ": "Луганська",
        "львів": "Львівська", "крим": "Крим"
    }

    @loader.command(uk_doc="[місто/область] - дізнатись статус тривоги та причину")
    async def alertcmd(self, message):
        """[місто/область] - перевірити тривогу за локацією та дізнатися причину"""
        args = utils.get_args_raw(message)
        await utils.answer(message, "<i>⏳ Оновлюю дані радару...</i>")
        
        region_text = ""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://ubilling.net.ua/aerialalerts/") as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        states = data.get("states", {})
                        
                        if args:
                            search_query = args.lower()
                            for city, region in self.CITY_TO_REGION.items():
                                base_city = city[:-1] if len(city) > 4 else city
                                if search_query.startswith(base_city) or city in search_query:
                                    search_query = region.lower()
                                    break
                                    
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
                                        safe_args = args.capitalize().replace("<", "").replace(">", "")
                                        loc_display = f"{safe_args} <i>({state})</i>"
                                    else:
                                        loc_display = state
                                        
                                    region_text = f"📍 <b>Локація:</b> {loc_display}\n🛡 <b>Статус:</b> {status_icon}\n➖➖➖➖➖➖➖➖➖➖\n"
                                    found = True
                                    break
                            
                            if not found:
                                safe_args = args.replace("<", "").replace(">", "")
                                region_text = f"📍 <b>Локація:</b> {safe_args} <i>(не знайдено в базі)</i>\n➖➖➖➖➖➖➖➖➖➖\n"
                                
                        else:
                            active_regions = []
                            for state, alert_data in states.items():
                                is_active = False
                                if isinstance(alert_data, dict):
                                    is_active = alert_data.get('alertnow', False) or alert_data.get('status', False)
                                else:
                                    is_active = str(alert_data).strip().lower() not in ['false', '0', 'null', 'none', '', 'no']
                                
                                if is_active:
                                    clean_name = state.replace(" область", "")
                                    active_regions.append(clean_name)
                                    
                            if active_regions:
                                active_list = ", ".join(active_regions)
                                region_text = f"🔴 <b>Зараз тривога:</b> {active_list}\n➖➖➖➖➖➖➖➖➖➖\n"
                            else:
                                region_text = f"🟢 <b>По Україні зараз чисто, тривог немає.</b>\n➖➖➖➖➖➖➖➖➖➖\n"
        except Exception as e:
            region_text = f"❌ <i>Не вдалося підключитися до радару: {e}</i>\n➖➖➖➖➖➖➖➖➖➖\n"

        try:
            messages = await message.client.get_messages("kpszsu", limit=2)
            reasons = []
            
            for msg in messages:
                raw_text = getattr(msg, 'raw_text', msg.text)
                if raw_text: