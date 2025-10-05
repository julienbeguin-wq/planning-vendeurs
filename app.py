import pandas as pd
import streamlit as st
from datetime import date, timedelta, time
import numpy as np
import io

# --- 1. CONFIGURATION ET CONSTANTES ---

NOM_DU_FICHIER = "RePlannings1.2.xlsx"
NOM_DU_LOGO = "mon_logo.png" 

# Noms des colonnes (headers) - DOIVENT CORRESPONDRE
COL_EMPLOYE = 'NOM VENDEUR'
COL_SEMAINE = 'SEMAINE'
COL_JOUR = 'JOUR'
COL_DEBUT = 'HEURE DEBUT'
COL_FIN = 'HEURE FIN'

# Liste des colonnes obligatoires pour le bon fonctionnement du script
COLONNES_OBLIGATOIRES = [COL_EMPLOYE, COL_SEMAINE, COL_JOUR, COL_DEBUT, COL_FIN]

# Ordre logique des jours
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

# --- 2. FONCTIONS DE TRAITEMENT (Pas de changement ici, elles sont robustes) ---

def formater_duree(td):
    if pd.isna(td):
        return "0h 00"
    total_seconds = td.total_seconds()
    heures = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{heures}h {minutes:02d}"

def get_dates_for_week(week_str, year=2025, format_type='full'):
    try:
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str if format_type == 'full' else ""
    try:
        d = date(year, 1, 4) 
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        
        date_debut_str = date_debut.strftime("%d/%m/%y")
        date_fin_str = date_fin.strftime("%d/%m/%y")
        
        if format_type == 'full':
            return f"{week_str} : du {date_debut_str} au {date_fin_str}"
        else:
            return f"Semaine {week_str} : du {date_debut_str} au {date_fin_str}"
            
    except Exception:
        return week_str if format_type == 'full' else ""

def convertir_heure_en_timedelta(val):
    if pd.isna(val) or val == "":
        return pd.NaT
    if isinstance(val, str) and "ECOLE" in val.upper():
         return pd.NaT
         
    if isinstance(val, (time, pd.Timestamp)):
        return pd.to_timedelta(str(val))
    elif isinstance(val, (int, float)) and 0 <= val <= 1: 
        total_seconds = val * 86400 
        return pd.to_timedelta(total_seconds, unit='s')
    try:
        return pd.to_timedelta(val)
    except:
        return pd.NaT

def calculer_duree_service(row):
    if pd.isna(row['Duree_Debut']) or pd.isna(row['Duree_
