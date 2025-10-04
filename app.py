import pandas as pd
import streamlit as st
import datetime
import csv # Nécessaire pour le paramètre quoting=3

# --- CONFIGURATION DU FICHIER CORRIGÉE ---
# 🔑 CORRECTION N°1 : Nom exact du fichier
NOM_DU_FICHIER = "planning.xlsx"

# 🔑 CORRECTION N°2 : Séparateur. On utilise la virgule dans le read_csv.
# On garde cette variable pour référence, mais le paramètre de lecture est corrigé.
SEPARATEUR_CSV = ',' 

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
    
    df_planning = df_planning.fillna({COL_DEBUT: '00:00:00', COL_FIN: '00:00:00'})

    try:
        # Convertir les colonnes d'heures en objets TimeDelta (durée)
        df_planning['Duree_Debut'] = pd.to_timedelta(df_planning[COL_DEBUT].astype(str).str.strip())
        df_planning['Duree_Fin'] = pd.to_timedelta(df_planning[COL_FIN].astype(str).str.strip())
        
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
            return duree

        df_planning['Durée du service'] = df_planning.apply(calculer_duree, axis=1)
        
        total_duree = df_planning[df_planning['Durée du service'] > pd.Timedelta(0)]['Durée du service'].sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception:
        return df_planning, "Erreur de calcul"


# --- FONCTION DE CHARGEMENT DES DONNÉES (CORRIGÉE DÉFINITIVE) ---

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier CSV une seule fois et nettoie les données."""
    try:
        # 🔑 CORRECTION N°3 : sep=',' + quoting=3 pour ignorer les guillemets et résoudre l'erreur
        df = pd.read_csv(
            fichier, 
            sep=',', 
            encoding='latin-1', 
            engine='python', 
            skipinitialspace=True, 
            quoting=csv.QUOTE_NONE # Équivalent à quoting=3
        )
        
        # Nettoyage des noms de colonnes et des données
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                
        # Supprimer les lignes vides
        df = df.dropna(how='all')
            
        # Créer une colonne pour l'affichage
        df['SEMAINE ET JOUR'] = df[COL_SEMAINE].astype(str) + ' - ' + df[COL_JOUR].astype(str)
        
        return df
    
    except FileNotFoundError:
        st.error(f"""
        **ERREUR CRITIQUE : Fichier non trouvé.**
        Le fichier de données nommé `{fichier}` doit être dans le même répertoire que `app.py` sur GitHub.
        """)
        st.stop()
        
    except UnicodeDecodeError:
        st.error(f"""
        **ERREUR D'ENCODAGE : Caractères illisibles.**
        L'application n'a pas pu lire le fichier (encodage 'latin-1').
        """)
        st.stop()

    except pd.errors.ParserError as e:
        st.error(f"""
        **ERREUR DE LECTURE DU FICHIER : Séparateur ou structure incorrecte.**
        Le fichier semble être mal formaté. Détails: {e}
        """)
        st.stop()
        
    except Exception as e:
        st.error(f"Impossible de charger le fichier CSV. Erreur générale: {e}")
        st.stop()


# --- INTERFACE STREAMLIT PRINCIPALE ---

st.set_page_config(page_title="Planning Employé", layout="wide")
st.title("🕒 Application de Consultation de Planning")
st.markdown("---")


try:
    # 1. Charger les données (Note : on ne passe plus le séparateur en argument)
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
        
        # --- AFFICHAGE PRINCIPAL ---
        
        st.metric(
            label="Total des heures cumulées", 
            value=total_heures_format,
            delta=f"sur {len(df_resultat[df_resultat['Durée du service'] > pd.Timedelta(0)])} services trouvés",
            delta_color="off"
        )
        
        st.subheader(f"Détail des services pour {employe_selectionne}")
