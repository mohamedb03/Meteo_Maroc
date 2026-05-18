"""
Étape 3 - Gold Layer (version corrigée)
========================================
- Garde uniquement la dernière mesure par ville (event_timestamp max)
- Génère des rangs uniques (pas d'ex aequo)
"""

import os
import pandas as pd
from datetime import datetime
from config import SILVER_PATH, GOLD_PATH


# ============================================================
#  PARAMETRES DU SCORE METEO
# ============================================================
TEMP_IDEAL_MIN = 22.0
TEMP_IDEAL_MAX = 26.0
HUM_IDEAL_MIN  = 40.0
HUM_IDEAL_MAX  = 60.0
WIND_IDEAL_MAX = 5.0

WEIGHT_TEMP   = 0.40
WEIGHT_HUM    = 0.20
WEIGHT_WIND   = 0.20
WEIGHT_SKY    = 0.20

SKY_BONUS = {
    "Clear":         100,
    "Clouds":         60,
    "Rain":           20,
    "Drizzle":        30,
    "Thunderstorm":   10,
    "Snow":           15,
    "Mist":           50,
    "Fog":            40,
}


def score_temperature(temp):
    if temp is None or pd.isna(temp):
        return 0
    if TEMP_IDEAL_MIN <= temp <= TEMP_IDEAL_MAX:
        return 100
    if temp < TEMP_IDEAL_MIN:
        ecart = TEMP_IDEAL_MIN - temp
    else:
        ecart = temp - TEMP_IDEAL_MAX
    return max(0, 100 - (ecart * 5))


def score_humidity(humidity):
    if humidity is None or pd.isna(humidity):
        return 0
    if HUM_IDEAL_MIN <= humidity <= HUM_IDEAL_MAX:
        return 100
    if humidity < HUM_IDEAL_MIN:
        ecart = HUM_IDEAL_MIN - humidity
    else:
        ecart = humidity - HUM_IDEAL_MAX
    return max(0, 100 - (ecart * 2))


def score_wind(wind_speed):
    if wind_speed is None or pd.isna(wind_speed):
        return 0
    if wind_speed <= WIND_IDEAL_MAX:
        return 100
    return max(0, 100 - ((wind_speed - WIND_IDEAL_MAX) * 8))


def score_sky(weather_main):
    if weather_main is None or pd.isna(weather_main):
        return 50
    return SKY_BONUS.get(weather_main, 50)


def compute_weather_score(row):
    s_temp = score_temperature(row["temperature"])
    s_hum  = score_humidity(row["humidity"])
    s_wind = score_wind(row["wind_speed"])
    s_sky  = score_sky(row["weather_main"])
    final = (WEIGHT_TEMP * s_temp + WEIGHT_HUM * s_hum +
             WEIGHT_WIND * s_wind + WEIGHT_SKY * s_sky)
    return round(final, 2)


def classify_score(score):
    if score >= 80:
        return "Excellent"
    elif score >= 65:
        return "Bon"
    elif score >= 50:
        return "Moyen"
    else:
        return "Mauvais"


def run_gold_transformation():
    print("=" * 60)
    print(f"  TRANSFORMATION GOLD LAYER — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    silver_file = os.path.join(SILVER_PATH, "weather_clean.csv")
    if not os.path.exists(silver_file):
        print(f"   ❌ Fichier Silver introuvable : {silver_file}")
        return

    df = pd.read_csv(silver_file)
    print(f"   ↪ {len(df)} lignes chargées depuis le Silver")

    # === CORRECTION 1 : ne garder que la mesure la plus récente par ville ===
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
    df = df.sort_values("event_timestamp").drop_duplicates(
        subset="city", keep="last"
    ).reset_index(drop=True)
    print(f"   ↪ {len(df)} villes uniques (mesure la plus récente)")

    # Calcul des scores
    df["score_temperature"] = df["temperature"].apply(score_temperature)
    df["score_humidity"]    = df["humidity"].apply(score_humidity)
    df["score_wind"]        = df["wind_speed"].apply(score_wind)
    df["score_sky"]         = df["weather_main"].apply(score_sky)
    df["weather_score"]     = df.apply(compute_weather_score, axis=1)
    df["score_category"]    = df["weather_score"].apply(classify_score)

    print(f"   ↪ Score météo calculé pour chaque ville")

    # === CORRECTION 2 : rangs uniques (method="first" au lieu de "min") ===
    df = df.sort_values("weather_score", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)  # Rang strictement croissant

    best_city = df.iloc[0]
    print(f"   🏆 Meilleure ville : {best_city['city']} ({best_city['weather_score']}/100)")

    gold_columns = [
        "city", "country", "latitude", "longitude", "date",
        "temperature", "humidity", "wind_speed", "weather_main",
        "score_temperature", "score_humidity", "score_wind", "score_sky",
        "weather_score", "score_category", "rank",
        "event_timestamp", "ingestion_timestamp",
    ]
    df_gold = df[gold_columns].copy()

    os.makedirs(GOLD_PATH, exist_ok=True)

    main_file = os.path.join(GOLD_PATH, "weather_scores.csv")
    df_gold.to_csv(main_file, index=False, encoding="utf-8")

    best_file = os.path.join(GOLD_PATH, "best_city.csv")
    pd.DataFrame([best_city[gold_columns]]).to_csv(best_file, index=False, encoding="utf-8")

    ranking_file = os.path.join(GOLD_PATH, "ranking.csv")
    df_gold[["rank", "city", "weather_score", "score_category", "date"]].to_csv(
        ranking_file, index=False, encoding="utf-8"
    )

    print("=" * 60)
    print(f"   ✅ {main_file}")
    print(f"   ✅ {best_file}")
    print(f"   ✅ {ranking_file}")
    print("=" * 60)

    print("\n   🏆 CLASSEMENT DU JOUR :")
    print("   " + "-" * 56)
    display = df_gold[["rank", "city", "temperature", "humidity",
                       "wind_speed", "weather_main", "weather_score",
                       "score_category"]]
    print(display.to_string(index=False))


if __name__ == "__main__":
    run_gold_transformation()