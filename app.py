import pandas as pd
import streamlit as st
from datetime import date, timedelta, time
import numpy as np
import io
import os 

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

# --- 2. FONCTIONS DE TRAITEMENT (Pas de changement ici) ---

def formater_duree(td):
    """Convertit un Timedelta en format 'Hh MMmin' lisible, utilisé pour le total."""
    if pd.isna(td):
        return "0h 00"
    
    total_seconds = td.total_seconds()
    heures = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    return f"{heures}h {minutes:02d}"


def get_dates_for_week(week_str, year=2025, format_type='full'):
    """Calcule la plage de dates pour la semaine."""
    try:
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str if format_type == 'full' else "Erreur SEMAINE (pas un format SXX)"
    
    try:
        d = date(year, 1, 4) 
        
        iso_week_of_jan_4 = d.isocalendar()[1] 
        date_debut = d + timedelta(days=(week_num - iso_week_of_jan_4) * 7)
        
        date_fin = date_debut + timedelta(days=6)
        
        date_debut_str = date_debut.strftime("%d/%m/%y")
        date_fin_str = date_fin.strftime("%d/%m/%y")
        
        if format_type == 'full':
            return f"{week_str} : du {date_debut_str} au {date_fin_str}"
        else: # only_dates
            return f"Semaine {week_str} : du {date_debut_str} au {date_fin_str}"
            
    except Exception as e:
        return f"Erreur de calcul de date: {e}" if format_type == 'only_dates' else week_str

def convertir_heure_en_timedelta(val):
    """Convertit diverses entrées d'heure en timedelta (pour le calcul des heures)."""
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
    """Calcule la durée de travail nette pour une ligne (avec 1h de pause si > 1h)."""
    if pd.isna(row['Duree_Debut']) or pd.isna(row['Duree_Fin']): 
        return pd.Timedelta(0) 
    
    duree = row['Duree_Fin'] - row['Duree_Debut']
    
    if duree < pd.Timedelta(0): 
        duree += pd.Timedelta(days=1)
        
    if duree > pd.Timedelta(hours=1): 
        duree -= pd.Timedelta(hours=1)
        
    if duree < pd.Timedelta(0): return pd.Timedelta(0)
    return duree

