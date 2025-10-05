import pandas as pd
import streamlit as st
from datetime import date, timedelta, time
import numpy as np
import io
import os 

# --- 1. CONFIGURATION ET CONSTANTES ---

# TITRE DE L'ONGLET DU NAVIGATEUR ET RÉGLAGES DE LA PAGE
st.set_page_config(
    page_title="Planning CLICHY - Consultation", 
    layout="wide", 
    initial_sidebar_state="expanded", 
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}, 
    page_icon="📅"
)


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

# --- 2. FONCTIONS DE TRAITEMENT ---

def formater_duree(td):
    """Convertit un Timedelta en format 'Hh MMmin' lisible, utilisé pour le total."""
    if pd.isna(td):
        return "0h 00"
    
    total_seconds = td.total_seconds()
    heures = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    return f"{heures}h {minutes:02d}"


def get_dates_for_week(week_str, year=2025, format_type='full'):
    """Calcule la plage de dates pour la semaine (Année 2025 codée en dur)."""
    try:
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str if format_type == 'full' else "Erreur SEMAINE (pas un format SXX)"
    
    try:
        # Nous prenons le 4 janvier comme point de référence pour le calcul
        d = date(year, 1, 4) 
        
        # isocalendar()[1] donne le numéro de semaine ISO
        iso_week_of_jan_4 = d.isocalendar()[1] 
        # Déplace le point de référence au début de la semaine souhaitée
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

