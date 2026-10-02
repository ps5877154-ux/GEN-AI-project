import os.environ.pop("SSL_CERT_FILE", None)

import streamlit as st
import speech_recognition as sr
import re
import climate
import ollama
import requests
from transformers import pipeline

classifier = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli",
                      device=-1)

st.set_page_config(layout="wide")

top1, top2, top3 = st.columns([1,3,1])
with top2:
    st.image("Atmos.png", width=600)
    st.write("Atmos uses OpenWeather + Ollama + HuggingFace + Regex for accurate weather prediction")

if "chat" not in st.session_state:
    st.session_state.chat=[]
if "reports" not in st.session_state:
    st.session_state.reports={}
if "last_fig" not in st.session_state:
    st.session_state.last_fig=None
if "last_table" not in st.session_state:
    st.session_state.last_table=None
if "show_report" not in st.session_state:
    st.session_state.show_report=False

left,center,right = st.columns([1,2,1])

with left:
    st.subheader("📊 Saved Reports")
    for city in st.session_state.reports:
        if st.button(city):
            st.pyplot(st.session_state.reports[city])

with right:
    st.subheader("💬 Chat History")
    chatbox=st.container(height=400)
    for m in st.session_state.chat[-12:]:
        chatbox.write(m)

with center:
    colA,colB = st.columns([10,2])
    with colA:
        user_input = st.text_input("Ask about weather or climate...")
    with colB:
        mic = st.button("🎙️")

    if mic:
        r=sr.Recognizer()
        with sr.Microphone() as source:
            audio=r.listen(source, phrase_time_limit=4)
        try:
            user_input=r.recognize_google(audio)
            st.success(f"Recognized: {user_input}")
        except:
            st.error("Could not understand")

    output_area = st.container()

#CITY EXTRACTION 
def extract_city(text):
    raw = text
    text = text.lower().strip()

    # current location
    if any(k in text for k in [
        "my location","current location","my place","here",
        "my current location's","where i am","my current location","my location's"
    ]):
        return climate.get_ip_location()

    # abbreviation support
    abbreviations = {
        "ny": "New York",
        "nyc": "New York",
        "la": "Los Angeles",
        "sf": "San Francisco",
        "del": "Delhi",
        "blr": "Bangalore",
        "bng": "Bangalore",
        "mum": "Mumbai",
        "bom": "Mumbai",
        "hyd": "Hyderabad",
        "kol": "Kolkata",
        "ccu": "Kolkata",
        "maa": "Chennai",
        "madras": "Chennai",
        "jk": "Jammu And Kashmir",
        "lv": "Las Vegas"
    }

    words = re.findall(r"[a-zA-Z]+", text)
    for w in words:
        if w in abbreviations:
            return abbreviations[w]

    # handles "stay in X", "living in X", "if I am in X"
    m0 = re.findall(r"(?:stay|staying|live|living|am|be|being)\s+in\s+([a-zA-Z ]+)", text)
    if m0:
        city = m0[-1]
        city = re.sub(r"\b(city|place|today|tomorrow|now|time|temperature|temp|weather|forecast)\b", "", city)
        return city.strip().title()
        
                                        
    # handles "at haldia", "at london", "at paris"
    m_at = re.findall(r"(?:at|on)\s+([a-zA-Z ]+)", text)
    if m_at:
        city = m_at[-1]
        city = re.sub(r"\b(city|place|today|tomorrow|now|time|temperature|temp|weather|forecast)\b", "", city)
        return city.strip().title()

        
        
        #handles "bar graph of wind for X"
    m_graph = re.findall(r"(?:of)\s+(?:wind|rain|temperature|temp|humidity)\s+(?:for|in)\s+([a-zA-Z ]+)", text)
    if m_graph:
        return m_graph[-1].strip().title()

    #handles "what is the time in X", "what is the humidity in X", etc.
    m_time = re.findall(r"(?:time|temperature|temp|humidity|rain|snow|wind)\s+in\s+([a-zA-Z ]+)", text)
    if m_time:
        city = m_time[-1]
        city = re.sub(r"\b(city|place|today|tomorrow|now|current)\b", "", city)
        return city.strip().title()


    # patterns: "in london", "at paris", "around tokyo", "near berlin"
    m = re.findall(r"(?:in|at|for|around|near|over|of)\s+([a-zA-Z ]+)", text)
    if m:
        city = m[-1]
        city = re.sub(
            r"\b(today|tomorrow|now|rain|what|is|near|around|snow|humidity|wind|time|temperature|temp|forecast|weather|climate|place|city)\b",
            "",
            city
        )
        return city.strip().title()

    # patterns: "london temperature", "paris rain", "tokyo humidity"
    m2 = re.findall(
        r"([a-zA-Z ]+?)\s+(?:temperature|temp|humidity|weather|climate|rain|snow|wind|time|forecast)",
        text
    )
    if m2:
        return m2[-1].strip().title()

    # patterns: "temperature of london"
    m3 = re.findall(r"(?:of)\s+([a-zA-Z ]+)", text)
    if m3:
        return m3[-1].strip().title()

    # fallback: longest non-keyword word
    blacklist = [
        "what","is","the","will","it","rain","snow","humidity","wind","time",
        "temperature","temp","today","tomorrow","now","weather","forecast",
        "climate","show","me","that","give","at","if","stay","staying","live","living","place","city"
    ]
    candidates = [w for w in words if w.lower() not in blacklist]
    if candidates:
        return candidates[-1].title()

    return None