def calculer_heures_travaillees(df_planning):
    """Calcule la durée de travail nette et le total."""
    df_planning_calc = df_planning.copy()
    
    df_planning_calc['Duree_Debut'] = df_planning_calc[COL_DEBUT].apply(convertir_heure_en_timedelta)
    df_planning_calc['Duree_Fin'] = df_planning_calc[COL_FIN].apply(convertir_heure_en_timedelta)
    
    df_planning_calc['Durée du service'] = df_planning_calc.apply(calculer_duree_service, axis=1)
    df_planning['Durée du service'] = df_planning_calc['Durée du service'] 

    durees_positives = df_planning_calc[df_planning_calc['Durée du service'] > pd.Timedelta(0)]['Durée du service']
    total_duree = durees_positives.sum()
    
    total_heures_format = formater_duree(total_duree).replace("min", "") 
    
    return df_planning, total_heures_format

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier, vérifie les colonnes, nettoie les données et pré-calcule les totaux."""
    try:
        df = pd.read_excel(fichier)
    except Exception:
        try:
            df = pd.read_csv(fichier, sep=';', encoding='latin1')
        except Exception as e_final:
            st.error(f"**ERREUR CRITIQUE DE FICHIER :** Impossible de lire le fichier '{fichier}'. Vérifiez son nom, son emplacement et son contenu (format Excel ou CSV).")
            st.stop()
    
    df.columns = df.columns.str.strip()
    colonnes_manquantes = [col for col in COLONNES_OBLIGATOIRES if col not in df.columns]
    
    if colonnes_manquantes:
        st.error(f"**ERREUR DE DONNÉES : Colonnes manquantes.** Votre fichier doit contenir : {', '.join(COLONNES_OBLIGATOIRES)}. Manque : {', '.join(colonnes_manquantes)}")
        st.stop()
        
    for col in df.columns:
        if df[col].dtype == 'object' or df[col].dtype.name == 'category': 
            df[col] = df[col].astype(str).str.strip()
            
    df = df.dropna(how='all')
    df[COL_JOUR] = df[COL_JOUR].astype(str).str.upper()
    df[COL_SEMAINE] = df[COL_SEMAINE].astype(str).str.upper()

    df_calc = df.copy()
    df_calc['Duree_Debut'] = df_calc[COL_DEBUT].apply(convertir_heure_en_timedelta)
    df_calc['Duree_Fin'] = df_calc[COL_FIN].apply(convertir_heure_en_timedelta)
    df_calc['Durée_Service_Total'] = df_calc.apply(calculer_duree_service, axis=1)

    df_totaux = df_calc.groupby([COL_EMPLOYE, COL_SEMAINE])['Durée_Service_Total'].sum().reset_index()
    df_totaux = df_totaux.rename(columns={'Durée_Service_Total': 'TEMPS_TOTAL_SEMAINE'})
    
    df = pd.merge(df, df_totaux, on=[COL_EMPLOYE, COL_SEMAINE], how='left')
    df['TEMPS_TOTAL_SEMAINE'] = df['TEMPS_TOTAL_SEMAINE'].fillna(pd.Timedelta(0))
    
    return df

# --- 3. LOGIQUE D'AUTHENTIFICATION (NOUVELLE SECTION) ---

# Définition des identifiants valides
USERNAMES = ["JULIEN", "HOUDA", "MOUNIA", "ADAM"]
PASSWORD = "clichy8404"

# Initialisation de l'état de connexion
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None

def login():
    """Fonction de gestion de la connexion."""
    st.title("Connexion")
    st.warning("Veuillez entrer votre identifiant et mot de passe pour accéder.")

    with st.form("login_form"):
        username_input = st.text_input("Prénom (Identifiant)").strip().upper()
        password_input = st.text_input("Mot de Passe", type="password")
        submitted = st.form_submit_button("Se connecter")

        if submitted:
            if username_input in USERNAMES and password_input == PASSWORD:
                st.session_state['authenticated'] = True
                st.session_state['username'] = username_input
                st.rerun() # Rafraîchit l'application pour afficher le contenu
            else:
                st.error("Identifiant ou mot de passe incorrect.")

# --- 4. INTERFACE STREAMLIT PRINCIPALE (ENGLOBÉE DANS L'AUTH) ---

st.set_page_config(page_title="Planning Employé", layout="wide")


# --- Démarrer le processus d'authentification ---

if not st.session_state['authenticated']:
    login()
    
else:
    # Le code ci-dessous ne s'exécute que si l'utilisateur est connecté
    try:
        # 4.1 Affichage du titre principal
        st.markdown("<h1 style='text-align: center;'>PLANNING CLICHY</h1>", unsafe_allow_html=True)
        st.markdown("---") 
        
        # Tentative d'affichage du logo dans la sidebar
        logo_path = NOM_DU_LOGO
        
        if os.path.exists(logo_path):
            try:
                st.logo(logo_path, icon_image=logo_path) 
            except Exception:
                 st.sidebar.image(logo_path, caption='Logo', use_column_width=True)
        else:
            st.sidebar.warning(f"Fichier de logo non trouvé : {NOM_DU_LOGO}") 

        # 4.2 Chargement des données 
        df_initial = charger_donnees(NOM_DU_FICHIER)
        
        liste_employes = sorted(df_initial[COL_EMPLOYE].unique().tolist())
        
        # Vérification des employés après chargement
        if not liste_employes or (len(liste_employes) == 1 and str(liste_employes[0]).upper() in ['', 'NAN', 'NONE', 'N/A']):
            st.error(f"**ERREUR :** La colonne des employés (`'{COL_EMPLOYE}'`) est vide ou contient des valeurs non valides.")
            st.stop()

        # 4.3 Création des menus déroulants (dans la sidebar)
        st.sidebar.header("Sélections")
        
        # Option 1: Laisser l'utilisateur choisir (décommenter pour cela)
        # employe_selectionne = st.sidebar.selectbox(
        #     'Sélectionnez l\'employé',
        #     liste_employes,
        #     index=liste_employes.index(st.session_state['username']) if st.session_state['username'] in liste_employes else 0
        # )

        # Option 2: FORCER l'affichage du planning de l'utilisateur connecté (plus sécurisé et direct)
        employe_selectionne = st.session_state['username']
        
        if employe_selectionne not in liste_employes:
            st.error(f"Erreur : Le prénom de connexion ({employe_selectionne}) ne correspond pas à un employé dans le fichier de planning.")
            st.stop()


        # Filtrer les semaines travaillées pour l'employé sélectionné
        df_employe_filtre = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
        df_semaines_travaillees = df_employe_filtre[df_employe_filtre['TEMPS_TOTAL_SEMAINE'] > pd.Timedelta(0)]
        
        liste_semaines_brutes = sorted(df_semaines_travaillees[COL_SEMAINE].unique().tolist())

        # Initialisation de la semaine pour l'affichage conditionnel
        semaine_selectionnee_brute = None
        
        if not liste_semaines_brutes:
            st.markdown("---")
            st.warning(f"**Attention :** Aucune semaine avec un temps de travail positif n'a été trouvée