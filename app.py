import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta
import yaml 
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# --- CONFIGURATION DU FICHIER ---
# ... (Configuration inchangée)
# --- CONFIGURATION D'AUTHENTIFICATION ---
# ... (Configuration inchangée)
# --- FONCTIONS (inchangées) ---
# ... (Fonctions inchangées)

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
# 💥 LIGNE 155 : Stockage du résultat dans une seule variable temporaire pour éviter le 'cannot unpack'
auth_result = authenticator.login(location='main') 

# LIGNE 156 : Affectation CONDITIONNELLE des variables
if auth_result is not None:
    name, authentication_status, username = auth_result
else:
    # Si la fonction retourne None, on s'assure que les variables sont initialisées
    authentication_status = None 
    name = None
    username = None

# --- LOGIQUE POST-CONNEXION ---

if st.session_state.get("authentication_status") is True: # Utilisez .get pour plus de sûreté
    # L'utilisateur est connecté

    # 1. Affichage du Header personnalisé et du bouton de déconnexion
    st.sidebar.markdown(f"Bienvenue **{name}**")
    authenticator.logout('Déconnexion', 'sidebar') 
    
    # ... (Reste du code de l'application) ...
    st.markdown("<h1 style='text-align: center;'>Application de Consultation de Planning</h1>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        df_initial = charger_donnees(NOM_DU_FICHIER)
        liste_employes = sorted(df_initial['NOM VENDEUR'].unique().tolist())
        
        if not liste_employes or (len(liste_employes) == 1 and str(liste_employes[0]).upper() in ['', 'NAN', 'NONE', 'N/A']):
            st.error(f"**ERREUR DE DONNÉES :** La colonne des employés (`'{COL_EMPLOYE}'`) est vide ou mal nommée.")
            st.stop()

        liste_semaines_brutes = sorted(df_initial[COL_SEMAINE].unique().tolist())
        liste_semaines_formatees = [get_dates_for_week(s) for s in liste_semaines_brutes]
        semaine_mapping = dict(zip(liste_semaines_formatees, liste_semaines_brutes))
        
        st.sidebar.header("Sélections")
        employe_selectionne = st.sidebar.selectbox('Sélectionnez l\'employé', liste_employes)
        semaine_selectionnee_formattee = st.sidebar.selectbox('Sélectionnez la semaine', liste_semaines_formatees)
        semaine_selectionnee_brute = semaine_mapping.get(semaine_selectionnee_formattee)

        if employe_selectionne and semaine_selectionnee_brute:
            df_employe = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
            df_filtre = df_employe[df_employe[COL_SEMAINE] == semaine_selectionnee_brute].copy()
            
            if semaine_selectionnee_brute == 'S52':
                df_filtre_avant = len(df_filtre)
                df_filtre = df_filtre[df_filtre[COL_JOUR] != 'JEUDI'].copy()
                if len(df_filtre) < df_filtre_avant:
                    st.info(f"Note: Le **Jeudi** de la semaine S52 a été retiré (Jour de Noël).")

            df_filtre[COL_JOUR] = pd.Categorical(df_filtre[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
            df_filtre = df_filtre.sort_values(by=[COL_JOUR])
            
            df_resultat, total_heures_format = calculer_heures_travaillees(df_filtre)
            
            st.subheader(f"Planning pour **{employe_selectionne}** - {semaine_selectionnee_formattee}")
            
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
            st.markdown(f"***")
            st.markdown(f"**TOTAL de la semaine pour {employe_selectionne} :** **{total_heures_format}**")
            
    except Exception as e:
        st.error(f"Une erreur inattendue est survenue : {e}")

elif authentication_status is False:
    # L'utilisateur a échoué à se connecter
    st.error('Identifiant/mot de passe incorrect')

elif authentication_status is None:
    # L'utilisateur n'a pas encore entré d'informations (ou l'appel a retourné None)
    st.markdown("<h1 style='text-align: center;'>Connexion</h1>", unsafe_allow_html=True)
    st.warning('Veuillez entrer votre identifiant et mot de passe pour accéder.')