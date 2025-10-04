import streamlit as st
import pandas as pd

# 🔑 NOTE TRES IMPORTANTE: Le nom du fichier est exact et sensible à la casse
FILE_NAME = 'planning.xlsx - De la S41 à la S52.csv'

st.set_page_config(layout="wide", page_title="Planification Vendeurs")
st.title("Tableau de bord de Planification")

try:
    # Lecture du fichier comme CSV (le format qu'il est réellement)
    df = pd.read_csv(FILE_NAME)
    
    # Nettoyage des noms de colonnes (supprime les espaces avant/après)
    df.columns = df.columns.str.strip()
    
    st.success(f"Fichier '{FILE_NAME}' chargé et lu comme CSV avec succès !")
    
    # Affichage des premières lignes pour confirmation
    st.dataframe(df.head())
    
    # Ajoutez ici le reste de votre logique d'application (filtrage, calculs...)
    
except FileNotFoundError:
    st.error(f"""
    **ERREUR : Fichier non trouvé.**
    Le fichier nommé `{FILE_NAME}` est introuvable sur le serveur.
    
    **C'est le problème principal :** Veuillez confirmer que ce fichier est bien présent **dans le même dossier que `app.py`** dans votre dépôt Git (GitHub), et que vous avez bien poussé (push) cette version.
    """)
except Exception as e:
    st.error(f"Une erreur est survenue lors du traitement du fichier : {e}")
