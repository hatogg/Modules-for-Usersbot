import requests
from datetime import datetime
from .. import loader, utils

# Модуль створено X44To для юзербота Hikka

class WeatherModule(loader.Module):
    """Показує погоду в зазначеному місті та прогноз на 5 днів. Створено X44To"""
    strings = {
        "name": "Погода",
        "no_city": "❗ Будь ласка, вкажіть назву міста.",
        "fetch_error": "❗ Не вдалося отримати дані про погоду. Перевірте назву міста та спробуйте ще раз."
    }

    # Словник для перекладу описів погоди
    weather_translations = {
        "clear sky": "ясно",
        "few clouds": "невелика хмарність",
        "scattered clouds": "розсіяні хмари",
        "broken clouds": "хмарно з проясненнями",
        "overcast clouds": "похмуро",
        "light rain": "легкий дощ",
        "moderate rain": "помірний дощ",
        "heavy intensity rain": "сильний дощ",
        "very heavy rain": "дуже сильний дощ",
        "extreme rain": "екстремальний дощ",
        "freezing rain": "крижаний дощ",
        "light intensity shower rain": "легкий зливовий дощ",
        "shower rain": "зливовий дощ",
        "heavy intensity shower rain": "сильний зливовий дощ",
        "ragged shower rain": "нерівномірний зливовий дощ",
        "light snow": "легкий сніг",
        "snow": "сніг",
        "heavy snow": "сильний сніг",
        "sleet": "мокрий сніг",
        "light shower sleet": "легкий мокрий сніг",
        "shower sleet": "мокрий сніг з дощем",
        "light rain and snow": "легкий дощ зі снігом",
        "rain and snow": "дощ зі снігом",
        "light shower snow": "легкий снігопад",
        "shower snow": "снігопад",
        "heavy shower snow": "сильний снігопад",
        "mist": "туман",
        "smoke": "дим",
        "haze": "серпанок",
        "sand/dust whirls": "піщані/пилові вихори",
        "fog": "туман",
        "sand": "пісок",
        "dust": "пил",
        "volcanic ash": "вулканічний попіл",
        "squalls": "шквали",
        "tornado": "торнадо",
        "thunderstorm with light rain": "гроза з легким дощем",
        "thunderstorm with rain": "гроза з дощем",
        "thunderstorm with heavy rain": "гроза з сильним дощем",
        "light thunderstorm": "легка гроза",
        "thunderstorm": "гроза",
        "heavy thunderstorm": "сильна гроза",
        "ragged thunderstorm": "нерівномірна гроза",
        "thunderstorm with light drizzle": "гроза з легкою мрякою",
        "thunderstorm with drizzle": "гроза з мрякою",
        "thunderstorm with heavy drizzle": "гроза з сильною мрякою",
        "light intensity drizzle": "легка мряка",
        "drizzle": "мряка",
        "heavy intensity drizzle": "сильна мряка",
        "light intensity drizzle rain": "легка мряка з дощем",
        "drizzle rain": "мряка з дощем",
        "heavy intensity drizzle rain": "сильна мряка з дощем",
        "shower rain and drizzle": "зливова мряка з дощем",
        "heavy shower rain and drizzle": "сильна зливова мряка з дощем",
        "shower drizzle": "зливова мряка",
        # Додайте інші описи за потреби
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "a02c91969383c2bd1cf56a292977f67b", lambda m: "Ваш API-ключ від OpenWeatherMap",
            "UNITS", "metric", lambda m: "Одиниці виміру: metric (Celsius) або imperial (Fahrenheit)"
        )

    def get_weather(self, city):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.config['API_KEY']}&units={self.config['UNITS']}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            description = data["weather"][0]["description"]
            # Переклад опису погоди
            translated_description = self.weather_translations.get(description.lower(), description)
            temp_unit = "°C" if self.config['UNITS'] == "metric" else "°F"
            wind_unit = "м/с" if self.config['UNITS'] == "metric" else "миль/год"
            weather = {
                "city": data["name"],
                "temperature": data["main"]["temp"],
                "description": translated_description,
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "pressure": data["main"]["pressure"],
                "visibility": data.get("visibility", "Н/Д") / 1000 if data.get("visibility") else "Н/Д",
                "temp_unit": temp_unit,
                "wind_unit": wind_unit
            }
            return weather
        else:
            return None

    def get_forecast(self, city):
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={self.config['API_KEY']}&units={self.config['UNITS']}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            forecast = []
            temp_unit = "°C" if self.config['UNITS'] == "metric" else "°F"
            for item in data["list"][::8]:  # Кожні 24 години (8 * 3 години = 24)
                date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                description = item["weather"][0]["description"]
                translated_description = self.weather_translations.get(description.lower(), description)
                forecast.append({
                    "date": date,
                    "temperature": item["main"]["temp"],
                    "description": translated_description,
                    "temp_unit": temp_unit
                })
            return forecast
        else:
            return None

    @loader.command()
    async def weathercmd(self, message):
        """Показує поточну погоду в зазначеному місті. Створено X44To"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_city"])
            return

        city = args
        weather = self.get_weather(city)

        if weather:
            reply = (
                f"🌆 Погода в {weather['city']}:\n"
                f"🌡️ Температура: {weather['temperature']}{weather['temp_unit']}\n"
                f"🌤️ Опис: {weather['description']}\n"
                f"💧 Вологість: {weather['humidity']}%\n"
                f"💨 Швидкість вітру: {weather['wind_speed']} {weather['wind_unit']}\n"
                f"🕛 Тиск: {weather['pressure']} гПа\n"
                f"👀 Видимість: {weather['visibility']} км"
            )
        else:
            reply = self.strings["fetch_error"]

        await utils.answer(message, reply)

    @loader.command()
    async def forecastcmd(self, message):
        """Показує прогноз погоди на 5 днів у зазначеному місті. Створено X44To"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_city"])
            return

        city = args
        forecast = self.get_forecast(city)

        if forecast:
            reply = f"📅 Прогноз погоди в {city} на 5 днів:\n\n"
            for day in forecast:
                reply += (
                    f"📆 {day['date']}:\n"
                    f"🌡️ Температура: {day['temperature']}{day['temp_unit']}\n"
                    f"🌤️ Опис: {day['description']}\n\n"
                )
        else:
            reply = self.strings["fetch_error"]

        await utils.answer(message, reply)