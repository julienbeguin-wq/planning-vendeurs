import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta
import locale

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

# --- CONVERSION DE SEMAINE EN DATES (Année 2025 de référence) ---

# Tenter de définir la locale en français pour les mois
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'fra')
    except locale.Error:
        pass # Laisser par défaut si non disponible

def get_dates_for_week(week_str, year=2025):
    """Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin (Lundi-Dimanche)."""
    try:
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str, week_str

    try:
        # Créer une date au début de l'année
        d = date(year, 1, 4) 
        
        # Trouver la date du lundi de la semaine souhaitée (ISO week date)
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        
        # Formatage du texte
        date_debut_str = date_debut.strftime("%d %B").lstrip('0')
        date_fin_str = date_fin.strftime("%d %B").lstrip('0')
        
        # Mettre le mois en minuscules
        date_debut_str = date_debut_str.replace(date_debut_str.split(' ')[1], date_debut_str.split(' ')[1].lower())
        date_fin_str = date_fin_str.replace(date_fin_str.split(' ')[1], date_fin_str.split(' ')[1].lower())

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        return week_str


# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures travaillées et la durée par service."""
    
    df_planning
