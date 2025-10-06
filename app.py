import pandas as pd
import streamlit as st
from datetime import date, timedelta, time
import numpy as np
import os 
import calendar 
import io 
import re 
from collections import defaultdict

# --- 1. CONFIGURATION ET CONSTANTES ---

# TITRE DE L'ONGLET DU NAVIGATEUR ET RÉGLAGES DE LA PAGE
st.set_page_config(
    page_title="Consultation Planning Clichy", 
    layout="wide", 
    initial_sidebar_state="expanded", 
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}, 
    page_icon="📅"
)

NOM_DU_FICHIER = "RePlannings1.2.xlsx"
NOM_DU_LOGO = "mon_logo.png" 

# LISTE DES ANNIVERSAIRES 🎂
# Format : "NOM VENDEUR EN MAJUSCULE" : (Mois, Jour)
ANNIVERSAIRES = {
    "MOUNIA": (2, 20),
    "ADAM": (2, 14),
    "HOUDA": (1, 27),
    "JULIEN": (10, 18), 
}

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


def get_dates_for_week(week_str, year, format_type='full'):
    """Calcule la plage de dates pour la semaine, en utilisant l'année fournie."""
    try:
        week_match = re.search(r'S(\d+)', week_str.upper())
        if not week_match:
            return week_str if format_type == 'full' else "Erreur SEMAINE"
            
        week_num = int(week_match.group(1))
        
    except ValueError:
        return week_str if format_type == 'full' else "Erreur SEMAINE"
    
    try:
        d = date(year, 1, 1)
        # Début de l'année ISO (Lundi de la première semaine)
        date_debut_annee_iso = d + timedelta(days=-d.weekday())

        date_debut = date_debut_annee_iso + timedelta(weeks=week_num - 1)
        date_fin = date_debut + timedelta(days=6)
        
        date_debut_str = date_debut.strftime("%d/%m/%y")
        date_fin_str = date_fin.strftime("%d/%m/%y")

        if format_type == 'full':
            return f"{week_str} ({year}): du {date_debut_str} au {date_fin_str}"
        elif format_type == 'start_date':
             return date_debut 
        elif format_type == 'month': 
             return (date_debut.month, date_debut.year)
        else: # only_dates
            return f"Semaine {week_str} ({year}) : du {date_debut_str} au {date_fin_str}"
            
    except Exception as e:
        # Gère les cas où la semaine n'est pas calculable pour l'année donnée
        return date(year, 1, 1) if format_type == 'start_date' else (1, year) if format_type == 'month' else "Erreur SEMAINE"

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
    
def calculer_duree_brute(row):
    """Calcule la durée de travail brute (avant déduction de la pause)."""
    if pd.isna(row['Duree_Debut']) or pd.isna(row['Duree_Fin']): 
        return pd.Timedelta(0) 
    
    duree = row['Duree_Fin'] - row['Duree_Debut']
    
    if duree < pd.Timedelta(0): 
        duree += pd.Timedelta(days=1)
    
    return duree

def calculer_duree_service(row):
    """Calcule la durée de travail nette pour une ligne (avec 1h de pause si > 1h)."""
    duree = row['Duree_Brute'] 
        
    if duree > pd.Timedelta(hours=1): 
        duree -= pd.Timedelta(hours=1)
        
    if duree < pd.Timedelta(0): return pd.Timedelta(0)
    return duree

def obtenir_statut_global(row):
    """Détermine le statut (Travail, Repos, École) basé sur la durée et le texte."""
    if row['Durée du service'] > pd.Timedelta(0):
        return "Travail"
    debut_str = str(row[COL_DEBUT]).upper()
    fin_str = str(row[COL_FIN]).upper()
    if "ECOLE" in debut_str or "ECOLE" in fin_str:
        return "École"
    return "Repos"


