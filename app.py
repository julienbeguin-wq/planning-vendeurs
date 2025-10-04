import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta

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

def get_dates_for_week(week_str, year=2025):
    """
    Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin.
    NOTE : Nous utilisons 2025 comme année de référence, car le planning couvre fin d'année.
    """
    try:
        # Extraire le numéro de semaine (ex: 41 de 'S41')
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str, week_str # Retourne la chaîne originale si le format n'est pas SXX

    # Calcule la date du lundi (premier jour) de la semaine
    # Utilise la convention ISO 8601 (lundi=1, dimanche=7)
    try:
        d = date(year, 1, 1) # Démarre au 1er janvier de l'année
        
        # Trouver le premier lundi de l'année
        if d.isoweekday() > 1:
            d += timedelta(days=7 - d.isoweekday() + 1)
        
        # Calculer la date de début de la semaine souhaitée
        # Le "-1" est pour s'ajuster à la première semaine de l'année
        date_debut = d + timedelta(days=(week_num - 1) * 7)
        
        # Calculer la date de fin (dimanche)
        date_fin = date_debut + timedelta(days=6)
        
        # Formatage du texte
        date_debut_str = date_debut.strftime("%d %B").lstrip('0')
        date_fin_str = date_fin.strftime("%d %B").lstrip('0')
        
        # Affichage du mois en minuscules (ex: 06 octobre -> 6 octobre)
        date_debut_str = date_debut_str.replace(date_debut_str.split(' ')[1], date_debut_str.split(' ')[1].lower())
        date_fin_str = date_fin_str.replace(date_fin_str.split(' ')[1], date_fin_str.split(' ')[1].lower())

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        # En cas d'erreur de calcul (ex: semaine non valide), retourne la chaîne originale
        return week_str


# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    # ... (le corps de cette fonction reste inchangé) ...
    df_planning_calc = df_planning.copy()

    try:
        # Fonction robuste pour convertir les valeurs d'heure en chaîne pour le calcul
        def to_time_str(val):
            # Si la valeur est manquante ou vide (nan ou ""), elle sera traitée comme 00:00:00
            if pd.isna(val) or val == "":
                return "00:00:00"
            if isinstance(val, (datetime.time, pd.Timestamp)):
                return str(val)
            # Gère les floats (fraction de jour) si Excel les a renvoyés
            elif isinstance(val, (int, float)) and 0 <= val <= 1: 
                total_seconds = val * 86400 
                h = int(total_seconds // 3600)
                m = int((total_seconds % 3600) // 60)
                s = int(total_seconds % 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return str(val)

        df_planning_calc['Duree_Debut'] = df_planning_calc[COL_DEBUT].apply(to_time_str).str.strip()
        df_planning_calc['Duree_Fin'] = df_planning_calc[COL_FIN].apply(to_time_str).str.strip()
        
        df_planning_calc['Duree_Debut'] = pd.to_timedelta(df_planning_calc['Duree_Debut'])
        df_planning_calc['Duree_Fin'] = pd.to_timedelta(df_planning_calc['Duree_Fin'])
        
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
            return duree

        df_planning_calc['Durée du service'] = df_planning_calc.apply(calculer_duree, axis=1)
        
        df_planning_calc['Durée du service'] = pd.to_timedelta(df_planning_calc['Durée du service'], errors='coerce')
        
        total_duree = df_planning_calc[df_planning_calc['Durée du service'] > pd.Timedelta(0)]['Durée du service'].sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        df_planning['Durée du service'] = df_planning_calc['Durée du service']

        return df_planning, f
