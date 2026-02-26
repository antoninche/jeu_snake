# storage.py
# Highscore : compatible macOS + Windows (et Linux au passage).
# On stocke dans un dossier utilisateur (écrivable), pas dans le dossier du projet
# ni dans le bundle .app / Program Files.

import os
import sys


NOM_APP = "SnakeGoogle"
NOM_FICHIER_PAR_DEFAUT = "highscore.txt"


def dossier_donnees_utilisateur(nom_app=NOM_APP):
    """
    Renvoie un dossier écrivable pour stocker les données du jeu.
    - Windows : %APPDATA%/SnakeGoogle
    - macOS   : ~/Library/Application Support/SnakeGoogle
    - Linux   : ~/.local/share/SnakeGoogle
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, nom_app)

    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", nom_app)

    # Linux / autres
    return os.path.join(os.path.expanduser("~"), ".local", "share", nom_app)


def chemin_highscore(nom_fichier=NOM_FICHIER_PAR_DEFAUT, nom_app=NOM_APP):
    """
    Chemin complet du fichier de highscore.
    On ignore les chemins "bizarres" : on garde juste le nom de fichier,
    pour être sûr d'écrire au bon endroit.
    """
    if not nom_fichier:
        nom_fichier = NOM_FICHIER_PAR_DEFAUT

    # On garde uniquement le nom (évite d'écrire dans le dossier du projet)
    nom_fichier = os.path.basename(nom_fichier)

    dossier = dossier_donnees_utilisateur(nom_app)
    return os.path.join(dossier, nom_fichier)


def load_highscore(nom_fichier=NOM_FICHIER_PAR_DEFAUT, nom_app=NOM_APP):
    """
    Lit le highscore.
    - si le fichier n'existe pas -> 0
    - si invalide -> 0
    """
    chemin = chemin_highscore(nom_fichier, nom_app)

    if not os.path.exists(chemin):
        return 0

    try:
        with open(chemin, "r", encoding="utf-8") as f:
            texte = f.read().strip()

        if texte == "":
            return 0

        score = int(texte)
        if score < 0:
            return 0
        return score

    except Exception:
        return 0


def save_highscore(nom_fichier=NOM_FICHIER_PAR_DEFAUT, score=0, nom_app=NOM_APP):
    """
    Sauvegarde le highscore dans un dossier utilisateur.
    Écriture "safe" : on écrit d'abord un fichier temporaire puis on remplace.
    """
    try:
        score = int(score)
    except Exception:
        return

    if score < 0:
        score = 0

    dossier = dossier_donnees_utilisateur(nom_app)
    os.makedirs(dossier, exist_ok=True)

    chemin = chemin_highscore(nom_fichier, nom_app)
    chemin_tmp = chemin + ".tmp"

    with open(chemin_tmp, "w", encoding="utf-8") as f:
        f.write(str(score))

    # Remplace de façon atomique (évite fichier corrompu si crash)
    os.replace(chemin_tmp, chemin)
