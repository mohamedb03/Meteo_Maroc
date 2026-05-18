"""
Étape 4 - Tests Qualité des données (version robuste)
======================================================
Valide la fiabilité du pipeline sur les 3 layers : Bronze, Silver, Gold.
Cette version gère correctement les ré-exécutions du pipeline.
"""

import os
import glob
import json
import pandas as pd
from datetime import datetime
from config import BRONZE_PATH, SILVER_PATH, GOLD_PATH, CITIES


PASSED = 0
FAILED = 0


def check(condition, message):
    global PASSED, FAILED
    if condition:
        print(f"   ✅ {message}")
        PASSED += 1
    else:
        print(f"   ❌ {message}")
        FAILED += 1


def test_bronze():
    print("\n🥉 TESTS BRONZE LAYER")
    print("-" * 60)
    check(os.path.isdir(BRONZE_PATH), f"Dossier Bronze existe : {BRONZE_PATH}")

    pattern = os.path.join(BRONZE_PATH, "city=*", "date=*", "data_*.json")
    files = glob.glob(pattern)
    check(len(files) > 0, f"Au moins 1 fichier JSON présent ({len(files)} trouvés)")

    for city in CITIES:
        city_files = glob.glob(os.path.join(BRONZE_PATH, f"city={city['name']}", "*", "*.json"))
        check(len(city_files) >= 1, f"Ville {city['name']} : {len(city_files)} fichier(s)")

    for f in files[:3]:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            has_main = "main" in data and "temp" in data["main"]
            check(has_main, f"JSON valide avec champ main.temp : {os.path.basename(f)}")
        except Exception as e:
            check(False, f"JSON invalide {os.path.basename(f)} : {e}")


def test_silver():
    print("\n🥈 TESTS SILVER LAYER")
    print("-" * 60)
    silver_file = os.path.join(SILVER_PATH, "weather_clean.csv")
    check(os.path.isfile(silver_file), f"Fichier Silver existe : {silver_file}")
    if not os.path.isfile(silver_file):
        return

    df = pd.read_csv(silver_file)
    check(len(df) > 0, f"DataFrame non vide ({len(df)} lignes)")

    required_cols = [
        "city", "temperature", "humidity", "wind_speed",
        "weather_main", "event_timestamp", "ingestion_timestamp",
    ]
    for col in required_cols:
        check(col in df.columns, f"Colonne '{col}' présente")

    for col in ["city", "temperature"]:
        nulls = df[col].isna().sum()
        check(nulls == 0, f"Aucune valeur nulle dans '{col}'")

    check(pd.api.types.is_numeric_dtype(df["temperature"]),
          "Colonne 'temperature' de type numérique")
    check(pd.api.types.is_numeric_dtype(df["humidity"]),
          "Colonne 'humidity' de type numérique")

    temp_ok = df["temperature"].between(-20, 55).all()
    check(temp_ok, "Températures dans la plage [-20, 55]°C")

    hum_ok = df["humidity"].between(0, 100).all()
    check(hum_ok, "Humidité dans la plage [0, 100]%")

    wind_ok = (df["wind_speed"] >= 0).all()
    check(wind_ok, "Vitesse du vent ≥ 0")


def test_gold():
    print("\n🥇 TESTS GOLD LAYER")
    print("-" * 60)
    scores_file = os.path.join(GOLD_PATH, "weather_scores.csv")
    best_file   = os.path.join(GOLD_PATH, "best_city.csv")
    ranking_file = os.path.join(GOLD_PATH, "ranking.csv")

    check(os.path.isfile(scores_file), "Fichier weather_scores.csv existe")
    check(os.path.isfile(best_file),   "Fichier best_city.csv existe")
    check(os.path.isfile(ranking_file), "Fichier ranking.csv existe")

    if not os.path.isfile(scores_file):
        return

    df = pd.read_csv(scores_file)
    check("weather_score" in df.columns, "KPI weather_score présent")

    score_ok = df["weather_score"].between(0, 100).all()
    check(score_ok, "Tous les scores entre 0 et 100")

    # === CORRECTION : rangs de 1 à N (N variable) ===
    n_villes = len(df)
    ranks = sorted(df["rank"].tolist())
    expected = list(range(1, n_villes + 1))
    check(ranks == expected, f"Rangs corrects de 1 à {n_villes} : {ranks}")

    best_df = pd.read_csv(best_file)
    check(len(best_df) == 1, "best_city.csv contient exactement 1 ligne")
    if len(best_df) == 1:
        check(int(best_df.iloc[0]["rank"]) == 1, "La meilleure ville a le rang 1")

    check("date" in df.columns, "Colonne 'date' présente (exigence sujet)")

    # === CORRECTION : on accepte les sous-ensembles de catégories ===
    valid_categories = {"Excellent", "Bon", "Moyen", "Mauvais"}
    cats_in_data = set(df["score_category"].unique())
    invalid = cats_in_data - valid_categories
    check(len(invalid) == 0, f"Catégories valides : {cats_in_data}")


def run_quality_tests():
    global PASSED, FAILED
    PASSED = 0
    FAILED = 0

    print("=" * 60)
    print(f"  TESTS QUALITE — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    test_bronze()
    test_silver()
    test_gold()

    total = PASSED + FAILED
    print("\n" + "=" * 60)
    print(f"  RESULTAT FINAL : {PASSED}/{total} tests réussis")
    if FAILED == 0:
        print("  🎉 TOUS LES TESTS SONT OK !")
    else:
        print(f"  ⚠️  {FAILED} test(s) ont échoué — vérifier le pipeline")
    print("=" * 60)

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    exit_code = run_quality_tests()
    exit(exit_code)