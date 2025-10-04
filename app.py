import pandas as pd
import streamlit as st
import datetime
from datetime import date, timedelta

# --- CONFIGURATION DU FICHIER ---
# Nom exact du fichier. ATTENTION : Vous avez défini "planningss.xlsx".
NOM_DU_FICHIER = "planningss.xlsx"

# Noms des colonnes (headers) - DOIVENT CORRESPONDRE
COL_EMPLOYE = 'NOM VENDEUR'
COL_SEMAINE = 'SEMAINE'
COL_JOUR = 'JOUR'
COL_DEBUT = 'HEURE DEBUT'
COL_FIN = 'HEURE FIN'

# Ordre logique des jours
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

# --- CONVERSION DE SEMAINE EN DATES (Année 2025 de référence) ---

def get_dates_for_week(week_str, year=2025):
    """Convertit une chaîne de semaine (ex: 'S41') en dates de début et de fin (Lundi-Dimanche)."""
    
    # Mapping simple des mois pour éviter les problèmes de locale
    MONTHS = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
        7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    try:
        # Tente de convertir S41 en 41
        week_num = int(week_str.upper().replace('S', ''))
    except ValueError:
        return week_str

    try:
        # Calcul des dates à partir du numéro de semaine ISO
        d = date(year, 1, 4) 
        date_debut = d + timedelta(days=(week_num - d.isoweek()) * 7)
        date_fin = date_debut + timedelta(days=6)
        
        # Formatage de l'affichage (ex: 15 décembre)
        date_debut_str = f"{date_debut.day} {MONTHS[date_debut.month]}"
        date_fin_str = f"{date_fin.day} {MONTHS[date_fin.month]}"

        return f"{week_str} : du {date_debut_str} au {date_fin_str}"

    except Exception:
        return week_str