# INTENT
def classify_intent(text):
    t=text.lower()
        # chart intent 
    if "bar" in t or "bar chart" in t or "bar graph" in t: return "bar chart"
    if "pie" in t or "pie chart" in t: return "pie chart"
    if "hist" in t or "histogram" in t: return "histogram"

    if "humidity" in t: return "humidity"
    if "rain" in t: return "rain"
    if "snow" in t: return "snow"
    if "wind" in t or "wind speed" in t: return "wind"
    if "temperature" in t or "temp" in t: return "temperature"
    if "time" in t: return "time"

    if "wear" in t or "cloths" in t: return "clothing"
    if "travel" in t or "travelling" in t: return "travel"
    if "full" in t and "report" in t: return "full report"
    return classifier(text, ["time","climate","around","weather","near","in","is","the","do","you","expect","expected","boy","girl","baby","with","wanted","at","to","provide","him","her","them","wants","who","lives","in","asked","me","myself","will","shall","my teacher","sir","my sir","ma'am","my ma'am","uncle","aunty","boy friend","girl friend","bf","gf","my ancesters","brother","sister","mother","mom","dad","father","grand parents","daddy","should","i","he","she","they","temperature","rain","snow","humidity","wind","full report","clothing","travel","bar chart","pie chart","histogram"])["labels"][0]

    #  Ollama smart response enhancer
def ollama_enhance(reply_text):
    try:
        response = ollama.chat(
            model="phi3:mini",
            messages=[
                {"role": "system", "content": "You are a helpful weather assistant. Rewrite the reply in a natural and friendly way."},
                {"role": "user", "content": reply_text}
            ]
        )
        return response["message"]["content"]
    except:
        return reply_text

