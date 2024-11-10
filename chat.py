import streamlit as st
import requests
from transformers import pipeline
import torch
from neo4j import GraphDatabase
from datetime import datetime

# User Data with Passwords, Preferences, and Chat History
user_data = {
    "romia": {"password": "2468", "preferences": {"interests": "culture, food", "budget": 1000}, "chat_history": []},
    "dhruv": {"password": "1357", "preferences": {"interests": "adventure, shopping", "budget": 2000}, "chat_history": []},
    "manju": {"password": "0987", "preferences": {"interests": "nature, wildlife", "budget": 1500}, "chat_history": []}
}

# Initialize session state for login and preferences
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.preferences = {}
    st.session_state.chat_history = []

# Neo4j Memory Agent Class
class MemoryAgent:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_or_update_user(self, user_id, preferences):
        # Create or update user node with preferences in Neo4j graph database
        with self.driver.session() as session:
            session.write_transaction(self._create_or_update_user_node, user_id, preferences)

    @staticmethod
    def _create_or_update_user_node(tx, user_id, preferences):
        query = """
        MERGE (u:User {id: $user_id})
        SET u.preferences = $preferences, u.last_updated = datetime()
        """
        tx.run(query, user_id=user_id, preferences=preferences)

    def fetch_user_data(self, user_id):
        # Fetch all entities and relationships linked to the user
        with self.driver.session() as session:
            return session.read_transaction(self._fetch_user_data, user_id)

    @staticmethod
    def _fetch_user_data(tx, user_id):
        query = """
        MATCH (u:User {id: $user_id})-[r]->(e)
        RETURN type(r) AS relationship, e.name AS entity
        """
        result = tx.run(query, user_id=user_id)
        return [{"relationship": record["relationship"], "entity": record["entity"]} for record in result]

# Weather Agent Class for Fetching Weather Data
class WeatherAgent:
    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_weather(self, city):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return {'description': data['weather'][0]['description'], 'temperature': data['main']['temp'], 'humidity': data['main']['humidity']}
        else:
            return None

# News Agent Class for Fetching News Data
class NewsAgent:
    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_news(self, city, date):
        url = f"https://newsapi.org/v2/everything?q={city}&from={date}&to={date}&sortBy=popularity&apiKey={self.api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['articles'][:3] if data['articles'] else None
        return None

# Itinerary Agent Class for Generating Itineraries
class ItineraryAgent:
    def __init__(self):
        # Initialize Hugging Face pipeline for text generation with NeoGPT model
        self.generator = pipeline("text-generation", model="NeoGPT", device=0 if torch.cuda.is_available() else -1)

    def generate_itinerary(self, preferences, weather_info, news_info, chat_history, graph_info):
        # Format graph info as context for prompt
        graph_context = "\n".join([f"{rel['relationship']}: {rel['entity']}" for rel in graph_info])

        # Prepare prompt with user preferences, weather, news, chat history, and graph context
        prompt = f"""
        You are a tour planner. Use the user's past interactions, preferences, and graph data to create a one-day itinerary for {preferences['city']} on {preferences['date']}.
        
        Graph data:
        {graph_context}

        Previous interactions:
        {" ".join(chat_history) if chat_history else "No previous interactions available."}

        User preferences:
        - Start time: {preferences['timing']}
        - Budget: ₹{preferences['budget']}
        - Interests: {preferences['interests']}
        - Starting point: {preferences['start_location']}

        Weather in {preferences['city']}:
        - {weather_info['description'].capitalize()}
        - Temperature: {weather_info['temperature']}°C
        - Humidity: {weather_info['humidity']}%

        News in {preferences['city']}:
        {" ".join([f"- {article['title']} ({article['source']['name']})" for article in news_info]) if news_info else "No significant news updates for this day."}

        Suggest a list of places to visit, the order, transportation options, time allocations, and a lunch recommendation.
        """
        
        response = self.generator(prompt, max_length=1024, temperature=0.7, num_return_sequences=1)
        return response[0]['generated_text']

# Streamlit App for user interaction
def main():
    st.title("One-Day Tour Planner with Login 🗺️")
    st.write("Log in to personalize your experience and get tailored recommendations based on past interactions and graph data.")

    if not st.session_state.logged_in:
        # Login UI
        with st.sidebar:
            st.subheader("Login")
            user_id = st.text_input("User ID")
            password = st.text_input("Password", type="password")
            login_button = st.button("Login")

        if login_button:
            if user_id in user_data and user_data[user_id]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.preferences = user_data[user_id].get("preferences", {})
                st.session_state.chat_history = user_data[user_id].get("chat_history", [])
                st.success(f"Welcome back, {user_id}!")
            else:
                st.error("Invalid credentials. Please try again.")
    else:
        user_id = st.session_state.user_id
        preferences = st.session_state.preferences
        chat_history = st.session_state.chat_history

        # UI for logged-in user
        st.sidebar.write(f"Logged in as: **{user_id}**")
        logout = st.sidebar.button("Logout")
        if logout:
            st.session_state.logged_in = False

        # Collect trip planning inputs from user
        city = st.text_input("Which city are you visiting?", value=preferences.get("city", ""))
        date = st.date_input("What date will you be visiting?")
        timing = st.text_input("What time do you plan to start your tour?", value=preferences.get("timing", "9:00 AM"))
        interests = st.text_input("What type of experience are you looking for?", value=preferences.get("interests", ""))
        budget = st.number_input("What is your budget for the day (in INR)?", min_value=0, value=preferences.get("budget", 1000))
        start_location = st.text_input("Where would you like to start your day?", value=preferences.get("start_location", "Hotel"))

        if st.button("Generate Itinerary"):
            # Update user preferences and initialize agents
            preferences = {
                "city": city,
                "date": date.strftime("%Y-%m-%d"),
                "timing": timing,
                "interests": interests,
                "budget": budget,
                "start_location": start_location
            }
            st.session_state.preferences = preferences
            user_data[user_id]["preferences"] = preferences

            weather_agent = WeatherAgent(api_key="API_KEY")
            news_agent = NewsAgent(api_key="API_KEY")
            memory_agent = MemoryAgent("bolt://localhost:7687", "neo4j", "password")
            memory_agent.create_or_update_user(user_id, preferences)

            itinerary_agent = ItineraryAgent()

            # Fetch weather, news, and graph data
            weather_info = weather_agent.fetch_weather(city)
            news_info = news_agent.fetch_news(city, preferences["date"])
            graph_info = memory_agent.fetch_user_data(user_id)

            if weather_info:
                itinerary = itinerary_agent.generate_itinerary(preferences, weather_info, news_info, chat_history, graph_info)
                st.session_state.chat_history.append(itinerary)
                user_data[user_id]["chat_history"] = st.session_state.chat_history
                st.subheader("Your One-Day Tour Itinerary")
                st.write(itinerary)
            else:
                st.error("Unable to fetch weather data. Please try again.")

if __name__ == "__main__":
    main()
