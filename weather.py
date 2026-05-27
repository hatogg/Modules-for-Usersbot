# meta developer: @ttx44to
import aiohttp
from .. import loader, utils

@loader.tds
class WeatherMod(loader.Module):
    """Модуль для зручного та гарного відстеження погоди 🌤"""
    strings = {"name": "Weather"}

    @loader.command(uk_doc="<місто> - дізнатись погоду")
    async def wcmd(self, message):
        """<місто> - дізнатись погоду в місті"""
        city = utils.get_args_raw(message)
        
        if not city:
            city = "Kyiv"

        await utils.answer(message, "<i>⏳ Збираю метеодані...</i>")

        url = f"https://wttr.in/{city}?format=j1&lang=uk"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return await utils.answer(message, "<b>❌ Місто не знайдено або сервіс недоступний.</b>")
                    
                   
                    data = await response.json(content_type=None)
                    
            current = data['current_condition'][0]
            area = data['nearest_area'][0]['areaName'][0]['value']
            country = data['nearest_area'][0]['country'][0]['value']
            
            temp = current['temp_C']
            feels_like = current['FeelsLikeC']
            
            if 'lang_uk' in current:
                desc = current['lang_uk'][0]['value']
            else:
                desc = current['weatherDesc'][0]['value']
                
            humidity = current['humidity']
            wind = current['windspeedKmph']
            
            text = (
                f"🌍 <b>Погода: {area}, {country}</b>\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"🌡 <b>Температура:</b> {temp}°C <i>(Відчувається як {feels_like}°C)</i>\n"
                f"☁️ <b>Стан:</b> {desc.capitalize()}\n"
                f"💧 <b>Вологість:</b> {humidity}%\n"
                f"💨 <b>Швидкість вітру:</b> {wind} км/год\n"
                f"➖➖➖➖➖➖➖➖➖➖"
            )
            
            await utils.answer(message, text)
            
        except Exception as e:
            await utils.answer(message, f"<b>❌ Виникла помилка:</b> <code>{e}</code>")