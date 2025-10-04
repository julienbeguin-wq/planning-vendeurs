import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta

# --- CONFIGURATION DU FICHIER ---
# Nom exact du fichier. ATTENTION : Vous avez défini "planningss.xlsx".
NOM_DU_FICHIER = "plannings.xlsx"

# Noms des colonnes (headers) - DOIVENT CORRESPONDRE
COL_EMPLOYE = 'NOM VENDEUR'
COL_SEMAINE = 'SEMAINE'
COL_JOUR = 'JOUR'
COL_DEBUT = 'HEURE DEBUT'
COL_FIN = 'HEURE FIN'

# Ordre logique des jours
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

# --- CONVERSION DE SEMAINE EN DATES (Année 2025 de référence) ---

def get_dates_for_week(week_str, year=2025):
    """Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin (Lundi-Dimanche)."""
    
    # Mapping simple des mois pour éviter les problèmes de locale
    MONTHS = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
        7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    try:
        # Tente de convertir S41 en 41
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str

    try:
        # Calcul des dates à partir du numéro de semaine ISO
        d = date(year, 1, 4) 
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        
        # Formatage de l'affichage (ex: 15 décembre)
        date_debut_str = f"{date_debut.day} {MONTHS[date_debut.month]}"
        date_fin_str = f"{date_fin.day} {MONTHS[date_fin.month]}"

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        return week_str


# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures travaillées et la durée par service."""
    
    df_planning_calc = df_planning.copy()

    try:
        # 1. Préparation des colonnes pour le calcul
        def to_time_str_for_calc(val):
            if pd.isna(val) or val == "":
                return "00:00:00"
            if isinstance(val, (datetime.time, pd.Timestamp)):
                return str(val)
            elif isinstance(val, (int, float)) and 0 <= val <= 1: 
                # Conversion des heures Excel (format float)
                total_seconds = val * 86400 
                h = int(total_seconds // 3600)
                m = int((total_seconds % 3600) // 60)
                s = int(total_seconds % 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return str(val)

        df_planning_calc['Duree_Debut'] = pd.to_timedelta(df_planning_calc[COL_DEBUT].apply(to_time_str_for_calc).str.strip())
        df_planning_calc['Duree_Fin'] = pd.to_timedelta(df_planning_calc[COL_FIN].apply(to_time_str_for_calc).str.strip())
        
        # 2. Calcul de la durée du service
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            
            # Gère les horaires de nuit
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
                
            # DÉDUCTION DE LA PAUSE
