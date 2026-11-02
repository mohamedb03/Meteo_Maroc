"""
Configuration du projet d'ingestion météo
Architecture des données - 4IASDG2 - EMSI
"""

import os

# ============================================================
#  CLE API OPENWEATHER
# ============================================================
# Définir la clé dans la variable d'environnement API_KEY.
API_KEY = os.getenv("API_KEY")

# Endpoint de l'API OpenWeather (current weather)
API_URL = "https://api.openweathermap.org/data/2.5/weather"

# ============================================================
#  VILLES MAROCAINES A SUIVRE
# ============================================================
# Format : nom utilisé pour les fichiers + nom envoyé à l'API
CITIES = [
    {"name": "Marrakech", "query": "Marrakech,MA"},
    {"name": "Tanger",    "query": "Tangier,MA"},
    {"name": "Dakhla",    "query": "Dakhla,MA"},
    {"name": "Essaouira", "query": "Essaouira,MA"},
]

# ============================================================
#  CHEMINS DE STOCKAGE (Data Lake local)
# ============================================================
BRONZE_PATH = "data/bronze/weather_raw"
SILVER_PATH = "data/silver/weather_clean"
GOLD_PATH   = "data/gold/weather_analytics"

# ============================================================
#  PARAMETRES API
# ============================================================
# units=metric -> température en Celsius
# lang=fr      -> descriptions météo en français
API_PARAMS_DEFAULT = {
    "units": "metric",
    "lang": "fr",
}