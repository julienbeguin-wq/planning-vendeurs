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
        # Ligne corrigée et complète (anciennement ligne 74)
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        
        date_debut_str = f"{date_debut.day} {MONTHS[date_debut.month]}"
        date_fin_str = f"{date_fin.day} {MONTHS[date_fin.month]}"

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        return week_str

# La fonction 'calculer_heures_travaillees' doit suivre ici, sans duplication.
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
        # LIGNE CORRIGÉE : Complète l'appel à isoweek() et ferme les parenthèses
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        
        date_debut_str = f"{date_debut.day} {MONTHS[date_debut.month]}"
        date_fin_str = f"{date_fin.day} {MONTHS[date_fin.month]}"

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        return week_str
    
