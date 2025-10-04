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
    
    df_planning = df_planning.fillna({COL_DEBUT: '00:00:00', COL_FIN: '00:00:00'})

    try:
        # Fonction robuste pour convertir les valeurs d'heure (chaîne, datetime.time, ou float Excel) en chaîne 'HH:MM:SS'
        def to_time_str(val):
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

        df_planning[COL_DEBUT] = df_planning[COL_DEBUT].apply(to_time_str).str.strip()
        df_planning[COL_FIN] = df_planning[COL_FIN].apply(to_time_str).str.strip()
        
        df_planning['Duree_Debut'] = pd.to_timedelta(df_planning[COL_DEBUT])
        df_planning['Duree_Fin'] = pd.to_timedelta(df_planning[COL_FIN])
        
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
            return duree

        df_planning['Durée du service'] = df_planning.apply(calculer_duree, axis=1)
        
        total_duree = df_planning[df_planning['Durée du service'] > pd.Timedelta(0)]['Durée du service'].sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception:
        return df_planning, "Erreur de calcul"


# --- FONCTION DE CHARGEMENT DES DONNÉES (VERSION EXCEL) ---

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier Excel une seule fois et nettoie les données."""
    try:
        # Lecture du fichier Excel (nécessite openpyxl)
        df = pd.read_excel(fichier)
        
        # Nettoyage des noms de colonnes et des données
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                
        # Supprimer les lignes vides
        df = df.dropna(how='all')
        
        # S'assurer que les
