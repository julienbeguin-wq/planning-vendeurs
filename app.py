import pandas as pd
import streamlit as st
from datetime import date, timedelta, time
import numpy as np

# --- 1. CONFIGURATION ET CONSTANTES ---

NOM_DU_FICHIER = "planningss.xlsx"
NOM_DU_LOGO = "mon_logo.png" 

# Noms des colonnes (headers) - DOIVENT CORRESPONDRE
COL_EMPLOYE = 'NOM VENDEUR'
COL_SEMAINE = 'SEMAINE'
COL_JOUR = 'JOUR'
COL_DEBUT = 'HEURE DEBUT'
COL_FIN = 'HEURE FIN'

# Ordre logique des jours
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

# --- 2. FONCTIONS DE TRAITEMENT ---

def get_dates_for_week(week_str, year=2025):
    """Calcule la plage de dates pour l'affichage de la semaine."""
    MONTHS = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
        7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    try:
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str
    try:
        d = date(year, 1, 4) 
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        date_debut_str = f"{date_debut.day} {MONTHS[date_debut.month]}"
        date_fin_str = f"{date_fin.day} {MONTHS[date_fin.month]}"
        return f"{week_str} : du {date_debut_str} au {date_fin_str}"
    except Exception:
        return week_str

def convertir_heure_en_timedelta(val):
    """Convertit diverses entrées d'heure (time, float Excel, str) en timedelta."""
    if pd.isna(val) or val == "":
        return pd.NaT
    if isinstance(val, (time, pd.Timestamp)):
        return pd.to_timedelta(str(val))
    elif isinstance(val, (int, float)) and 0 <= val <= 1: 
        # Gestion des formats Excel (fraction du jour)
        total_seconds = val * 86400 
        return pd.to_timedelta(total_seconds, unit='s')
    try:
        # Essayer de convertir la chaîne si elle est déjà formatée
        return pd.to_timedelta(val)
    except:
        return pd.NaT

def calculer_heures_travaillees(df_planning):
    """Calcule la durée de travail nette (avec 1h de pause si > 1h)."""
    df_planning_calc = df_planning.copy()
    
    # Nouvelle conversion utilisant la fonction robuste
    df_planning_calc['Duree_Debut'] = df_planning_calc[COL_DEBUT].apply(convertir_heure_en_timedelta)
    df_planning_calc['Duree_Fin'] = df_planning_calc[COL_FIN].apply(convertir_heure_en_timedelta)
    
    try:
        # Calcul de la durée brute et ajustement pour la pause
        def calculer_duree(row):
            # Si les heures sont manquantes
            if pd.isna(row['Duree_Debut']) or pd.isna(row['Duree_Fin']):
                return pd.Timedelta(0)
            
            duree = row['Duree_Fin'] - row['Duree_Debut']
            
            # Gestion du chevauchement de minuit (si Fin < Début)
            if duree < pd.Timedelta(0): 
                duree += pd.Timedelta(days=1)
                
            # Soustraction de la pause de 1 heure si la durée brute est > 1 heure
            if duree > pd.Timedelta(hours=1): 
                duree -= pd.Timedelta(hours=1)
                
            if duree < pd.Timedelta(0): return pd.Timedelta(0)
            return duree

        df_planning_calc['Durée du service'] = df_planning_calc.apply(calculer_duree, axis=1)
        df_planning['Durée du service'] = df_planning_calc['Durée du service'] 

        # Calcul du total des heures nettes
        durees_positives = df_planning_calc[df_planning_calc['Durée du service'] > pd.Timedelta(0)]['Durée du service']
        total_duree = durees_positives.sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception as e:
        df_planning['Durée du service'] = pd.NaT
        return df_planning, f"Erreur de calcul: {e}"

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier (Excel ou CSV) et nettoie les données."""
    try:
        df = pd.read_excel(fichier)
    except Exception:
        try:
            df = pd.read_csv(fichier, sep=';', encoding='latin1')
        except Exception:
            try:
                df = pd.read_csv(fichier, encoding='latin1') 
            except Exception as e_final:
                st.error(f"**ERREUR CRITIQUE : Impossible de lire le fichier de données.** Vérifiez le nom et le format du fichier (`{fichier}`).")
                st.stop
