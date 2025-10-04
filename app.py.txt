{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import pandas as pd\
import streamlit as st\
import datetime\
\
# --- CONFIGURATION DU FICHIER ---\
# Nom exact de votre fichier CSV\
NOM_DU_FICHIER = "planning.xlsx - De la S41 \'e0 la S52.csv"\
# Le s\'e9parateur est souvent la virgule (,) pour ce type de fichier\
SEPARATEUR_CSV = ',' \
\
# Noms des colonnes (headers) de votre fichier - DOIVENT CORRESPONDRE\
COL_EMPLOYE = 'NOM VENDEUR'\
COL_SEMAINE = 'SEMAINE'\
COL_JOUR = 'JOUR'\
COL_DEBUT = 'HEURE DEBUT'\
COL_FIN = 'HEURE FIN'\
\
# Ordre logique des jours\
ORDRE_JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']\
\
# --- FONCTION DE CALCUL ---\
def calculer_heures_travaillees(df_planning):\
    """Calcule le total des heures travaill\'e9es et la dur\'e9e par service."""\
    \
    # Remplacer les heures vides/manquantes par un temps nul (pour \'e9viter les erreurs de calcul)\
    df_planning = df_planning.fillna(\{COL_DEBUT: '00:00:00', COL_FIN: '00:00:00'\})\
\
    try:\
        # Convertir les colonnes d'heures en objets TimeDelta (dur\'e9e)\
        df_planning['Duree_Debut'] = pd.to_timedelta(df_planning[COL_DEBUT].astype(str).str.strip())\
        df_planning['Duree_Fin'] = pd.to_timedelta(df_planning[COL_FIN].astype(str).str.strip())\
        \
        # Calculer la dur\'e9e du service\
        def calculer_duree(row):\
            duree = row['Duree_Fin'] - row['Duree_Debut']\
            \
            # G\'e9rer les services qui passent minuit (la dur\'e9e est n\'e9gative et doit \'eatre augment\'e9e de 24h)\
            if duree < pd.Timedelta(0):\
                duree += pd.Timedelta(days=1)\
                \
            return duree\
\
        df_planning['Dur\'e9e du service'] = df_planning.apply(calculer_duree, axis=1)\
        \
        # Calculer le total g\'e9n\'e9ral (en ignorant les services de 0h)\
        total_duree = df_planning[df_planning['Dur\'e9e du service'] > pd.Timedelta(0)]['Dur\'e9e du service'].sum()\
        \
        # Formater le r\'e9sultat en heures et minutes (HHh MMmin)\
        secondes_totales = total_duree.total_seconds()\
        heures = int(secondes_totales // 3600)\
        minutes = int((secondes_totales % 3600) // 60)\
        \
        return df_planning, f"\{heures\}h \{minutes\}min"\
        \
    except Exception as e:\
        # En cas d'erreur de formatage (si les heures ne sont pas HH:MM:SS)\
        return df_planning, "Erreur de calcul"\
\
\
# --- INTERFACE STREAMLIT PRINCIPALE ---\
\
st.set_page_config(page_title="Planning Employ\'e9", layout="wide")\
st.title("\uc0\u55357 \u56658  Application de Consultation de Planning")\
st.markdown("---")\
\
\
@st.cache_data\
def charger_donnees(fichier, separateur):\
    """Charge le fichier CSV une seule fois et nettoie les donn\'e9es."""\
    try:\
        df = pd.read_csv(fichier, sep=separateur, skipinitialspace=True)\
        \
        # Nettoyage des noms de colonnes et des donn\'e9es (gestion des espaces)\
        df.columns = df.columns.str.strip()\
        for col in df.columns:\
            if df[col].dtype == 'object':\
                df[col] = df[col].astype(str).str.strip()\
                \
        # Supprimer les lignes qui n'ont aucune donn\'e9e\
        df = df.dropna(how='all')\
                \
        # Cr\'e9er une colonne pour l'affichage : "S41 - LUNDI"\
        df['SEMAINE ET JOUR'] = df[COL_SEMAINE] + ' - ' + df[COL_JOUR]\
        \
        return df\
    except Exception as e:\
        st.error(f"Impossible de charger le fichier CSV. V\'e9rifiez le nom du fichier et le s\'e9parateur. D\'e9tails: \{e\}")\
        st.stop()\
        \
try:\
    # 1. Charger les donn\'e9es (Point de d\'e9part)\
    df_initial = charger_donnees(NOM_DU_FICHIER, SEPARATEUR_CSV)\
    \
    # 2. Pr\'e9parer la liste des employ\'e9s uniques\
    liste_employes = sorted(df_initial[COL_EMPLOYE].unique().tolist())\
    \
    # 3. Cr\'e9er le menu d\'e9roulant sur le c\'f4t\'e9 (Sidebar)\
    st.sidebar.header("S\'e9lectionnez votre profil")\
    employe_selectionne = st.sidebar.selectbox(\
        'Qui \'eates-vous ?',\
        liste_employes\
    )\
\
    # 4. Afficher les r\'e9sultats pour l'employ\'e9 s\'e9lectionn\'e9\
    if employe_selectionne:\
        \
        df_employe = df_initial[df_initial[COL_EMPLOYE] == employe_selectionne].copy()\
        \
        # Trier par Semaine, puis par ordre logique des Jours\
        df_employe[COL_JOUR] = pd.Categorical(df_employe[COL_JOUR], categories=ORDRE_JOURS, ordered=True)\
        df_employe = df_employe.sort_values(by=[COL_SEMAINE, COL_JOUR])\
        \
        # Calculer les heures\
        df_resultat, total_heures_format = calculer_heures_travaillees(df_employe)\
        \
        # --- AFFICHAGE PRINCIPAL ---\
        \
        st.metric(\
            label="Total des heures cumul\'e9es", \
            value=total_heures_format,\
            delta=f"sur \{len(df_resultat[df_resultat['Dur\'e9e du service'] > pd.Timedelta(0)])\} services trouv\'e9s",\
            delta_color="off"\
        )\
        \
        st.subheader(f"D\'e9tail des services pour \{employe_selectionne\}")\
        \
        # Affichage du tableau de planning\
        st.dataframe(\
            df_resultat[['SEMAINE ET JOUR', COL_DEBUT, COL_FIN, 'Dur\'e9e du service']],\
            use_container_width=True,\
            column_config=\{\
                "SEMAINE ET JOUR": st.column_config.Column("Semaine et Jour", width="large"),\
                COL_DEBUT: st.column_config.Column("D\'e9but"),\
                COL_FIN: st.column_config.Column("Fin"),\
                "Dur\'e9e du service": st.column_config.DurationColumn("Dur\'e9e", format="HH:mm")\
            \},\
            hide_index=True\
        )\
    \
except Exception as e:\
    st.error(f"Le lancement a \'e9chou\'e9. Assurez-vous que Conda est activ\'e9 et que les fichiers sont au bon endroit. Erreur g\'e9n\'e9rale: \{e\}")\
\
# --- FIN DU CODE ---}
