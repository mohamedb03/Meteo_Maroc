"""
Étape 2 - Silver Layer
======================
Lit tous les fichiers JSON du Bronze, extrait les champs utiles,
nettoie, type, ajoute les timestamps et sauvegarde en CSV propre.

Transformation Bronze → Silver :
- Lecture de tous les fichiers JSON Bronze
- Extraction des champs utiles uniquement
- Conversion des types (float, datetime)
- Nettoyage des valeurs nulles / incohérentes
- Ajout de event_timestamp et ingestion_timestamp
- Sauvegarde dans silver/weather_clean/weather_clean.csv
"""

import os
import json
import glob
import pandas as pd
from datetime import datetime
from config import BRONZE_PATH, SILVER_PATH


def list_bronze_files():
    """
    Liste tous les fichiers JSON du Bronze Layer
    en parcourant l'arborescence city=*/date=*/data_*h.json
    """
    pattern = os.path.join(BRONZE_PATH, "city=*", "date=*", "data_*.json")
    files = glob.glob(pattern)
    print(f"   ↪ {len(files)} fichiers JSON trouvés dans le Bronze")
    return files


def extract_city_from_path(filepath):
    """
    Extrait le nom de la ville depuis le chemin du fichier.
    Exemple : data/bronze/weather_raw/city=Marrakech/... → Marrakech
    """
    parts = filepath.split(os.sep)
    for part in parts:
        if part.startswith("city="):
            return part.replace("city=", "")
    return None


def parse_weather_json(filepath):
    """
    Lit un fichier JSON Bronze et extrait les champs utiles
    sous forme de dictionnaire plat (une ligne du futur DataFrame).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Récupération du nom de ville (depuis le chemin, plus fiable)
    city_name = extract_city_from_path(filepath)

    # Extraction des champs utiles depuis le JSON OpenWeather
    record = {
        # Identification
        "city": city_name,
        "country": raw.get("sys", {}).get("country"),

        # Coordonnées géographiques
        "latitude":  raw.get("coord", {}).get("lat"),
        "longitude": raw.get("coord", {}).get("lon"),

        # Températures (en Celsius car units=metric)
        "temperature":      raw.get("main", {}).get("temp"),
        "temperature_min":  raw.get("main", {}).get("temp_min"),
        "temperature_max":  raw.get("main", {}).get("temp_max"),
        "feels_like":       raw.get("main", {}).get("feels_like"),

        # Atmosphère
        "pressure": raw.get("main", {}).get("pressure"),
        "humidity": raw.get("main", {}).get("humidity"),

        # Vent
        "wind_speed":     raw.get("wind", {}).get("speed"),
        "wind_direction": raw.get("wind", {}).get("deg"),

        # Conditions météo (premier élément de la liste weather)
        "weather_main":        (raw.get("weather") or [{}])[0].get("main"),
        "weather_description": (raw.get("weather") or [{}])[0].get("description"),

        # Couverture nuageuse (en %)
        "clouds": raw.get("clouds", {}).get("all"),

        # Timestamps
        # event_timestamp = quand la mesure a été prise (champ dt de l'API)
        "event_timestamp": datetime.fromtimestamp(raw["dt"]) if "dt" in raw else None,
        # ingestion_timestamp = maintenant (quand on transforme)
        "ingestion_timestamp": datetime.now(),
    }

    return record


def clean_dataframe(df):
    """
    Nettoie le DataFrame :
    - Conversion des types numériques
    - Suppression des lignes avec température manquante
    - Ajout d'une colonne date (utile pour le Gold Layer)
    """
    print(f"   ↪ Nettoyage : {len(df)} lignes au départ")

    # Conversion explicite des types numériques (au cas où)
    numeric_cols = [
        "latitude", "longitude",
        "temperature", "temperature_min", "temperature_max", "feels_like",
        "pressure", "humidity",
        "wind_speed", "wind_direction", "clouds",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Conversion des timestamps en vrai datetime
    df["event_timestamp"]     = pd.to_datetime(df["event_timestamp"])
    df["ingestion_timestamp"] = pd.to_datetime(df["ingestion_timestamp"])

    # Suppression des lignes sans température (donnée critique)
    before = len(df)
    df = df.dropna(subset=["temperature", "city"])
    after = len(df)
    if before != after:
        print(f"   ↪ {before - after} ligne(s) supprimée(s) (température manquante)")

    # Ajout d'une colonne date (juste la date, pour les agrégations)
    df["date"] = df["event_timestamp"].dt.date

    print(f"   ↪ {len(df)} lignes après nettoyage")
    return df


def run_silver_transformation():
    """
    Pipeline complet Bronze → Silver
    """
    print("=" * 60)
    print(f"  TRANSFORMATION SILVER LAYER — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    # 1. Lister tous les fichiers Bronze
    files = list_bronze_files()
    if not files:
        print("   ❌ Aucun fichier dans le Bronze Layer. Lance ingestion.py d'abord.")
        return

    # 2. Parser chaque fichier JSON
    records = []
    for filepath in files:
        try:
            record = parse_weather_json(filepath)
            records.append(record)
        except Exception as e:
            print(f"   ⚠️  Erreur sur {filepath} : {e}")

    # 3. Construire un DataFrame pandas
    df = pd.DataFrame(records)
    print(f"   ↪ DataFrame construit : {df.shape[0]} lignes, {df.shape[1]} colonnes")

    # 4. Nettoyer
    df = clean_dataframe(df)

    # 5. Sauvegarder en CSV
    os.makedirs(SILVER_PATH, exist_ok=True)
    output_file = os.path.join(SILVER_PATH, "weather_clean.csv")
    df.to_csv(output_file, index=False, encoding="utf-8")

    print("=" * 60)
    print(f"   ✅ Silver Layer sauvegardé : {output_file}")
    print(f"   ✅ {len(df)} lignes × {len(df.columns)} colonnes")
    print("=" * 60)

    # Aperçu
    print("\n   Aperçu des 5 premières lignes :")
    print(df[["city", "temperature", "humidity", "wind_speed",
              "weather_main", "event_timestamp"]].head().to_string(index=False))


if __name__ == "__main__":
    run_silver_transformation()