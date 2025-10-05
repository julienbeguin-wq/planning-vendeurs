import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta
import yaml 
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
# NOUVEL IMPORT NÉCESSAIRE pour le contournement du hachage
from passlib.context import CryptContext

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
passwords_clairs = ['password123', 'autre_mdp'] 

# 2. GÉNÉRER LES MOTS DE PASSE CRYPTÉS (HASHÉS)
# CONTOURNEMENT de l'erreur Hasher : Utilisation directe de passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_passwords = [pwd_context.hash(pwd) for pwd in passwords_clairs]
# -------------------------------------------------------------

config = {
    'cookie': {
        'expiry_days': 30,
        'key': 'random_secret_key_please_change_this', 
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
# ... (le reste de cette fonction n'a pas changé)
    """Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin (Lundi-Dimanche)."""
    
    MONTHS = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
        7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    try:
        # Premier bloc try: pour la conversion du numéro de semaine
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str

    try:
        # Second bloc try: pour le calcul des dates
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
# ... (le reste de cette fonction n'a pas changé)
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
            # DÉDUCTION DE LA PAUSE DÉJEUNER (1 heure) si la durée est > 1h
            if duree > pd.Timedelta(hours=1):
                duree -= pd.Timedelta(hours=1) 
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
# ... (le reste de cette fonction n'a pas changé)
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
        if df[col].dtype == 'object' or df[col].dtype.name == 'category': 
            df[col] = df[col].astype(str).str.strip()
            
    df = df.dropna(how='all')
    df[COL_JOUR] = df[COL_JOUR].astype(str).str.upper()
    df[COL_SEMAINE] = df[COL_SEMAINE].astype(str).str.upper()
    df['SEMAINE ET JOUR'] = df[COL_SEMAINE].astype(str) + ' - ' + df[COL_JOUR].astype(str)
    
    return df


# --- INTERFACE STREAMLIT PRINCIPALE AVEC AUTHENTIFICATION ---

st.set_page_config(page_title="Planning Employé", layout="wide")

# NOUVEAU : Initialisation de l'authentification
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Affichage du formulaire de connexion
name, authentication_status, username = authenticator.login('Login', 'main')

# --- LOGIQUE POST-CONNEXION ---

if st.session_state["authentication_status"]:
    # L'utilisateur est connecté

    # 1. Affichage du Header personnalisé et du bouton de déconnexion
    st.sidebar.markdown(f"Bienvenue **{name}**")
    authenticator.logout('Déconnexion', 'sidebar') 
    
    # Gestion de l'affichage du logo
    try:
        st.logo(NOM_DU_LOGO, icon_image=NOM_DU_LOGO) 
    except AttributeError:
        # Pour les anciennes versions de Streamlit sans st.logo
        if NOM_DU_LOGO and st.sidebar:
            st.sidebar.image(NOM_DU_LOGO, use_column_width=True)
    except Exception:
         # Gère l'erreur si le fichier n'est pas trouvé
         st.sidebar.warning(f"Logo '{NOM_DU_LOGO}' non trouvé.")


    st.markdown("<h1 style='text-align: center;'>Application de Consultation de Planning</h1>", unsafe_allow_html=True)
    st.markdown("---")


    try:
        # 2. Charger les données (Le reste de votre application)
        df_initial = charger_donnees(NOM_DU_FICHIER)
        
        liste_employes = sorted(df_initial[COL_EMPLOYE].unique().tolist())
        
        if not liste_employes or (len(liste_employes) == 1 and str(liste_employes[0]).upper() in ['', 'NAN', 'NONE', 'N/A']):
            st.error(f"**ERREUR DE DONNÉES :** La colonne des employés (`'{COL_EMPLOYE}'`) est vide ou mal nommée.")
            st.stop()

        liste_semaines_brutes = sorted(df_initial[COL_SEMAINE].unique().tolist())
        liste_semaines_formatees = [get_dates_for_week(s) for s in liste_semaines_brutes]
        semaine_mapping = dict(zip(liste_semaines_formatees, liste_semaines_brutes))
        
        # 3. Créer les menus déroulants dans le côté (Sidebar)
        st.sidebar.header("Sélections")
        
        employe_selectionne = st.sidebar.selectbox(
            'Sélectionnez l\'employé',
            liste_employes
        )

        semaine_selectionnee_formattee = st.sidebar.selectbox(
            'Sélectionnez la semaine',
            liste_semaines_formatees
        )
        
        semaine_selectionnee_brute = semaine_mapping.get(semaine_selectionnee_formattee)

        # 4. Afficher les résultats pour l'employé et la semaine sélectionnés
        if employe_selectionne and semaine_selectionnee_brute:
            
            # Filtrer par employé et par semaine
            df_employe = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
            df_filtre = df_employe[df_employe[COL_SEMAINE] == semaine_selectionnee_brute].copy()
            
            # GESTION DE L'EXCEPTION NOËL (JEUDI S52)
            if semaine_selectionnee_brute == 'S52':
                df_filtre_avant = len(df_filtre)
                df_filtre = df_filtre[df_filtre[COL_JOUR] != 'JEUDI'].copy()
                
                if len(df_filtre) < df_filtre_avant:
                    st.info(f"Note: Le **Jeudi** de la semaine S52 a été retiré (Jour de Noël).")

            # Trier par Jour logique
            df_filtre[COL_JOUR] = pd.Categorical(df_filtre[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
            df_filtre = df_filtre.sort_values(by=[COL_JOUR])
            
            # Calculer les heures
            df_resultat, total_heures_format = calculer_heures_travaillees(df_filtre)
            
            st.subheader(f"Planning pour **{employe_selectionne}** - {semaine_selectionnee_formattee}")
            
            # Affichage du tableau de planning
            st.dataframe(
                df_resultat[[COL_JOUR, COL_DEBUT, COL_FIN, 'Durée du service']], 
                use_container_width=True,
                column_config={
                    COL_JOUR: st.column_config.Column("Jour", width="large"),
                    COL_DEBUT: st.column_config.Column("Début"),
                    COL_FIN: st.column_config.Column("Fin"),
                    'Durée du service': st.column_config.Column("Durée Nette"),
                },
                hide_index=True
            )
            
            # Ligne de TOTAL
            st.markdown(f"***")
            st.markdown(f"**TOTAL de la semaine pour {employe_selectionne} :** **{total_heures_format}**")
            
    except Exception as e:
        st.error(f"Une erreur inattendue est survenue : {e}")

elif st.session_state["authentication_status"] is False:
    # L'utilisateur a échoué à se connecter
    st.error('Identifiant/mot de passe incorrect')

elif st.session_state["authentication_status"] is None:
    # L'utilisateur n'a pas encore entré d'informations
    st.warning('Veuillez entrer votre identifiant et mot de passe pour accéder.')