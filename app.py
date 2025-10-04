import pandas as pd
import streamlit as st
import datetime

# --- CONFIGURATION DU FICHIER ---
# Nom exact du fichier Excel (doit être au format .xlsx)
NOM_DU_FICHIER = "planning.xlsx"

# Noms des colonnes (headers) - DOIVENT CORRESPONDRE
COL_EMPLOYE = 'NOM VENDEUR'
COL_SEMAINE = 'SEMAINE'
COL_JOUR = 'JOUR'
COL_DEBUT = 'HEURE DEBUT'
COL_FIN = 'HEURE FIN'

# Ordre logique des jours
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures travaillées et la durée par service."""
    
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

        return df_planning, f"{heures}h {minutes}min"
        
    except Exception as e:
        df_planning['Durée du service'] = pd.NaT
        return df_planning, f"Erreur de calcul: {e}"


# --- FONCTION DE CHARGEMENT DES DONNÉES (VERSION EXCEL) ---

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier Excel une seule fois et nettoie les données."""
    try:
        # Lecture du fichier Excel (nécessite openpyxl)
        df = pd.read_excel(fichier)
        
        # Nettoyage des noms de colonnes et des données
        df.columns = df.columns.str.strip()
        
        # FIX: Remplacement immédiat des NaN/NaT par des chaînes vides ("") pour l'affichage
        df[COL_DEBUT] = df[COL_DEBUT].fillna("")
        df[COL_FIN] = df[COL_FIN].fillna("")

        for col in df.columns:
            # Conversion de toutes les colonnes objet en string et nettoyage des espaces
            if df[col].dtype == 'object' or df[col].dtype.name == 'category':
                df[col] = df[col].astype(str).str.strip()
                
        # Supprimer les lignes vides
        df = df.dropna(how='all')
