"""
Étape 1 - Bronze Layer
======================
Script d'ingestion des données météo brutes depuis l'API OpenWeather.
Les données sont stockées SANS modification (principe du Bronze Layer).

Structure de stockage :
    data/bronze/weather_raw/
        city=Marrakech/date=2026-05-10/data_14h.json
        city=Tanger/date=2026-05-10/data_14h.json
        ...
"""

import os
import json
import requests
from datetime import datetime
from config import API_KEY, API_URL, CITIES, BRONZE_PATH, API_PARAMS_DEFAULT


def fetch_weather(city):
    """
    Appelle l'API OpenWeather pour une ville donnée.
    Retourne le JSON brut tel quel.
    """
    if not API_KEY:
        raise RuntimeError(
            "La variable d'environnement API_KEY est requise pour l'ingestion."
        )

    params = {
        "q": city["query"],
        "appid": API_KEY,
        **API_PARAMS_DEFAULT,
    }

    print(f"   ↪ Appel API pour {city['name']}...")
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()  # Lève une exception si erreur HTTP

    return response.json()


def save_to_bronze(city_name, data):
    """
    Sauvegarde le JSON brut dans le Bronze Layer.
    Organisation : city=<ville>/date=<YYYY-MM-DD>/data_<HH>h.json
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour_str = now.strftime("%Hh")

    # Construction du chemin (style "partitionnement Hive" comme dans le sujet)
    folder = os.path.join(
        BRONZE_PATH,
        f"city={city_name}",
        f"date={date_str}",
    )
    os.makedirs(folder, exist_ok=True)

    filename = f"data_{hour_str}.json"
    filepath = os.path.join(folder, filename)

    # Écriture du JSON sans transformation
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def run_ingestion():
    """
    Boucle principale d'ingestion :
    pour chaque ville on appelle l'API et on sauvegarde le résultat.
    """
    print("=" * 60)
    print(f"  INGESTION BRONZE LAYER — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    success_count = 0
    error_count = 0

    for city in CITIES:
        try:
            raw_data = fetch_weather(city)
            saved_path = save_to_bronze(city["name"], raw_data)
            print(f"   ✅ {city['name']:12s} → {saved_path}")
            success_count += 1
        except requests.exceptions.HTTPError as e:
            print(f"   ❌ {city['name']:12s} → erreur HTTP : {e}")
            error_count += 1
        except Exception as e:
            print(f"   ❌ {city['name']:12s} → erreur : {e}")
            error_count += 1

    print("=" * 60)
    print(f"  Résumé : {success_count} succès, {error_count} échecs")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()