def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures nettes pour le planning."""

    durees_positives = df_planning[df_planning['Durée du service'] > pd.Timedelta(0)]['Durée du service']
    total_duree = durees_positives.sum()
    
    total_heures_format = formater_duree(total_duree).replace("min", "") 
    
    return df_planning, total_heures_format

def extraire_annee(semaine_str):
    """Essaie d'extraire l'année (YY) du format SXX-YY ou retourne une année par défaut."""
    if isinstance(semaine_str, str):
        match = re.search(r'-(\d{2})$', semaine_str)
        if match:
            return 2000 + int(match.group(1))
            
    return date.today().year

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier, vérifie les colonnes, calcule toutes les durées par ligne et pré-calcule les totaux."""
    if not os.path.exists(fichier):
        st.error(f"**ERREUR CRITIQUE DE FICHIER :** Le fichier '{fichier}' est introuvable. Assurez-vous qu'il est dans le même dossier que 'app.py' et que le nom est exact.")
        st.stop()

    try:
        df = pd.read_excel(fichier)
    except Exception:
        try:
            df = pd.read_csv(fichier, sep=';', encoding='latin1')
        except Exception as e_final:
            st.error(f"**ERREUR CRITIQUE DE FICHIER :** Impossible de lire le fichier '{fichier}'. Vérifiez que le fichier n'est pas déjà ouvert et que son contenu est valide (format Excel ou CSV).")
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
    
    df['ANNEE'] = df[COL_SEMAINE].apply(extraire_annee)
    
    # --- CALCULS DE DURÉE PAR LIGNE (Pour le calendrier et le tableau) ---
    df['Duree_Debut'] = df[COL_DEBUT].apply(convertir_heure_en_timedelta)
    df['Duree_Fin'] = df[COL_FIN].apply(convertir_heure_en_timedelta)
    
    df['Duree_Brute'] = df.apply(calculer_duree_brute, axis=1)
    df['Durée du service'] = df.apply(calculer_duree_service, axis=1) # Colonne nécessaire pour le calendrier
    
    # Ajout du statut par ligne pour le calendrier (Travail/Repos/École)
    df['Statut'] = df.apply(obtenir_statut_global, axis=1)
    
    # Ajout de la colonne DATE (pour le calendrier)
    df['DATE'] = df.apply(
        lambda row: get_dates_for_week(row[COL_SEMAINE], row['ANNEE'], format_type='start_date') + 
        timedelta(days=ORDRE_JOURS.index(row[COL_JOUR])), axis=1
    )
    df['DATE'] = pd.to_datetime(df['DATE'])
    # -----------------------------------------------------------------------------------

    # Calcul des totaux par semaine (pour la synthèse latérale)
    df_totaux = df.groupby([COL_EMPLOYE, COL_SEMAINE, 'ANNEE'])['Durée du service'].sum().reset_index()
    df_totaux = df_totaux.rename(columns={'Durée du service': 'TEMPS_TOTAL_SEMAINE'})
    
    df = pd.merge(df, df_totaux, on=[COL_EMPLOYE, COL_SEMAINE, 'ANNEE'], how='left')
    df['TEMPS_TOTAL_SEMAINE'] = df['TEMPS_TOTAL_SEMAINE'].fillna(pd.Timedelta(0))
    
    return df

def verifier_donnees(df_semaine):
    """Vérifie la logique des données de planning et retourne une liste d'avertissements."""
    avertissements = []
    df_travail = df_semaine[df_semaine['Durée du service'] > pd.Timedelta(0)].copy()
    
    # 1. Vérification : Heure de début après Heure de fin (sans compter les nuits)
    erreurs_ordre = df_travail[
        (df_travail['Duree_Brute'] < pd.Timedelta(0)) & 
        (df_travail['Duree_Brute'] > pd.Timedelta(days=-1)) 
    ]
    
    if not erreurs_ordre.empty:
        jours = ", ".join(erreurs_ordre[COL_JOUR].unique())
        avertissements.append(f"**Heure inversée :** Les horaires de début et de fin sont inversés pour le(s) jour(s) : **{jours}**. Vérifiez la saisie.")

    # 2. Vérification : Multiples entrées pour le même jour (risque de chevauchement)
    comptage_jours = df_semaine.groupby(COL_JOUR).size()
    multiples_entrees = comptage_jours[comptage_jours > 1]
    
    if not multiples_entrees.empty:
        jours = ", ".join(multiples_entrees.index)
        avertissements.append(f"**Multiples entrées :** Plusieurs lignes de planning trouvées pour le(s) jour(s) : **{jours}**. Risque de chevauchement d'horaires non géré par le calcul (le temps de travail est cumulé).")
    
    return avertissements