if user_input:
    
    st.session_state.show_report=False
    st.session_state.last_fig=None
    st.session_state.last_table=None

    st.session_state.chat.append("You: "+user_input)
    reply=""
    # Greetings and Self Introduction
    greet_text = user_input.lower()

    if any(k in greet_text for k in ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]):
        reply = "Hello! 👋 I am Atmos, your AI-powered climate assistant. You can ask me about weather, temperature, rain, humidity, wind, time, or even request charts and full climate reports for any city."

    elif any(k in greet_text for k in ["hey atmos introduce yourself","introduce yourself", "introduce your self", "who are you", "what are you", "what is atmos", "about you"]):
        reply = (
            "Hello! I am Atmos 🌍, an AI-based climate assistant. "
            "I understand natural language questions, extract locations intelligently, "
            "fetch real-time data from the OpenWeather API, and present results using charts and tables. "
            "I can provide temperature, rain, humidity, wind, time, clothing advice, and travel advice. "
            "I also use AI models and pattern recognition to understand user intent and generate friendly responses."
        )

    elif any(k in greet_text for k in ["good job", "nice", "great", "awesome", "well done", "thank you", "thanks"]):
        reply = "Thank you so much! 😊 I’m glad I could help. Feel free to ask me about the weather or request charts for any city."

    else:
        city = extract_city(user_input)
        tomorrow = "tomorrow" in user_input.lower()

        #reject country-only inputs
        if city.lower() in ["india", "mexico", "usa", "uk", "china", "japan", "france", "germany", "canada"]:
            reply = "Please specify a city in " + city + " (for example: 'rain in Mexico City')."

        elif not city:
            reply="Please mention a city or say my location."

        if not city:
            reply="Please mention a city or say my location."
        else:
            data = climate.get_weather(city)
        
            # universal fallback using geocoding
            if "list" not in data:
                try:
                    geo = requests.get(
                        f"https://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={climate.API_KEY}"
                    ).json()
                    if geo:
                        lat = geo[0]["lat"]
                        lon = geo[0]["lon"]
                        data = requests.get(
                            f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={climate.API_KEY}&units=metric"
                        ).json()
                except:
                    pass
        
            if "list" not in data:
                reply="City not found."
            else:
                intent=classify_intent(user_input)
                days,temps,hum,wind,rain,snow = climate.parse_weather(data)

                idx = 2 if tomorrow else 0

                if intent=="time":
                    reply=f"The current time in {city} is {climate.get_local_time(city)}"

                elif intent=="temperature":
                    reply=f"The temperature in {city} is {temps[idx]}°C"

                elif intent=="rain":
                    reply=("Yes, rain is likely in "+city+" because precipitation is forecast."
                           if rain[idx]>0 else
                           "No, rain is unlikely in "+city+" as skies are expected to remain dry.")

                elif intent=="snow":
                    reply=("Yes, snow is possible in "+city+" due to low temperatures."
                           if snow[idx]>0 else
                           "No, snow is unlikely in "+city+" since temperatures are above freezing.")

                elif intent=="humidity":
                    reply=f"Humidity in {city} is {hum[idx]}%"

                elif intent=="wind":
                    reply=f"Wind speed in {city} is {wind[idx]} m/s"

                elif intent=="clothing":
                    reply=climate.clothing_advice(temps[idx],rain[idx],snow[idx])

                elif intent=="travel":
                    reply=climate.travel_advice(wind[idx],rain[idx],snow[idx])

                elif intent=="full report":
                    fig=climate.generate_charts(days,temps,hum,wind,rain,city)
                    table=climate.make_table(days,temps,hum,wind,rain)
                    st.session_state.reports[city]=fig
                    st.session_state.last_fig=fig
                    st.session_state.last_table=table
                    st.session_state.show_report=True
                    reply=f"Full climate report for {city} generated."

                elif intent=="bar chart":
                    if "wind" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(wind, days, "bar", "Wind Speed")
                    elif "rain" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(rain, days, "bar", "Rain")
                    elif "temp" in user_input.lower() or "temperature" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(temps, days, "bar", "Temperature")
                    else:
                        st.session_state.last_fig = climate.chart_single(hum, days, "bar", "Humidity")
                    reply="Bar chart/graph generated."

                elif intent=="pie chart":
                    if "wind" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(wind, days, "pie", "Wind Speed")
                    elif "rain" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(rain, days, "pie", "Rain")
                    elif "temp" in user_input.lower() or "temperature" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(temps, days, "pie", "Temperature")
                    else:
                        st.session_state.last_fig = climate.chart_single(hum, days, "pie", "Humidity")
                    reply = "Pie chart generated."

                elif intent=="histogram":
                    if "wind" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(wind, days, "hist", "Wind Speed Distribution")
                    elif "rain" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(rain, days, "hist", "Rain Distribution")
                    elif "humidity" in user_input.lower():
                        st.session_state.last_fig = climate.chart_single(hum, days, "hist", "Humidity Distribution")
                    else:
                        st.session_state.last_fig = climate.chart_single(temps, days, "hist", "Temperature Distribution")
                    reply = "Histogram generated."

                else:
                    reply=f"The weather in {city} is {temps[idx]}°C with {hum[idx]}% humidity."

    reply = ollama_enhance(reply)
    st.session_state.chat.append("Atmos: "+reply)

with output_area:
    if st.session_state.chat:
        st.success(st.session_state.chat[-1].replace("Atmos: ",""))
        st.info("Try: Will it rain tomorrow in Bangaluru | What should I wear in Delhi | Humidity in Tokyo | Time in New York")

    if st.session_state.show_report:
        st.subheader("🧥 Clothing Advice")
        st.success(climate.clothing_advice(temps[0],rain[0],snow[0]))

        st.subheader("✈ Travel Advice")
        st.warning(climate.travel_advice(wind[0],rain[0],snow[0]))

        if st.button("❌ Close Report"):
            st.session_state.show_report=False
            st.session_state.last_fig = None
            st.session_state.last_table = None
            
    if st.session_state.last_fig:
        st.pyplot(st.session_state.last_fig)
    if st.session_state.last_table is not None:
        st.dataframe(st.session_state.last_table)