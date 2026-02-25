# config.py
# Réglages du jeu.
# Objectif : rendre le plateau, le texte et les éléments plus grands
# sans changer la taille de la fenêtre.

class Config:
    def __init__(self):
        # ===== Fenêtre (inchangée) =====
        self.largeur_ecran = 800
        self.hauteur_ecran = 600

        # ===== Grille =====
        # On agrandit la taille des cases => plateau visuellement plus grand (éléments plus gros)
        # 40 divise 800 et 600 (important !)
        self.taille_case = 40  # pixels par case

        if self.largeur_ecran % self.taille_case != 0 or self.hauteur_ecran % self.taille_case != 0:
            raise ValueError("largeur_ecran et hauteur_ecran doivent être multiples de taille_case.")

        self.largeur_grille = self.largeur_ecran // self.taille_case
        self.hauteur_grille = self.hauteur_ecran // self.taille_case

        # ===== Snake =====
        self.longueur_initiale = 5
        self.croissance_par_pomme = 1

        # ===== Options par défaut =====
        self.sans_murs_defaut = False
        self.portails_defaut = False
        self.obstacles_defaut = False

        # ===== Vitesses =====
        self.tps_lent = 8.0
        self.tps_normal = 10.0
        self.tps_rapide = 13.0

        # ===== Obstacles =====
        self.nombre_obstacles = 18

        # ===== UI =====
        self.fps_affichage = 60

        # ===== Stockage =====
        self.fichier_highscore = "highscore.txt"