# --- FONCTION DE CALCUL ---
def calculer_heures_travaillees(df_planning):
    """Calcule le total des heures travaillées et la durée par service."""
    
    df_planning_calc = df_planning.copy()

    try:
        # 1. Préparation des colonnes pour le calcul
        def to_time_str_for_calc(val):
            if pd.isna(val) or val == "":
                return "00:00:00"
            if isinstance(val, (datetime.time, pd.Timestamp)):
                return str(val)
            elif isinstance(val, (int, float)) and 0 <= val <= 1: 
                # Conversion des heures Excel (format float)
                total_seconds = val * 86400 
                h = int(total_seconds // 3600)
                m = int((total_seconds % 3600) // 60)
                s = int(total_seconds % 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return str(val)

        df_planning_calc['Duree_Debut'] = pd.to_timedelta(df_planning_calc[COL_DEBUT].apply(to_time_str_for_calc).str.strip())
        df_planning_calc['Duree_Fin'] = pd.to_timedelta(df_planning_calc[COL_FIN].apply(to_time_str_for_calc).str.strip())
        
        # 2. Calcul de la durée du service
        def calculer_duree(row):
            duree = row['Duree_Fin'] - row['Duree_Debut']
            
            # Gère les horaires de nuit
            if duree < pd.Timedelta(0):
                duree += pd.Timedelta(days=1)
                
            # DÉDUCTION DE LA PAUSE DÉJEUNER (1 heure)
            # Soustrait 1 heure de pause si la durée est supérieure à 1 heure
            if duree > pd.Timedelta(hours=1):
                duree -= pd.Timedelta(hours=1)
                
            # Assurez-vous que la durée n'est jamais négative après la pause
            if duree < pd.Timedelta(0):
                return pd.Timedelta(0)
                
            return duree

        df_planning_calc['Durée du service'] = df_planning_calc.apply(calculer_duree, axis=1)
        
        df_planning['Durée du service'] = df_planning_calc['Durée du service'] 
        
        # 3. Calcul du total d'heures 
        durees_positives = df_planning_calc[df_planning_calc['Durée du service'] > pd.Timedelta(0)]['Durée du service']
        total_duree = durees_positives.sum()
        
        secondes_totales = total_duree.total_seconds()
        heures = int(secondes_totales // 3600)
        minutes = int((secondes_totales % 3600) // 60)
        
        return df_planning, f"{heures}h {minutes}min"
        
    except Exception as e:
        df_planning['Durée du service'] = pd.NaT
        return df_planning, f"Erreur de calcul: {e}"


# --- FONCTION DE CHARGEMENT DES DONNÉES (VERSION EXCEL + CSV ROBUSTE) ---

@st.cache_data
def charger_donnees(fichier):
    """Charge le fichier (Excel ou CSV) et nettoie les données."""
    try:
        # Tenter de lire en tant qu'Excel
        df = pd.read_excel(fichier)
    except Exception:
        try:
            # Si échec, tenter de lire en tant que CSV (avec point-virgule, commun en français)
            df = pd.read_csv(fichier, sep=';', encoding='latin1')
        except Exception as e:
            # Si échec, tenter de lire en tant que CSV standard (avec virgule)
            try:
                df = pd.read_csv(fichier, encoding='latin1') 
            except Exception as e_final:
                st.error(f"""
**ERREUR CRITIQUE : Impossible de lire le fichier de données.**
Vérifiez que le fichier `{fichier}` est dans le bon format (.xlsx ou .csv) et que son nom correspond exactement à la variable `NOM_DU_FICHIER` dans `app.py`.
Détails de l'erreur: {e_final}
""")
                st.stop()
    
    # --- NETTOYAGE DES DONNÉES (commun aux deux méthodes) ---
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


# --- INTERFACE STREAMLIT PRINCIPALE ---

st.set_page_config(page_title="Planning Employé", layout="wide")
st.title("🕒 Application de Consultation de Planning")
st.markdown("---")


try:
    # 1. Charger les données 
    df_initial = charger_donnees(NOM_DU_FICHIER)
    
    # 2. Préparer les listes de sélection
    liste_employes = sorted(df_initial[COL_EMPLOYE].unique().tolist())
    
    # DIAGNOSTIC CRITIQUE : Si la liste des employés est vide, afficher l'erreur.
    if not liste_employes or (len(liste_employes) == 1 and str(liste_employes[0]).upper() in ['', 'NAN', 'NONE', 'N/A']):
        st.error(f"""
**ERREUR DE DONNÉES : Impossible de trouver les employés.**
Le fichier `{NOM_DU_FICHIER}` a été chargé, mais la colonne des noms d'employés (`'{COL_EMPLOYE}'`) est vide ou n'a pas été trouvée correctement.
""")
        st.stop() # Arrête l'exécution pour afficher l'erreur

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
        
        # GESTION DE L'EXCEPTION NOËL (JEUDI S42)
        if semaine_selectionnee_brute == 'S42':
            # Sauvegarder la taille avant de filtrer
            df_filtre_avant = len(df_filtre)
            
            # Filtrer pour retirer le jeudi
            df_filtre = df_filtre[df_filtre[COL_JOUR] != 'JEUDI'].copy()
            
            if len(df_filtre) < df_filtre_avant:
                st.info(f"Note: Le **Jeudi** de la semaine S42 a été retiré du planning de **{employe_selectionne}** et du calcul des heures (Jour de Noël).")

        # Trier par Jour logique
        df_filtre[COL_JOUR] = pd.Categorical(df_filtre[COL_JOUR], categories=ORDRE_JOURS, ordered=True)
        df_filtre = df_filtre.sort_values(by=[COL_JOUR])
        
        # Calculer les heures
        df_resultat, total_heures_format = calculer_heures_travaillees(df_filtre)
        
        # Convertir la durée en chaîne formatée (HH:mm)
        def format_duration(x):
            if pd.isna(x) or x.total_seconds() <= 0:
                return ""
            h = int(x.total_seconds() // 3600)
            m = int((x.total_seconds() % 3600) // 60)
            return f"{h:02d}:{m:02d}"
            
        df_resultat['Durée du service (Affichage)'] = df_resultat['Durée du service'].apply(format_duration)
        
        # --- AFFICHAGE PRINCIPAL ---
        
        # Affiche le titre avec la semaine formatée (dates)
        st.subheader(f"Planning pour **{employe_selectionne}** - {semaine_selectionnee_formattee}")
        
        # Affichage du tableau de planning
        st.dataframe(
            df_resultat[[COL_JOUR, COL_DEBUT, COL_FIN, 'Durée du service (Affichage)']],
            use_container_width=True,
            column_config={
                COL_JOUR: st.column_config.Column("Jour", width="large"),
                COL_DEBUT: st.column_config.Column("Début"),
                COL_FIN: st.column_config.Column("Fin"),
                "Durée du service (Affichage)": "Durée du service (Pause déduite)" 
            },
            hide_index=True
        )
        
        # Ligne de TOTAL (Fonctionnalité demandée)
        st.markdown(f"***")
        st.markdown(f"**TOTAL de la semaine pour {employe_selectionne} :** **{total_heures_format}**")
        
except Exception as e:
    # Affiche les erreurs qui ne sont pas liées à l'indentation ou au chargement du fichier
    st.error(f"Une erreur inattendue est survenue au lancement : {e}")