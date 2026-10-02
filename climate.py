import requests
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "b436b8c10adb33045a6f95c09d8a384b"

def get_ip_location():
    try:
        data = requests.get("https://ipinfo.io/json", timeout=5).json()
        return data.get("city","").title()
    except:
        return None

def get_weather(city):
    # first try city name
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    data = requests.get(url).json()

    # if city name fails, use geocoding
    if "list" not in data:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
        geo = requests.get(geo_url).json()

        if geo:
            lat = geo[0]["lat"]
            lon = geo[0]["lon"]
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
            data = requests.get(url).json()

    return data


def parse_weather(data):
    days, temps, humidity, wind, rain, snow = [], [], [], [], [], []
    for item in data["list"][:8]:
        days.append(item["dt_txt"])
        temps.append(item["main"]["temp"])
        humidity.append(item["main"]["humidity"])
        wind.append(item["wind"]["speed"])
        rain.append(item.get("rain", {}).get("3h", 0))
        snow.append(item.get("snow", {}).get("3h", 0))
    return days, temps, humidity, wind, rain, snow

def generate_charts(days, temps, humidity, wind, rain, city):
    fig, axs = plt.subplots(2,2, figsize=(7,5))
    fig.suptitle(f"Climate for {city}")

    axs[0,0].plot(days, temps, marker="o")
    axs[0,0].set_title("Temperature")
    axs[0,0].tick_params(axis='x', rotation=45)

    axs[0,1].bar(days, humidity)
    axs[0,1].set_title("Humidity")
    axs[0,1].tick_params(axis='x', rotation=45)

    axs[1,0].bar(days, wind)
    axs[1,0].set_title("Wind Speed")
    axs[1,0].tick_params(axis='x', rotation=45)

    axs[1,1].bar(days, rain)
    axs[1,1].set_title("Rain")
    axs[1,1].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    return fig

def chart_single(values, labels, chart_type, title):
    plt.figure(figsize=(5,4))

    # remove NaN values
    clean_values = [0 if (v is None or (isinstance(v, float) and pd.isna(v))) else v for v in values]

    if chart_type=="bar":
        plt.bar(labels, clean_values)

    elif chart_type=="pie":
        # avoid pie chart crash if all values are zero
        if sum(clean_values) == 0:
            plt.text(0.5, 0.5, "No rain data available", ha="center", va="center")
        else:
            plt.pie(clean_values, labels=labels, autopct="%1.1f%%")

    elif chart_type=="hist":
        plt.hist(clean_values, bins=5)

    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return plt.gcf()


def make_table(days, temps, humidity, wind, rain):
    return pd.DataFrame({
        "Time": days,
        "Temp °C": temps,
        "Humidity %": humidity,
        "Wind m/s": wind,
        "Rain mm": rain
    })

def clothing_advice(temp, rain, snow):
    if snow > 0:
        return "Heavy winter clothing is recommended due to snowfall."
    if rain > 2:
        return "Wear waterproof clothing or carry an umbrella."
    if temp < 10:
        return "Warm clothes and jackets are recommended."
    if temp < 20:
        return "Light sweater or full sleeves are suitable."
    return "Light, breathable clothing is suitable."

def travel_advice(wind, rain, snow):
    if snow > 1:
        return "Travel may be unsafe due to snowfall."
    if rain > 5 or wind > 8:
        return "Travel may be risky due to rain or wind."
    return "Weather conditions look safe for travel."

def get_local_time(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    data = requests.get(url).json()
    offset = data["timezone"]
    utc = datetime.utcnow()
    local = utc + timedelta(seconds=offset)
    return local.strftime("%I:%M %p on %d %b %Y")