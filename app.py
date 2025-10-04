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
    
    # Remplissage initial pour éviter les erreurs de conversion au format HH:MM:SS
    df_planning = df_planning.fillna({COL_DEBUT: '00:00:00', COL_FIN: '00:00:00'})

    try:
        # Fonction robuste pour convertir les valeurs d'heure
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
        
        # 🔑 CORRECTION : Convertir explicitement 'Durée du service' en Timedelta avant la comparaison/somme
        df_planning['Durée du service'] = pd.to_timedelta(df_planning['Durée du service'], errors='coerce')
        
        # Filtrer et sommer les durées valides
        total_duree = df_planning[df_planning['Durée du service'] > pd.Timedelta(0)]['Durée du service'].sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception as e:
        # En cas d'erreur irrécupérable dans le calcul, journaliser l'erreur et continuer
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
        for col in df.columns:
            if df[col].dtype == 'object':
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
        # Gestion des valeurs non-Timedelta (NaN/NaT) qui peuvent survenir
        def format_duration(x):
            if pd.isna(x) or x.total_seconds() <= 0:
                return ""
            h = int(x.total_seconds() // 3600)
            m = int((x.total_seconds() % 3600) // 60)
            return f"{h:02d}:{m:02d}"
            
        df_resultat['Durée du service (Affichage)'] = df_resultat['Durée du service'].apply(format_duration)
        
        # --- AFFICHAGE PRINCIPAL ---
        
        st.metric(
            label="Total des heures cumulées", 
            value=total_heures_format,
            delta=f"sur {len(df_resultat[df_resultat['Durée du service'] > pd.Timedelta(0)])} services trouvés",
            delta_color="off"
        )
        
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
