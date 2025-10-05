import pandas as pd
import streamlit as st
from datetime import date, timedelta, time
import numpy as np
import io

# --- 1. CONFIGURATION ET CONSTANTES ---

NOM_DU_FICHIER = "planningss.xlsx"
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
    """Convertit un Timedelta en format 'Hh MMmin' lisible, ou 'Repos'."""
    if td == pd.Timedelta(0) or pd.isna(td):
        return "Repos"
    
    total_seconds = td.total_seconds()
    heures = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    if heures == 0 and minutes == 0: 
        return "Repos"
    
    return f"{heures}h {minutes:02d}min"


def get_dates_for_week(week_str, year=2025):
    """Calcule la plage de dates pour l'affichage de la semaine."""
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
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        date_debut_str = f"{date_debut.day} {MONTHS[date_debut.month]}"
        date_fin_str = f"{date_fin.day} {MONTHS[date_fin.month]}"
        return f"{week_str} : du {date_debut_str} au {date_fin_str}"
    except Exception:
        return week_str

def convertir_heure_en_timedelta(val):
    """Convertit diverses entrées d'heure (time, float Excel, str) en timedelta."""
    if pd.isna(val) or val == "":
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

def calculer_heures_travaillees(df_planning):
    """Calcule la durée de travail nette (avec 1h de pause si > 1h)."""
    df_planning_calc = df_planning.copy()
    
    df_planning_calc['Duree_Debut'] = df_planning_calc[COL_DEBUT].apply(convertir_heure_en_timedelta)
    df_planning_calc['Duree_Fin'] = df_planning_calc[COL_FIN].apply(convertir_heure_en_timedelta)
    
    try:
        def calculer_duree(row):
            if pd.isna(row['Duree_Debut']) or pd.isna(row['Duree_Fin']):
                return pd.Timedelta(0) 
            
            duree = row['Duree_Fin'] - row['Duree_Debut']
            
            if duree < pd.Timedelta(0): 
                duree += pd.Timedelta(days=1)
                
            if duree > pd.Timedelta(hours=1): 
                duree -= pd.Timedelta(hours=1)
                
            if duree < pd.Timedelta(0): return pd.Timedelta(0)
            return duree

        df_planning_calc['Durée du service'] = df_planning_calc.apply(calculer_duree, axis=1)
        df_planning['Durée du service'] = df_planning_calc['Durée du service'] 

        # Calcul du total des heures nettes
        durees_positives = df_planning_calc[df_planning_calc['Durée du service'] > pd.Timedelta(0)]['Durée du service']
        total_duree = durees_positives.sum()
        
        # Formatage du total
        total_heures_format = formater_duree(total_duree).replace("min", "") 
        
        return df_planning, total_heures_format
        
    except Exception as e:
        df_planning['Durée du service'] = pd.NaT
        return df_planning, f"Erreur de calcul: {e}"

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier (Excel ou CSV), vérifie les colonnes et nettoie les données."""
    try:
        df = pd.read_excel(fichier)
    except FileNotFoundError:
        st.error(f"**ERREUR CRITIQUE : Fichier non trouvé.** Assurez-vous que `{fichier}` est dans le même répertoire que `app.py`.")
        st.stop()
    except Exception:
        try:
            df = pd.read_csv(fichier, sep=';', encoding='latin1')
        except Exception:
            try:
                df = pd.read_csv(fichier, encoding='latin1') 
            except Exception as e_final:
                st.error(f"**ERREUR CRITIQUE : Impossible de lire le fichier de données.** Vérifiez le format (Excel, CSV) et le contenu de `{fichier}`.")
                st.stop()
    
    df.columns = df.columns.str.strip()
    
    colonnes_manquantes = [col for col in COLONNES_OBLIGATOIRES if col not in df.columns]
    
    if colonnes_manquantes:
        st.error(f"**ERREUR DE DONNÉES : Colonnes manquantes.** Votre fichier doit contenir les colonnes suivantes : {', '.join(COLONNES_OBLIGATOIRES)}. Colonnes manquantes : {', '.join(colonnes_manquantes)}")
        st.stop()
        
    df[COL_DEBUT] = df[COL_DEBUT].fillna('') 
    df[COL_FIN] = df[COL_FIN].fillna('')

    for col in df.columns:
        if df[col].dtype == 'object' or df[col].dtype.name == 'category': 
            df[col] = df[col].astype(str).str.strip()
            
    df = df.dropna(how='all')
    df[COL_JOUR] = df[COL_JOUR].astype(str).str.upper()
    df[COL_SEMAINE] = df[COL_SEMAINE].astype(str).str.upper()
    
    return df

# --- 3. INTERFACE STREAMLIT PRINCIPALE ---

st.set_page_config(page_title="Planning Employé", layout="wide")

try:
    # 3.1 Affichage du titre et du logo
    st.markdown("<h1 style='text-align: center;'>Application de Consultation de Planning</h1>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        st.logo(NOM_DU_LOGO, icon_image=NOM_DU_LOGO) 
    except AttributeError:
        if NOM_DU_LOGO and st.sidebar:
            st.sidebar.image(NOM_DU_LOGO, use_column_width=True)
    except Exception:
         st.sidebar.warning(f"Logo '{NOM_DU_LOGO}' non trouvé.")
    
    # 3.2 Chargement des données 
    df_initial = charger_donnees(NOM_DU_FICHIER)
    
    liste_employes = sorted(df_initial[COL_EMPLOYE].unique().tolist())
    
    if not liste_employes or (len(liste_employes) == 1 and str(liste_employes[0]).upper() in ['', 'NAN', 'NONE', 'N/A']):
        st.error(f"**ERREUR DE DONNÉES :** La colonne des employés (`'{COL_EMPLOYE}'`) est vide. Impossible de continuer.")
        st.stop()

    liste_semaines_brutes = sorted(df_initial[COL_SEMAINE].unique().tolist())
    liste_semaines_formatees = [get_dates_for_week(s) for s in liste_semaines_brutes]
    semaine_mapping = dict(zip(liste_semaines_formatees, liste_semaines_brutes))
    
    # 3.3 Création des menus déroulants (dans la sidebar)
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

    # 3.4 Affichage du planning
    if employe_selectionne and semaine_selectionnee_brute:
        
        df_employe = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()
        df_filtre = df_employe[df_employe[COL_SEMAINE] == semaine_selectionnee_brute].copy()
        
        # GESTION SPÉCIFIQUE (Noël)
        if semaine_selectionnee_brute == 'S52':
            df_filtre_avant = len(df_filtre)
            df_filtre = df_filtre[df_filtre[COL_JOUR] != 'JEUDI'].copy()
            
            if len(df_filtre) < df_filtre_avant:
                st.info(f"Note: Le **Jeudi** de la semaine S52 a été retiré (Jour de Noël).")

        # Trier par Jour logique
        df_filtre[COL_JOUR] = pd.Categorical(df_filtre[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
        df_filtre = df_filtre.sort_values(by=[COL_JOUR])
        
        # Calculer les heures et obtenir le tableau
        df_resultat, total_heures_format = calculer_heures_travaillees(df_filtre)
        
        # NOTE : La colonne 'Durée du service' est toujours dans df_resultat pour le calcul,
        # mais nous allons maintenant l'ignorer à l'affichage.
        
        st.subheader(f"Planning pour **{employe_selectionne}** - {semaine_selectionnee_formattee}")
        
        # Affichage du tableau de planning - ON NE GARDE QUE JOUR, DEBUT, ET FIN
        st.dataframe(
            df_resultat[[COL_JOUR, COL_DEBUT, COL_FIN]], 
            use_container_width=True,
            column_config={
                COL_JOUR: st.column_config.Column("Jour", width="large"),
                COL_DEBUT: st.column_config.Column("Début"),
                COL_FIN: st.column_config.Column("Fin"),
            },
            hide_index=True
        )
        
        # Affichage du total
        st.markdown(f"***")
        st.markdown(f"**TOTAL de la semaine pour {employe_selectionne} :** **{total_heures_format}**")
        
except Exception as e:
    st.error(f"Une erreur inattendue est survenue : {e}. Veuillez vérifier les logs de votre application pour plus de détails.")