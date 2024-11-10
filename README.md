# One-Day Tour Planner with Login

## Overview
This project is a personalized one-day tour planning application that leverages Streamlit, Neo4j, and Hugging Face Transformers (NeoGPT model) to provide tailored itineraries based on user preferences, past interactions, weather, news, and entity-relationship data stored in a Neo4j graph database.

## Features
- **User Login**: Enables personalized itinerary creation with user-specific preferences and past interactions.
- **Agents** : Itinerary Agent, Mmeory Agent, Weather agent, News agent
- **Memory and Graph Data**: Stores and retrieves user preferences and historical data with Neo4j, enhancing personalization.
- **External Data**: Fetches real-time weather and news for the itinerary.
- **AI-Generated Itineraries**: Uses a NeoGPT model for generating the itinerary based on user data and context.

## Requirements
- Python 3.8+
- [Neo4j](https://neo4j.com/) (configured for local access)
- [OpenWeather API](https://openweathermap.org/) and [News API](https://newsapi.org/) keys
