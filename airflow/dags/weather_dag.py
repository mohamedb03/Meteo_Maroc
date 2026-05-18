"""
DAG Airflow - Pipeline Météo Maroc
====================================
Orchestre le pipeline complet :
    Bronze (ingestion) -> Silver (transform) -> Gold (analytics) -> Tests qualité

Fréquence : tous les jours à 6h du matin (exigence du sujet)
"""

import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ============================================================
#  IMPORTANT : Ajout du dossier projet au PYTHONPATH
#  pour pouvoir importer ingestion.py, transform_silver.py, etc.
# ============================================================
PROJECT_DIR = os.path.expanduser("~/Desktop/projet_meteo")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Imports de nos modules Python
from ingestion import run_ingestion
from transform_silver import run_silver_transformation
from transform_gold import run_gold_transformation
from tests_quality import run_quality_tests


# ============================================================
#  PARAMETRES PAR DEFAUT DU DAG
# ============================================================
default_args = {
    "owner": "EMSI - 4IASD",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ============================================================
#  WRAPPER POUR LES TESTS QUALITE
#  (run_quality_tests retourne 0 ou 1, on doit lever une exception
#  si ça échoue pour qu'Airflow marque la tâche en rouge)
# ============================================================
def task_quality_tests():
    exit_code = run_quality_tests()
    if exit_code != 0:
        raise ValueError("Tests qualité échoués — pipeline invalide")


# ============================================================
#  CHANGEMENT DE DOSSIER DE TRAVAIL AVANT CHAQUE TACHE
#  (les scripts utilisent des chemins relatifs)
# ============================================================
def task_with_cwd(func):
    """Wrapper qui place le cwd dans le dossier projet avant exécution."""
    def wrapper():
        os.chdir(PROJECT_DIR)
        return func()
    return wrapper


# ============================================================
#  DEFINITION DU DAG
# ============================================================
with DAG(
    dag_id="weather_pipeline_maroc",
    description="Pipeline météo Maroc - Bronze, Silver, Gold + Tests",
    default_args=default_args,
    start_date=datetime(2026, 5, 10),
    schedule="0 6 * * *",       # Tous les jours à 6h du matin
    catchup=False,              # Pas de rattrapage des jours manqués
    tags=["meteo", "emsi", "4IASD", "etl"],
) as dag:

    # === Tâche 1 : Ingestion Bronze ===
    ingestion_task = PythonOperator(
        task_id="bronze_ingestion",
        python_callable=task_with_cwd(run_ingestion),
        doc_md="Appelle l'API OpenWeather et stocke les JSON bruts dans le Bronze Layer.",
    )

    # === Tâche 2 : Transformation Silver ===
    silver_task = PythonOperator(
        task_id="silver_transformation",
        python_callable=task_with_cwd(run_silver_transformation),
        doc_md="Nettoie et structure les données du Bronze vers le Silver Layer.",
    )

    # === Tâche 3 : Transformation Gold ===
    gold_task = PythonOperator(
        task_id="gold_transformation",
        python_callable=task_with_cwd(run_gold_transformation),
        doc_md="Calcule le score météo et classe les villes (Gold Layer).",
    )

    # === Tâche 4 : Tests qualité ===
    quality_task = PythonOperator(
        task_id="quality_tests",
        python_callable=task_with_cwd(task_quality_tests),
        doc_md="Vérifie la fiabilité des 3 layers (Bronze, Silver, Gold).",
    )

    # === Dépendances : exécution séquentielle ===
    ingestion_task >> silver_task >> gold_task >> quality_task
    