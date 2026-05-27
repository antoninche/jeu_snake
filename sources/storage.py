# storage.py
import os
import sys
 
NOM_APP              = "SnakeGoogle"
NOM_FICHIER_PAR_DEF  = "meilleur_score.txt"
  
def dossier_donnees_utilisateur(nom_app=NOM_APP):
    """
    Renvoie le chemin du dossier où stocker les données du jeu.
    Le dossier est dans l'espace utilisateur (toujours accessible en écriture).
    """
    if sys.platform.startswith("win"):
        # Windows : %APPDATA%
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, nom_app)

    if sys.platform == "darwin":
        # macOS : ~/Library/Application Support/
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", nom_app)

    # Linux / autres
    return os.path.join(os.path.expanduser("~"), ".local", "share", nom_app)

def chemin_meilleur_score(nom_fichier=NOM_FICHIER_PAR_DEF, nom_app=NOM_APP):
    """Renvoie le chemin complet du fichier contenant le meilleur score."""
    if not nom_fichier:
        nom_fichier = NOM_FICHIER_PAR_DEF
    nom_fichier = os.path.basename(nom_fichier)
    dossier     = dossier_donnees_utilisateur(nom_app)
    return os.path.join(dossier, nom_fichier)

def charger_meilleur_score(nom_fichier=NOM_FICHIER_PAR_DEF, nom_app=NOM_APP):
    """Lit et renvoie le meilleur score depuis le fichier système."""
    chemin = chemin_meilleur_score(nom_fichier, nom_app)

    if not os.path.exists(chemin):
        return 0

    try:
        with open(chemin, "r", encoding="utf-8") as f:
            texte = f.read().strip()

        if texte == "":
            return 0

        score = int(texte)
        return score if score >= 0 else 0
    except Exception:
        return 0

def sauvegarder_meilleur_score(nom_fichier=NOM_FICHIER_PAR_DEF, score=0, nom_app=NOM_APP):
    """Sauvegarde le meilleur score de façon sécurisée (atomique)."""
    try:
        score = int(score)
    except Exception:
        return

    if score < 0:
        score = 0

    dossier = dossier_donnees_utilisateur(nom_app)
    os.makedirs(dossier, exist_ok=True)

    chemin     = chemin_meilleur_score(nom_fichier, nom_app)
    chemin_tmp = chemin + ".tmp"

    with open(chemin_tmp, "w", encoding="utf-8") as f:
        f.write(str(score))

    os.replace(chemin_tmp, chemin)
