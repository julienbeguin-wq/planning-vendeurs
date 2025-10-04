import pandas as pd
import streamlit as st
import datetime

# --- CONFIGURATION DU FICHIER ---
# Nom exact du fichier Excel (doit être au format .xlsx)
NOM_DU_FICHIER = "planningss.xlsx"

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
        
        # Le calcul du total est maintenu ici, même s'il n'est pas affiché
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
        
        # S'assurer que les jours sont en majuscules pour le tri
        df[COL_JOUR] = df[COL_JOUR].astype(str).str.upper()
            
        # Créer une colonne pour l'affichage
        df['SEMAINE ET JOUR'] = df[COL_SEMAINE].astype(str) + ' - ' + df[COL_JOUR].astype(str)
        
        return df
    
    except FileNotFoundError:
        st.error(f"""
        **ERREUR CRITIQUE : Fichier non trouvé.**
        Le fichier de données nommé `{fichier}` doit être dans le même répertoire que `app.py` sur GitHub.
        """)
        st.stop()
        
    except Exception as e:
        st.error(f"Impossible de charger le fichier Excel. Détails: {e}. Vérifiez que le fichier '{fichier}' est bien au format .xlsx.")
        st.stop()


# --- INTERFACE STREAMLIT PRINCIPALE ---

st.set_page_config(page_title="Planning Employé", layout="wide")
st.title("🕒 Application de Consultation de Planning")
st.markdown("---")


try:
    # 1. Charger les données 
    df_initial = charger_donnees(NOM_DU_FICHIER)
    
    # 2. Préparer la liste des employés uniques
    liste_employes = sorted(df_initial[COL_EMPLOYE].unique().tolist())
    
    # 3. Créer le menu déroulant sur le côté (Sidebar)
    st.sidebar.header("Sélectionnez votre profil")
    employe_selectionne = st.sidebar.selectbox(
        'Qui êtes-vous ?',
        liste_employes
    )

    # 4. Afficher les résultats pour l'employé sélectionné
    if employe_selectionne:
        
        df_employe = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
        
        # Trier par Semaine, puis par ordre logique des Jours
        df_employe[COL_JOUR] = pd.Categorical(df_employe[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
        df_employe = df_employe.sort_values(by=[COL_SEMAINE, COL_JOUR])
        
        # Calculer les heures
        df_resultat, total_heures_format = calculer_heures_travaillees(df_employe)
        
        # FIX ULTIME : Convertir la durée en chaîne formatée (HH:mm)
        def format_duration(x):
            if pd.isna(x) or x.total_seconds() <= 0:
                return ""
            h = int(x.total_seconds() // 3600)
            m = int((x.total_seconds() % 3600) // 60)
            return f"{h:02d}:{m:02d}"
            
        df_resultat['Durée du service (Affichage)'] = df_resultat['Durée du service'].apply(format_duration)
        
        # --- AFFICHAGE PRINCIPAL ---
        
        st.subheader(f"Détail des services pour {employe_selectionne}")
        
        # Affichage du tableau de planning
        st.dataframe(
            df_resultat[['SEMAINE ET JOUR', COL_DEBUT, COL_FIN, 'Durée du service (Affichage)']],
            use_container_width=True,
            column_config={
                "SEMAINE ET JOUR": st.column_config.Column("Semaine et Jour", width="large"),
                COL_DEBUT: st.column_config.Column("Début"),
                COL_FIN: st.column_config.Column("Fin"),
                "Durée du service (Affichage)": "Durée du service" 
            },
            hide_index=True
        )
        
except Exception as e:
    st.error(f"Une erreur inattendue est survenue au lancement : {e}")
