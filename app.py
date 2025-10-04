import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta
import yaml 
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# --- CONFIGURATION DU FICHIER ---
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

# --- CONFIGURATION D'AUTHENTIFICATION ---

# 1. LISTE DE VOS MOTS DE PASSE EN CLAIR (À MODIFIER!)
passwords_clairs = ['password123', 'autre_mdp'] # REMPLACEZ PAR VOS VRAIS MDP EN CLAIR

# 2. GÉNÉRER LES MOTS DE PASSE CRYPTÉS (HASHÉS)
hashed_passwords = stauth.Hasher(passwords_clairs).generate()


config = {
    'cookie': {
        'expiry_days': 30,
        'key': 'random_secret_key_please_change_this', # CLÉ SECRÈTE À MODIFIER
        'name': 'streamlit_auth_cookie'
    },
    'credentials': {
        'usernames': {
            'admin': {
                'email': 'admin@example.com',
                'name': 'Administrateur',
                'password': hashed_passwords[0] 
            },
            'user1': {
                'email': 'user1@example.com',
                'name': 'Utilisateur Standard',
                'password': hashed_passwords[1]
            }
        }
    },
    'preauthorized': {
        'emails': ['example@email.com']
    }
}

# --- FONCTION DE CONVERSION DE SEMAINE EN DATES ---

def get_dates_for_week(week_str, year=2025):
    """Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin (Lundi-Dimanche)."""
    
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

# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures travaillées et la durée par service."""
    
    df_planning_calc = df_planning.copy()

    try:
        def to_time_str_for_calc(val):
            if pd.isna(val) or val == "":
                return "00:00:00"
            if isinstance(val, (datetime.time, pd.Timestamp)):
                return str(val)
            elif isinstance(val, (int, float)) and 0 <= val <= 1: 
                total_seconds = val * 86400 
                h = int(total_seconds // 3600)
                m = int((total_seconds % 3600) // 60)
                s = int(total_seconds % 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return str(val)

        df_planning_calc['Duree_Debut'] = pd.to_timedelta(df_planning_calc[COL_DEBUT].apply(to_time_str_for_calc).str.strip())
        df_planning_calc['Duree_Fin'] = pd.to_timedelta(df_planning_calc[COL_FIN].apply(to_time_str_for_calc).str.strip())
        
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
            if duree > pd.Timedelta(hours=1):
                duree -= pd.Timedelta(hours=1) # DÉDUCTION DE LA PAUSE DÉJEUNER (1 heure)
            if duree < pd.Timedelta(0):
                return pd.Timedelta(0)
            return duree

        df_planning_calc['Durée du service'] = df_planning_calc.apply(calculer_duree, axis=1)
        df_planning['Durée du service'] = df_planning_calc['Durée du service'] 
        
        durees_positives = df_planning_calc[df_planning_calc['Durée du service'] > pd.Timedelta(0)]['Durée du service']
        total_duree = durees_positives.sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception as e:
        df_planning['Durée du service'] = pd.NaT
        return df_planning, f"Erreur de calcul: {e}"

# --- FONCTION DE CHARGEMENT DES DONNÉES ---

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier (Excel ou CSV) et nettoie les données."""
    try:
        df = pd.read_excel(fichier)
    except Exception:
        try:
            df = pd.read_csv(fichier, sep=';', encoding='latin1')
        except Exception as e:
            try:
                df = pd.read_csv(fichier, encoding='latin1') 
            except Exception as e_final:
                st.error(f"**ERREUR CRITIQUE : Impossible de lire le fichier de données.** Vérifiez le nom et le format du fichier.")
                st.stop()
    
    # --- NETTOYAGE DES DONNÉES ---
    df.columns = df.columns.str.strip()
    df[COL_DEBUT] = df[COL_DEBUT].fillna("")
    df[COL_FIN] = df[COL_FIN].fillna("")

    for col in df.columns:
        if df[col].dtype == 'object' or df[col].dtype.name == '