def afficher_calendrier(df_employe, mois, annee, employe_connecte, output_container):
    """Affiche un calendrier HTML stylisé dans le conteneur spécifié (st ou st.sidebar)."""
    
    statut_par_jour = defaultdict(lambda: 'Repos')
    
    df_mois = df_employe[
        (df_employe['ANNEE'] == annee) & 
        (df_employe['DATE'].dt.month == mois)
    ].copy()
    
    # Utilisation de la colonne 'Statut' pré-calculée
    for _, row in df_mois.iterrows():
        jour = row['DATE'].day
        # Note: Si plusieurs entrées existent pour un jour, seul le statut de la dernière ligne sera retenu
        statut_par_jour[jour] = row['Statut']


    # 2. Préparer les styles
    styles = {
        'Travail': 'background-color: #CCFFCC; font-weight: bold;', 
        'Repos': 'background-color: #F0F0F0;', 
        'École': 'background-color: #DDEEFF; color: #0000FF;', 
        'Aujourdhui': 'border: 2px solid #FF0000; font-weight: bold; padding: 2px;', 
        'Anniversaire': 'background-color: #FFFF99; font-weight: bold;', 
        'Default': 'background-color: white;'
    }
    
    # 3. Générer le calendrier HTML
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    output_container.header("Vue Mensuelle")
    html_calendar = f"<h4>{calendar.month_name[mois].title()} {annee}</h4>"
    
    # Correction pour forcer l'affichage des 7 colonnes
    html_calendar += "<table style='width: 100%; font-size: 14px; text-align: center; border-collapse: collapse; table-layout: fixed;'>"
    html_calendar += "<thead><tr>"
    
    # Forcer la largeur des en-têtes
    for day_name in ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]:
        html_calendar += f"<th style='width: 14.28%;'>{day_name}</th>"
    html_calendar += "</tr></thead><tbody>"

    aujourdhui = date.today()
    
    # Utilisation des informations mémorisées (date d'anniversaire)
    anniversaire_julien = False
    if employe_connecte in ANNIVERSAIRES:
        mois_anniv, jour_anniv = ANNIVERSAIRES[employe_connecte]
        if mois == mois_anniv:
            anniversaire_julien = True

    for week in cal.monthdays2calendar(annee, mois):
        html_calendar += "<tr>"
        for day_num, weekday in week:
            if day_num == 0:
                html_calendar += "<td style='background-color: #E8E8E8; height: 35px;'></td>" 
                continue
            
            day_date = date(annee, mois, day_num)
            day_status = statut_par_jour[day_num]
            day_style = styles.get(day_status, styles['Default'])
            
            # Application des styles spéciaux
            if day_date == aujourdhui:
                day_style += styles['Aujourdhui']
                
            if anniversaire_julien and day_num == jour_anniv:
                day_style = styles['Anniversaire']
            
            html_calendar += f"<td style='{day_style}; border: 1px solid #DDDDDD; height: 35px;'>{day_num}</td>"
        html_calendar += "</tr>"
    
    html_calendar += "</tbody></table>"
    
    output_container.markdown(html_calendar, unsafe_allow_html=True)
    

# --- FONCTION D'AFFICHAGE DE LA NOTICE (NOUVEAUTÉ) ---

