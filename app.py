import pandas as pd
import streamlit as st
import datetime

# --- CONFIGURATION DU FICHIER ---
# Nom exact de votre fichier CSV
NOM_DU_FICHIER = "planning.xlsx"
# Le séparateur est souvent la virgule (,) pour ce type de fichier
SEPARATEUR_CSV = ',' 

# Noms des colonnes (headers) de votre fichier - DOIVENT CORRESPONDRE
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
    
    # Remplacer les heures vides/manquantes par un temps nul (pour éviter les erreurs de calcul)
    df_planning = df_planning.fillna({COL_DEBUT: '00:00:00', COL_FIN: '00:00:00'})

    try:
        # Convertir les colonnes d'heures en objets TimeDelta (durée)
        df_planning['Duree_Debut'] = pd.to_timedelta(df_planning[COL_DEBUT].astype(str).str.strip())
        df_planning['Duree_Fin'] = pd.to_timedelta(df_planning[COL_FIN].astype(str).str.strip())
        
        # Calculer la durée du service
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            
            # Gérer les services qui passent minuit (la durée est négative et doit être augmentée de 24h)
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
                
            return duree

        df_planning['Durée du service'] = df_planning.apply(calculer_duree, axis=1)
        
        # Calculer le total général (en ignorant les services de 0h)
        total_duree = df_planning[df_planning['Durée du service'] > pd.Timedelta(0)]['Durée du service'].sum()
        
        # Formater le résultat en heures et minutes (HHh MMmin)
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception as e:
        # En cas d'erreur de formatage (si les heures ne sont pas HH:MM:SS)
        return df_planning, "Erreur de calcul"
    import streamlit as st
import pandas as pd

# Nom de fichier exact
FILE_NAME = 'planning.xlsx - De la S41 à la S52.csv'

st.set_page_config(layout="wide", page_title="Planification Vendeurs")
st.title("Tableau de bord de Planification")

try:
    # 🔑 CORRECTION DE L'ENCODAGE: On passe l'argument 'encoding' à 'latin-1'
    df = pd.read_csv(FILE_NAME, encoding='latin-1')
    
    # Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()
    
    st.success(f"Fichier '{FILE_NAME}' chargé avec succès en utilisant l'encodage latin-1 !")
    
    # Affichage des premières lignes pour confirmation
    st.dataframe(df.head())
    
    # ... votre code Streamlit continue ici ...
    
except FileNotFoundError:
    st.error(f"""
    **ERREUR : Fichier non trouvé.**
    Le fichier nommé `{FILE_NAME}` est introuvable.
    """)
except UnicodeDecodeError as e:
    st.error(f"""
    **ERREUR : Problème d'encodage (Unicode Decode Error).**
    Le fichier CSV n'a pas pu être lu. Tentez d'utiliser un autre encodage si 'latin-1' ne fonctionne pas (ex: 'windows-1252').
    Détails: {e}
    """)
except Exception as e:
    st.error(f"Une autre erreur est survenue lors du traitement du fichier : {e}")

# --- INTERFACE STREAMLIT PRINCIPALE ---

st.set_page_config(page_title="Planning Employé", layout="wide")
st.title("🕒 Application de Consultation de Planning")
st.markdown("---")


@st.cache_data
def charger_donnees(fichier, separateur):
    """Charge le fichier CSV une seule fois et nettoie les données."""
    try:
        df = pd.read_csv(fichier, sep=separateur, skipinitialspace=True)
        
        # Nettoyage des noms de colonnes et des données (gestion des espaces)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                
        # Supprimer les lignes qui n'ont aucune donnée
        df = df.dropna(how='all')
                
        # Créer une colonne pour l'affichage : "S41 - LUNDI"
        df['SEMAINE ET JOUR'] = df[COL_SEMAINE] + ' - ' + df[COL_JOUR]
        
        return df
    except Exception as e:
        st.error(f"Impossible de charger le fichier CSV. Vérifiez le nom du fichier et le séparateur. Détails: {e}")
        st.stop()
        
try:
    # 1. Charger les données (Point de départ)
    df_initial = charger_donnees(NOM_DU_FICHIER, SEPARATEUR_CSV)
    
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
        
        # Affichage du tableau de planning
        st.dataframe(
            df_resultat[['SEMAINE ET JOUR', COL_DEBUT, COL_FIN, 'Durée du service']],
            use_container_width=True,
            column_config={
                "SEMAINE ET JOUR": st.column_config.Column("Semaine et Jour", width="large"),
                COL_DEBUT: st.column_config.Column("Début"),
                COL_FIN: st.column_config.Column("Fin"),
                "Durée du service": st.column_config.DurationColumn("Durée", format="HH:mm")
            },
            hide_index=True
        )
    
except Exception as e:
    st.error(f"Le lancement a échoué. Assurez-vous que Conda est activé et que les fichiers sont au bon endroit. Erreur générale: {e}")

# --- FIN DU CODE ---
