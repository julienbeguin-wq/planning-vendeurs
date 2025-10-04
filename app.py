import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta
import locale
import platform

# --- CONFIGURATION DU FICHIER ---
# Nom exact du fichier Excel (doit être au format .xlsx)
NOM_DU_FICHIER = "planningss.xlsx"

# Noms des colonnes (headers) - DOIVENT CORRESPONDRE
COL_EMPLOYE = 'NOM VENDEUR'
COL_SEMAINE = 'SEMAINE'
COL_JOUR = 'JOUR'
COL_DEBUT = 'HEURE DEBUT'
COL_FIN = 'HEURE FIN'

# Ordre logique des jours
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

# --- NOUVELLE FONCTION DE CONVERSION DE SEMAINE EN DATES ---

# Tenter de définir la locale en français pour l'affichage des mois
try:
    if platform.system() == "Windows":
        locale.setlocale(locale.LC_TIME, 'fra')
    else:
        # Pour les systèmes basés sur Linux (comme Streamlit Cloud)
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    # Option de secours si la locale n'est pas trouvée
    pass

def get_dates_for_week(week_str, year=2025):
    """
    Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin.
    NOTE : Nous utilisons 2025 comme année de référence.
    """
    try:
        # Extraire le numéro de semaine (ex: 41 de 'S41')
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str, week_str # Retourne la chaîne originale si le format n'est pas SXX

    # Calcule la date du lundi (premier jour) de la semaine
    try:
        # Créer une date dans la semaine 1 de l'année
        d = date(year, 1, 4) 
        
        # Trouver la date correspondant au début de la semaine ISO spécifiée
        # date_debut est le premier jour (lundi) de la semaine souhaitée
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        
        # Calculer la date de fin (dimanche)
        date_fin = date_debut + timedelta(days=6)
        
        # Formatage du texte (Mois en français grâce au module locale)
        date_debut_str = date_debut.strftime("%d %B").lstrip('0')
        date_fin_str = date_fin.strftime("%d %B").lstrip('0')
        
        # Affichage du mois en minuscules
        date_debut_str = date_debut_str.replace(date_debut_str.split(' ')[1], date_debut_str.split(' ')[1].lower())
        date_fin_str = date_fin_str.replace(date_fin_str.split(' ')[1], date_fin_str.split(' ')[1].lower())

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        # En cas d'erreur de calcul (ex: semaine non valide), retourne la chaîne originale
        return week_str


# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures travaillées et la durée par service."""
    
    df_planning_calc = df_planning.copy()

    try:
        # 1. Préparation des colonnes pour le calcul
        def to_time_str_for_calc(val):
            # Si vide/nan, retourne 00:00:00 pour que la durée soit 0 sans erreur
            if pd.isna(val) or val == "":
                return "00:00:00"
            if isinstance(val, (datetime.time, pd.Timestamp)):
                return str(val)
            # Gestion des floats (pour Excel)
            elif isinstance(val, (int, float)) and 0 <= val <= 1: 
                total_seconds = val * 86400 
                h = int(total_seconds // 3600)
                m = int((total_seconds % 3600) // 60)
                s = int(total_seconds % 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return str(val)

        df_planning_calc['Duree_Debut'] = pd.to_timedelta(df_planning_calc[COL_DEBUT].apply(to_time_str_for_calc).str.strip())
        df_planning