# --- 3. LOGIQUE D'AUTHENTIFICATION ---

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
    st.markdown("<h1 style='text-align: center;'>Connexion à l'application Planning</h1>", unsafe_allow_html=True)
    st.warning("Veuillez entrer votre identifiant et mot de passe pour accéder.")

    with st.form("login_form"):
        username_input = st.text_input("Prénom (Identifiant)").strip().upper()
        password_input = st.text_input("Mot de Passe", type="password")
        submitted = st.form_submit_button("Se connecter")

        if submitted:
            if username_input in USERNAMES and password_input == PASSWORD:
                st.session_state['authenticated'] = True
                st.session_state['username'] = username_input
                st.rerun() 
            else:
                st.error("Identifiant ou mot de passe incorrect.")

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
                # Utilise st.logo si Streamlit le supporte, sinon st.sidebar.image
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

        # 4.3 Barre latérale et menus déroulants
        
        # MESSAGE DE BIENVENUE ET DÉCONNEXION
        st.sidebar.markdown(f"**👋 Bienvenue, {st.session_state['username'].title()}**")
        
        if st.sidebar.button("Déconnexion"):
            st.session_state['authenticated'] = False
            st.session_state['username'] = None
            st.rerun()
            
        st.sidebar.markdown("---")
        
        # L'employé sélectionné est celui qui est connecté (pour la sécurité)
        employe_selectionne = st.session_state['username']
        
        if employe_selectionne not in liste_employes:
            st.error(f"Erreur : Le prénom de connexion ({employe_selectionne}) ne correspond pas à un employé dans le fichier de planning.")
            st.stop()


        # Filtrer les semaines travaillées pour l'employé sélectionné
        df_employe_filtre = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
        
        df_semaines_travaillees = df_employe_filtre[
            df_employe_filtre['TEMPS_TOTAL_SEMAINE'] > pd.Timedelta(0)
        ].drop_duplicates(subset=[COL_SEMAINE])
        
        liste_semaines_brutes = sorted(df_semaines_travaillees[COL_SEMAINE].unique().tolist())

        
        # Initialisation de la semaine pour l'affichage conditionnel
        semaine_selectionnee_brute = None
        
        if not liste_semaines_brutes:
            st.markdown("---")
            st.warning(f"**Attention :** Aucune semaine avec un temps de travail positif n'a été trouvée pour **{employe_selectionne}**.")
            
        else:
            # Poursuite de l'affichage UNIQUEMENT si des semaines sont disponibles
            liste_semaines_formatees = [get_dates_for_week(s, format_type='full') for s in liste_semaines_brutes]
            semaine_mapping = dict(zip(liste_semaines_formatees, liste_semaines_brutes))
            
            # --- LOGIQUE D'AMÉLIORATION B: SÉLECTION AUTOMATIQUE DE LA SEMAINE ACTUELLE ---
            semaine_actuelle_num = date.today().isocalendar()[1]
            # Formate le numéro de semaine avec un 'S' et deux chiffres (ex: 'S41')
            semaine_actuelle_brute = f"S{semaine_actuelle_num:02d}" 
            
            # Chercher l'index de la semaine actuelle
            try:
                # Tente de trouver la semaine actuelle dans la liste des semaines disponibles
                index_semaine_actuelle = liste_semaines_brutes.index(semaine_actuelle_brute)
            except ValueError:
                # Si la semaine actuelle n'est pas dans le planning, sélectionne la première semaine de la liste
                index_semaine_actuelle = 0
            
            
            # --- 1. DÉTAIL SEMAINE (Sélection) EN PREMIER ---
            st.sidebar.header("Détail Semaine") 
            
            semaine_selectionnee_formattee = st.sidebar.selectbox(
                'Sélectionnez la semaine', 
                liste_semaines_formatees,
                # Utilisation de l'index calculé pour la présélection
                index=index_semaine_actuelle 
            )
            
            semaine_selectionnee_brute = semaine_mapping.get(semaine_selectionnee_formattee)
            st.sidebar.markdown("---")
            
            
            # --- 2. SYNTHÈSE GLOBALE EN SECOND ---
            if not df_semaines_travaillees.empty:
                
                st.sidebar.subheader("Synthèse Annuelle")
                
                # Créer le tableau de synthèse
                df_synthese = df_semaines_travaillees[[COL_SEMAINE, 'TEMPS_TOTAL_SEMAINE']].copy()
                df_synthese = df_synthese.sort_values(by=COL_SEMAINE, ascending=False)
                
                # Formater la colonne des totaux pour l'affichage
                df_synthese['Total Heures'] = df_synthese['TEMPS_TOTAL_SEMAINE'].apply(formater_duree).str.replace("min", "")
                
                st.sidebar.dataframe(
                    df_synthese[[COL_SEMAINE, 'Total Heures']],
                    use_container_width=True,
                    column_config={
                        COL_SEMAINE: st.column_config.Column("Semaine", width="small"),
                        "Total Heures": st.column_config.Column("Total (net)", width="small"),
                    },
                    hide_index=True
                )
                st.sidebar.markdown("---")
            
            # -------------------------------------------------

            # 4.4 Affichage du planning
            if employe_selectionne and semaine_selectionnee_brute:
                
                # Afficher la date sous le titre principal 
                dates_pour_affichage = get_dates_for_week(semaine_selectionnee_brute, format_type='only_dates')
                
                # Affichage de la date au centre
                st.markdown(f"<h3 style='text-align: center;'>{dates_pour_affichage}</h3>", unsafe_allow_html=True)
                st.markdown("---")
                
                df_filtre = df_employe_filtre[df_employe_filtre[COL_SEMAINE] == semaine_selectionnee_brute].copy()
                
                # GESTION SPÉCIFIQUE (Noël)
                if semaine_selectionnee_brute == 'S52':
                    df_filtre_avant = len(df_filtre)
                    df_filtre = df_filtre[df_filtre[COL_JOUR] != 'JEUDI'].copy()
                    if len(df_filtre) < df_filtre_avant:
                        st.info(f"Note: Le **Jeudi** de la semaine S52 a été retiré (Jour de Noël).")

                # Tri
                df_filtre[COL_JOUR] = pd.Categorical(df_filtre[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
                df_filtre = df_filtre.sort_values(by=[COL_JOUR])
                
                df_resultat, total_heures_format = calculer_heures_travaillees(df_filtre)
                
                # Appliquer la logique Repos/École à l'affichage
                def obtenir_statut(row):
                    if row['Durée du service'] > pd.Timedelta(0):
                        return ""
                    debut_str = str(row[COL_DEBUT]).upper()
                    fin_str = str(row[COL_FIN]).upper()
                    if "ECOLE" in debut_str or "ECOLE" in fin_str:
                        return "École"
                    return "Repos"

                df_resultat['Statut'] = df_resultat.apply(obtenir_statut, axis=1)

                df_resultat[COL_DEBUT] = df_resultat.apply(
                    lambda row: row['Statut'] if row['Statut'] in ["Repos", "École"] else row[COL_DEBUT], axis=1
                )
                df_resultat[COL_FIN] = df_resultat.apply(
                    lambda row: "" if row['Statut'] in ["Repos", "École"] else row[COL_FIN], axis=1
                )

                st.subheader(f"Planning pour **{employe_selectionne.title()}**")
                
                # AFFICHAGE DU TOTAL EN MODE METRIC
                st.metric(
                    label=f"Total d'heures calculées pour la semaine {semaine_selectionnee_brute}", 
                    value=f"{total_heures_format}h"
                )
                st.markdown("---")
                
                st.dataframe(
                    df_resultat[[COL_JOUR, COL_DEBUT, COL_FIN]], 
                    use_container_width=True,
                    column_config={
                        COL_JOUR: st.column_config.Column("Jour", width="large"),
                        COL_DEBUT: st.column_config.Column("Début / Statut"), 
                        COL_FIN: st.column_config.Column("Fin"),
                    },
                    hide_index=True
                )
                
    except Exception as e:
        # Affiche l'erreur si elle n'a pas été gérée plus tôt
        st.error(f"Une erreur fatale s'est produite : {e}.")