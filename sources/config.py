# config.py

class Config:
    """Configuration centralisée du jeu Snake."""

    def __init__(self):
        # Paramètres de la fenêtre
        self.largeur_ecran = 800
        self.hauteur_ecran = 600

        # Taille de la grille
        self.taille_case = 40

        if self.largeur_ecran % self.taille_case != 0:
            raise ValueError("largeur_ecran doit être un multiple de taille_case.")
        if self.hauteur_ecran % self.taille_case != 0:
            raise ValueError("hauteur_ecran doit être un multiple de taille_case.")

        self.largeur_grille = self.largeur_ecran // self.taille_case
        self.hauteur_grille = self.hauteur_ecran // self.taille_case

        # Serpent
        self.longueur_initiale = 5
        self.croissance_par_pomme = 1

        # Options de départ configurables
        self.sans_murs_defaut = False
        self.portails_defaut  = False
        self.obstacles_defaut = False

        # Vitesses de jeu (ticks par seconde)
        self.tps_lent   = 8.0
        self.tps_normal = 10.0
        self.tps_rapide = 13.0

        # Vitesse progressive
        self.tps_acceleration = 0.15
        self.tps_max          = 25.0

        # Expérience de jeu (Niveaux / Obstacles)
        self.pommes_par_niveau  = 5
        self.obstacles_par_lvl  = 3
        self.duree_message_lvl  = 2.0

        # Multiplicateur de score (Combo x2)
        self.delai_multi  = 3.0
        self.score_multi  = 2

        # Décompte
        self.duree_compte_a_rebours = 3.0

        # Environnement initial
        self.nombre_obstacles = 18

        # Événements en jeu (Pomme bonus)
        self.duree_pomme_bonus  = 7.0
        self.score_pomme_bonus  = 3
        self.proba_pomme_bonus  = 0.25

        # Rendu technique
        self.fps_affichage = 60

        # Données utilisateur
        self.fichier_meilleur_score = "meilleur_score.txt"