def afficher_notice():
    """Affiche la notice d'utilisation dans un conteneur principal."""
    st.header("Manuel d'Utilisation de l'Application Planning Clichy 📋")
    st.markdown("---")

    st.subheader("1. Connexion Sécurisée")
    st.markdown("""
    * **Identifiant :** Votre prénom (par exemple, JULIEN).
    * **Mot de Passe :** Votre code personnel.
    * Le système vous connecte automatiquement à **votre planning personnel** uniquement.
    """)
    
    st.subheader("2. Navigation et Périodes")
    st.markdown("""
    La navigation se fait dans la **barre latérale gauche**.
    
    * **Période Globale (Année) :** Permet de sélectionner l'année des plannings (si plusieurs années sont disponibles dans le fichier Excel).
    * **Détail Semaine :** Permet de choisir **une ou plusieurs semaines** pour la consultation (pour l'affichage principal, seule la première semaine sélectionnée est utilisée) et pour le téléchargement.
    """)
    
    st.subheader("3. Consultation du Planning")
    
    # Intégration de la légende pour l'affichage
    st.markdown("""
    Le planning principal affiche vos horaires (Début et Fin).
    * **Téléchargement :** Vous pouvez exporter le planning de **toutes les semaines sélectionnées** au format Excel via le bouton **'📥 Télécharger le planning'**.
    """)
    
    st.markdown("---")
    
    st.subheader("4. Légende des Couleurs et Calcul des Heures")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Tableau Principal**")
        st.markdown("""
        * <span style='background-color: #CCFFCC; padding: 2px;'>🟢 Jour en Vert :</span> C'est **Aujourd'hui**.
        * <span style='background-color: #FFFF99; padding: 2px;'>🟡 Jour en Jaune :</span> Votre **Anniversaire** 🎂.
        * <span style='background-color: #F0F0F0; padding: 2px;'>⚪ Jour en Gris :</span> Jour de **Repos** (Temps de service nul).
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Calcul Net d'Heures**")
        st.markdown("""
        * Le **"Total d'heures nettes"** dans la barre latérale calcule la somme des heures de travail de **toutes les semaines sélectionnées**.
        * **Règle de pause :** Pour chaque jour travaillé, **1 heure de pause** est automatiquement déduite du temps de service si la durée brute du service est supérieure à 1 heure.
        """)
    
    st.markdown("---")
    st.info("💡 **Conseil :** N'oubliez pas de vous déconnecter en fin de session via le bouton 'Déconnexion' dans la barre latérale.")


# --- 3. LOGIQUE D'AUTHENTIFICATION ---
# Dictionnaire de MAPPING : Identifiant (UPPER) -> Mot de passe
PASSWORDS = {
    "MOUNIA": "clichy2002",
    "ADAM": "clichy1402",
    "HOUDA": "clichy2701",
    "JULIEN": "1810", 
}
USERNAMES = PASSWORDS.keys() # La liste des utilisateurs est déduite du dictionnaire


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
            # Vérifie si l'utilisateur existe ET si le mot de passe correspond
            if username_input in PASSWORDS and password_input == PASSWORDS[username_input]:
                st.session_state['authenticated'] = True
                st.session_state['username'] = username_input
                st.rerun() 
            else:
                st.error("Identifiant ou mot de passe incorrect.")

# --- FONCTION DE STYLISATION ---
def appliquer_style(row, date_debut_semaine, employe_connecte, statut_map):
    """Applique une couleur de fond à la ligne en fonction du statut (Repos, École, Anniversaire)."""
    styles = [''] * len(row) 
    
    jour_str = row[COL_JOUR] 
    statut = statut_map.get(jour_str, "")
    
    try:
        jour_index = ORDRE_JOURS.index(jour_str) 
        date_ligne = date_debut_semaine + timedelta(days=jour_index)
    except Exception:
        return styles

    # Anniversaire 🥳
    if employe_connecte in ANNIVERSAIRES:
        mois_anniv, jour_anniv = ANNIVERSAIRES[employe_connecte]
        if date_ligne.month == mois_anniv and date_ligne.day == jour_anniv:
            return ['background-color: #FFFF99'] * len(row) 
            
    # Aujourd'hui 🟢
    if date_ligne == date.today():
        return ['background-color: #CCFFCC'] * len(row) 
        
    # Styles secondaires
    if statut == "Repos":
        return ['background-color: #F0F0F0'] * len(row) 
    
    if statut == "École":
        return ['background-color: #DDEEFF'] * len(row) 
    
    return styles
    
# --- FONCTION D'EXPORT MISE À JOUR (Multi-semaines) ---
def to_excel_buffer(df_initial, employe_selectionne, semaines_a_exporter, annee_selectionnee):
    """Crée un buffer Excel en mémoire pour le téléchargement multi-semaines."""
    
    # 1. Filtrer les données pour les semaines sélectionnées
    df_export_data = df_initial[
        (df_initial[COL_SEMAINE].isin(semaines_a_exporter)) & 
        (df_initial[COL_EMPLOYE] == employe_selectionne)
    ].copy()
    
    if df_export_data.empty:
        st.warning("Aucune donnée de planning à exporter pour les semaines sélectionnées.")
        return None
        
    # 2. Calcul du total global
    df_export_data, total_heures_format = calculer_heures_travaillees(df_export_data)
    
    # 3. Préparer le DataFrame final pour l'export
    # Ajout de la colonne SEMAINE en première position et tri par SEMAINE puis JOUR
    df_export = df_export_data[[COL_SEMAINE, COL_JOUR, COL_DEBUT, COL_FIN, 'Durée du service']].copy()
    df_export[COL_JOUR] = pd.Categorical(df_export[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
    df_export = df_export.sort_values(by=[COL_SEMAINE, COL_JOUR])
    df_export.columns = ['Semaine', 'Jour', 'Début', 'Fin', 'Heures Net (Déduites)']
    
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Formats
            time_format = workbook.add_format({'num_format': 'hh:mm'})
            duration_format = workbook.add_format({'num_format': '[h]:mm'})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#DDEEFF', 'border': 1})
            
            # Écriture dans la feuille 'Planning Global'
            worksheet = writer.sheets['Planning']
            
            # Infos de l'en-tête (Lignes 1 à 4)
            worksheet.write('A1', "Export Global Planning", workbook.add_format({'bold': True, 'font_size': 14}))
            worksheet.write('A2', f"Employé: {employe_selectionne.title()}")
            worksheet.write('A3', f"Période: {len(semaines_a_exporter)} semaine(s) de l'année {annee_selectionnee}")
            worksheet.write('A4', f"TOTAL HEURES NETTES sur la période: {total_heures_format}h", workbook.add_format({'bold': True, 'bg_color': '#CCFFCC'}))
            
            # Écriture du DataFrame (Commence à la ligne 6)
            df_export.to_excel(writer, sheet_name='Planning', index=False, startrow=6, header=False)
            
            # Écriture des en-têtes (à la ligne 6) et mise en forme des colonnes
            for col_num, value in enumerate(df_export.columns.values):
                worksheet.write(6, col_num, value, header_format)

            worksheet.set_column('A:A', 10) # Semaine
            worksheet.set_column('B:B', 15) # Jour
            worksheet.set_column('C:D', 12, time_format)  # Début, Fin
            worksheet.set_column('E:E', 20, duration_format) # Heures Net
            
            worksheet.write('A15', "Note: Une heure de pause méridienne est déduite chaque jour si la durée brute du service dépasse 1 heure.")
            
    except ImportError:
          st.error("Erreur d'exportation : Le module 'xlsxwriter' est manquant. Veuillez l'installer (`pip install xlsxwriter`) pour activer le téléchargement Excel.")
          return None 
          
    output.seek(0)
    return output


# --- LOGIQUE PRINCIPALE DE L'APPLICATION ---

if not st.session_state['authenticated']:
    login()
    
else:
    try:
        # 4.1 Affichage du titre principal
        st.markdown("<h1 style='text-align: center; font-size: 48px;'>PLANNING CLICHY</h1>", unsafe_allow_html=True) 
        st.markdown("---") 
        
        # Gestion du logo
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
        employe_connecte = st.session_state['username']
        
        # --- Barre latérale : Informations utilisateur et déconnexion ---
        st.sidebar.markdown(f"**👋 Bienvenue, {employe_connecte.title()}**")
        aujourdhui = date.today()
        
        # Anniversaire 
        anniv_message = ""
        # Personnalisation de l'anniversaire pour l'utilisateur
        if employe_connecte == "JULIEN" and aujourdhui.month == 10 and aujourdhui.day == 18:
            st.sidebar.balloons() 
            anniv_message = "Joyeux Anniversaire ! 🎂"
        elif employe_connecte in ANNIVERSAIRES:
            mois_anniv, jour_anniv = ANNIVERSAIRES[employe_connecte]
            if aujourdhui.month == mois_anniv and aujourdhui.day == jour_anniv:
                 st.sidebar.balloons() 
                 anniv_message = "Joyeux Anniversaire ! 🎂"
        
        if anniv_message:
             st.sidebar.success(anniv_message)

        if st.sidebar.button("Déconnexion"):
            st.session_state['authenticated'] = False
            st.session_state['username'] = None
            st.rerun()
            
        st.sidebar.markdown("---")
        employe_selectionne = employe_connecte
        
        if employe_selectionne not in liste_employes:
            st.error(f"Erreur : Le prénom de connexion ({employe_selectionne}) ne correspond pas à un employé dans le fichier de planning.")
            st.stop()

        df_employe_filtre = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
        
        
        # --- DÉTECTION ET SÉLECTION DE L'ANNÉE (PÉRIODE GLOBALE) ---
        annees_disponibles = sorted(df_employe_filtre['ANNEE'].unique().tolist(), reverse=True)
        if not annees_disponibles:
             annees_disponibles = [date.today().year] 

        annee_defaut = annees_disponibles[0] 

        st.sidebar.header("Période Globale")
        annee_selectionnee = st.sidebar.selectbox(
            'Année du Planning',
            annees_disponibles,
            index=annees_disponibles.index(annee_defaut) if annee_defaut in annees_disponibles else 0
        )
        st.sidebar.markdown("---")
        
        df_employe_annee = df_employe_filtre[df_employe_filtre['ANNEE'] == annee_selectionnee].copy()


        # --- DÉTECTION ET SÉLECTION DE LA SEMAINE (DÉTAIL SEMAINE) ---
        
        df_semaines_travaillees = df_employe_annee[
            df_employe_annee['TEMPS_TOTAL_SEMAINE'] > pd.Timedelta(0)
        ].drop_duplicates(subset=[COL_SEMAINE])
        
        liste_semaines_brutes = sorted(df_semaines_travaillees[COL_SEMAINE].unique().tolist())
        
        if not liste_semaines_brutes:
            st.warning(f"**Attention :** Aucune semaine avec un temps de travail positif n'a été trouvée pour **{employe_selectionne}** en {annee_selectionnee}.")
            st.stop()
        
        # Trouver la semaine actuelle pour la sélection par défaut
        semaine_actuelle_num = aujourdhui.isocalendar()[1]
        semaine_actuelle_brute = f"S{semaine_actuelle_num:02d}" 
        
        try:
            semaine_defaut_brute = semaine_actuelle_brute if semaine_actuelle_brute in liste_semaines_brutes else liste_semaines_brutes[0]
        except IndexError:
            semaine_defaut_brute = None
        
        liste_semaines_formatees = [get_dates_for_week(s, annee_selectionnee, format_type='full') for s in liste_semaines_brutes]
        semaine_mapping = dict(zip(liste_semaines_formatees, liste_semaines_brutes))
        
        
        st.sidebar.header("Détail Semaine") 
        
        # --- DÉFINITION DE LA SÉLECTION PAR DÉFAUT POUR LE MULTISELECT ---
        default_selection = []
        if semaine_defaut_brute:
            semaine_formattee_defaut = get_dates_for_week(semaine_defaut_brute, annee_selectionnee, format_type='full')
            if semaine_formattee_defaut in liste_semaines_formatees:
                 default_selection = [semaine_formattee_defaut]

        # Utilisation de multiselect et rétention de la sélection via st.session_state
        semaines_selectionnees_formattees = st.sidebar.multiselect(
            'Sélectionnez la ou les semaines', 
            liste_semaines_formatees,
            default=st.session_state.get('semaines_selec', default_selection),
            key='semaines_selec_multiselect'
        )
        
        # Mise à jour de la clé de session avec la sélection actuelle
        st.session_state['semaines_selec'] = semaines_selectionnees_formattees

        
        # Récupération des brutes (utilisée pour l'export)
        semaines_selectionnees_brutes = [semaine_mapping.get(s) for s in semaines_selectionnees_formattees if s in semaine_mapping]
        
        
        # --- CONTRÔLE DE L'AFFICHAGE DU CORPS PRINCIPAL ---
        if not semaines_selectionnees_brutes:
            # Si aucune semaine n'est sélectionnée, on affiche l'avertissement et le total à zéro
            st.info("Veuillez sélectionner au moins une semaine dans la barre latérale pour afficher le planning détaillé et le bouton de téléchargement.")
            
            st.sidebar.markdown("### Total d'heures nettes")
            st.sidebar.markdown(f"**Période sélectionnée (0 sem.):**")
            st.sidebar.markdown(f"<h2 style='text-align: center; color: #1E90FF; margin-top: -10px;'>0h 00</h2>", unsafe_allow_html=True)
            st.sidebar.markdown("<p style='text-align: center; font-size: small; margin-top: -15px;'>*Une heure de pause déduite par jour travaillé*</p>", unsafe_allow_html=True)
            st.sidebar.markdown("---") 
            st.stop()


        # Détermination de la semaine à afficher dans le corps principal (la première de la sélection)
        semaine_pour_affichage_brute = semaines_selectionnees_brutes[0]
        
        
        # --- CALCUL ET AFFICHAGE DU TOTAL D'HEURES NETTES (SIDEBAR) ---
        # Le calcul du total utilise TOUTES les semaines sélectionnées
        df_filtre_total = df_employe_annee[df_employe_annee[COL_SEMAINE].isin(semaines_selectionnees_brutes)].copy()
        df_temp, total_heures_format = calculer_heures_travaillees(df_filtre_total)
        
        st.sidebar.markdown("### Total d'heures nettes")
        st.sidebar.markdown(f"**Période sélectionnée ({len(semaines_selectionnees_brutes)} sem.):**")
        st.sidebar.markdown(f"<h2 style='text-align: center; color: #1E90FF; margin-top: -10px;'>{total_heures_format}h</h2>", unsafe_allow_html=True)
        st.sidebar.markdown("<p style='text-align: center; font-size: small; margin-top: -15px;'>*Une heure de pause déduite par jour travaillé*</p>", unsafe_allow_html=True)
        st.sidebar.markdown("---") # Séparateur final
        
        
        # --- GESTION PAR ONGLETS ---
        tab_planning, tab_notice = st.tabs(["📅 Mon Planning", "ℹ️ Notice d'Utilisation"])

        with tab_notice:
            afficher_notice()

        with tab_planning:
            
            # --- CALCUL DU MOIS POUR LE CALENDRIER ---
            mois_selectionne, annee_calendrier = get_dates_for_week(
                semaine_pour_affichage_brute, 
                annee_selectionnee, 
                format_type='month'
            )
            
            # 4.3 AFFICHAGE DU CALENDRIER
            afficher_calendrier(
                df_employe_filtre, 
                mois_selectionne, 
                annee_calendrier, 
                employe_connecte, 
                st 
            )
            
            st.markdown("---") # SÉPARATEUR AJOUTÉ APRÈS LE CALENDRIER

            # 4.4 Affichage du planning principal (détail de la première semaine sélectionnée)
            
            date_debut_semaine = get_dates_for_week(semaine_pour_affichage_brute, annee_selectionnee, format_type='start_date')
            dates_pour_affichage = get_dates_for_week(semaine_pour_affichage_brute, annee_selectionnee, format_type='only_dates')
            st.markdown(f"<h3 style='text-align: center;'>Semaine détaillée : {dates_pour_affichage}</h3>", unsafe_allow_html=True)
            st.markdown("---")
            
            # Filtrer pour le tableau d'affichage (une seule semaine)
            df_filtre_affichage = df_employe_annee[df_employe_annee[COL_SEMAINE] == semaine_pour_affichage_brute].copy()
            df_filtre_affichage[COL_JOUR] = pd.Categorical(df_filtre_affichage[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
            df_filtre_affichage = df_filtre_affichage.sort_values(by=[COL_JOUR])
            
            # Calculer les heures pour l'affichage (non utilisé mais pour la complétude)
            df_resultat_affichage, total_heures_semaine = calculer_heures_travaillees(df_filtre_affichage)
            
            
            # Affichage des avertissements 
            avertissements = verifier_donnees(df_resultat_affichage)
            if avertissements:
                for alerte in avertissements:
                    st.warning(alerte)
            st.markdown("---")
            
            # Préparation du DataFrame pour l'affichage
            statut_map = df_resultat_affichage.set_index(COL_JOUR)['Statut'].to_dict()

            df_affichage = df_resultat_affichage[[COL_JOUR, COL_DEBUT, COL_FIN]].copy()
            
            # --- CORRECTION DE LA LOGIQUE DE FORMATAGE DES HEURES POUR L'AFFICHAGE ---
            def formater_heure_ou_statut_pour_tableau(row, col_name):
                # Si le statut est Repos ou École, afficher le statut dans la colonne Début
                if row['Statut'] in ["Repos", "École"]:
                    return row['Statut'] if col_name == COL_DEBUT else ""
                
                # Sinon, formater l'heure
                val = row[col_name]
                if pd.isna(val) or val == "":
                    return ""
                    
                # Si c'est un objet Python time ou str (l'heure initiale du Excel)
                if isinstance(val, (time, str)):
                     return str(val)
                # Si c'est un Timedelta (le résultat de la conversion pour le calcul), essayer de formater en hh:mm
                if isinstance(val, pd.Timedelta):
                    seconds = val.total_seconds()
                    heures = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    return f"{heures:02d}:{minutes:02d}"
                
                # Dernière tentative de conversion en str
                return str(val)

            # Application des heures nettes (avec déduction de pause)
            df_affichage['Pause Déduite (Net)'] = df_resultat_affichage.apply(
                lambda row: "1h 00" if row['Duree_Brute'] > pd.Timedelta(hours=1) and row['Statut'] == "Travail" else "", axis=1
            )
            
            df_affichage[COL_DEBUT] = df_resultat_affichage.apply(
                lambda row: formater_heure_ou_statut_pour_tableau(row, COL_DEBUT), axis=1
            )
            df_affichage[COL_FIN] = df_resultat_affichage.apply(
                lambda row: formater_heure_ou_statut_pour_tableau(row, COL_FIN), axis=1
            )

            df_affichage.columns = ['Jour', 'Début / Statut', 'Fin', 'Pause Déduite (Net)'] # Renommer les colonnes pour l'affichage
            
            st.subheader(f"Planning pour **{employe_selectionne.title()}**")
            
            # Bouton de téléchargement MULTI-SEMAINE (Doit être affiché ici)
            if semaines_selectionnees_brutes:
                excel_buffer = to_excel_buffer(
                    df_initial, 
                    employe_selectionne, 
                    semaines_selectionnees_brutes,
                    annee_selectionnee
                )
                
                if excel_buffer:
                    st.download_button(
                        label=f"📥 Télécharger les {len(semaines_selectionnees_brutes)} semaines (Excel)",
                        data=excel_buffer,
                        file_name=f"Planning_Global_{employe_selectionne.title()}_{annee_selectionnee}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Télécharge toutes les semaines sélectionnées dans un fichier Excel (.xlsx)."
                    )

                st.markdown("---")
            
            # --- AFFICHAGE FINAL DU DATAFRAME ---
            styled_df = df_affichage.style.apply(
                appliquer_style,
                axis=1,
                date_debut_semaine=date_debut_semaine,
                employe_connecte=employe_selectionne,
                statut_map=statut_map 
            )
            
            st.dataframe(
                styled_df, 
                use_container_width=True,
                column_config={
                    'Jour': st.column_config.Column("Jour", width="large"),
                    'Début / Statut': st.column_config.Column("Début / Statut"), 
                    'Fin': st.column_config.Column("Fin"),
                    'Pause Déduite (Net)': st.column_config.Column("Pause Déduite (Net)"),
                },
                hide_index=True
            )
            
            st.markdown("""
            **Légende :**
            - <span style='background-color: #CCFFCC; padding: 2px;'>🟢 Aujourd'hui</span>
            - <span style='background-color: #FFFF99; padding: 2px;'>🟡 Anniversaire</span>
            - <span style='background-color: #F0F0F0; padding: 2px;'>⚪ Repos</span>
            <br>
            *Le calcul déduit **une heure de pause** chaque jour travaillé.*
            """, unsafe_allow_html=True)
            
    except Exception as e:
        # st.error(f"Une erreur fatale s'est produite : {e}") 
        pass