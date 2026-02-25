# engine.py
# Moteur de jeu (logique) SANS pygame.
# Objectif : code clair, testable, et facile à complexifier.

import random


class MoteurSnake:
    def __init__(self, config, highscore=0, graine=None):
        self.cfg = config
        self.rng = random.Random(graine)

        # Etats possibles : "menu", "jeu", "pause", "perdu"
        self.etat = "menu"

        # Options (réglables dans le menu)
        self.sans_murs = self.cfg.sans_murs_defaut
        self.portails_actifs = self.cfg.portails_defaut
        self.obstacles_actifs = self.cfg.obstacles_defaut
        self.vitesse = "normal"  # "lent" / "normal" / "rapide"

        # Score = nombre de pommes mangées (comme Google Snake)
        self.score = 0
        self.highscore = highscore
        self.highscore_a_sauver = False  # True quand on dépasse le highscore

        # Timing : accumulateur pour faire des ticks réguliers
        self.accumulateur = 0.0

        # Données de jeu (seront initialisées dans reset_partie)
        self.serpent = []
        self.longueur_voulue = 0
        self.direction = (1, 0)         # (dx, dy) : commence vers la droite
        self.direction_voulue = None    # direction demandée au clavier, appliquée au tick suivant

        self.pomme = None               # (x, y)
        self.obstacles = set()          # ensemble de cases
        self.portail_a = None           # (x, y) ou None
        self.portail_b = None           # (x, y) ou None

        # Prépare une partie "prête" (mais on reste au menu)
        self.reset_partie()
        self.etat = "menu"

    # =============================
    # Fonctions "menu" (options)
    # =============================

    def basculer_sans_murs(self):
        if self.etat == "menu":
            self.sans_murs = not self.sans_murs

    def basculer_portails(self):
        if self.etat == "menu":
            self.portails_actifs = not self.portails_actifs

    def basculer_obstacles(self):
        if self.etat == "menu":
            self.obstacles_actifs = not self.obstacles_actifs

    def choisir_vitesse(self, vitesse):
        # vitesse: "lent" / "normal" / "rapide"
        if self.etat == "menu":
            if vitesse in ("lent", "normal", "rapide"):
                self.vitesse = vitesse

    # =============================
    # Cycle de vie (start/pause)
    # =============================

    def demarrer(self):
        # Démarre une partie depuis menu ou après un game over
        if self.etat in ("menu", "perdu"):
            self.reset_partie()
        self.etat = "jeu"

    def retour_menu(self):
        self.etat = "menu"

    def basculer_pause(self):
        if self.etat == "jeu":
            self.etat = "pause"
        elif self.etat == "pause":
            self.etat = "jeu"

    # =============================
    # Entrées (direction)
    # =============================

    def demander_direction(self, dx, dy):
        # On empêche le demi-tour direct (classique Snake)
        if self.etat not in ("jeu", "pause"):
            return

        dx_actuel, dy_actuel = self.direction
        if dx == -dx_actuel and dy == -dy_actuel:
            return

        self.direction_voulue = (dx, dy)

    # =============================
    # Timing / update
    # =============================

    def tps_actuel(self):
        # ticks par seconde selon la vitesse choisie
        if self.vitesse == "lent":
            return self.cfg.tps_lent
        if self.vitesse == "rapide":
            return self.cfg.tps_rapide
        return self.cfg.tps_normal

    def update(self, dt):
        # dt en secondes
        if self.etat != "jeu":
            return

        # si dt est énorme (lag), on limite pour éviter les sauts
        if dt > 0.25:
            dt = 0.25

        self.accumulateur += dt

        dt_tick = 1.0 / float(self.tps_actuel())
        while self.accumulateur >= dt_tick and self.etat == "jeu":
            self.accumulateur -= dt_tick
            self.tick()

    # =============================
    # Partie (reset / tick)
    # =============================

    def reset_partie(self):
        # Snake au centre, horizontal, vers la droite
        cx = self.cfg.largeur_grille // 2
        cy = self.cfg.hauteur_grille // 2

        self.serpent = []
        for i in range(self.cfg.longueur_initiale):
            self.serpent.append((cx - i, cy))

        self.longueur_voulue = self.cfg.longueur_initiale
        self.direction = (1, 0)
        self.direction_voulue = None

        self.score = 0
        self.highscore_a_sauver = False
        self.accumulateur = 0.0

        # Obstacles
        self.obstacles = set()
        if self.obstacles_actifs:
            self.generer_obstacles(self.cfg.nombre_obstacles)

        # Portails
        self.portail_a = None
        self.portail_b = None
        if self.portails_actifs:
            self.generer_portails()

        # Pomme
        self.pomme = self.choisir_case_libre()

    def tick(self):
        # 1) Appliquer direction demandée (si existante)
        if self.direction_voulue is not None:
            self.direction = self.direction_voulue
            self.direction_voulue = None

        # 2) Calculer prochaine case
        tete_x, tete_y = self.serpent[0]
        dx, dy = self.direction
        prochaine = (tete_x + dx, tete_y + dy)

        # 3) Gestion des murs / wrap
        prochaine = self.normaliser_case(prochaine)
        if prochaine is None:
            self.etat = "perdu"
            return

        # 4) Portails (si activés)
        prochaine = self.teleporter_si_portail(prochaine)

        # 5) Collision obstacles
        if self.obstacles_actifs and prochaine in self.obstacles:
            self.etat = "perdu"
            return

        # 6) Déplacement : on ajoute la tête
        self.serpent.insert(0, prochaine)

        # 7) Manger la pomme ?
        mange = (prochaine == self.pomme)
        if mange:
            self.score += 1
            self.longueur_voulue += self.cfg.croissance_par_pomme

            if self.score > self.highscore:
                self.highscore = self.score
                self.highscore_a_sauver = True

            # Nouvelle pomme
            self.pomme = self.choisir_case_libre()
        else:
            # On enlève la queue pour garder la même longueur
            while len(self.serpent) > self.longueur_voulue:
                self.serpent.pop()

        # 8) Collision avec soi-même
        # Important : on vérifie après avoir éventuellement retiré la queue.
        tete = self.serpent[0]
        corps = self.serpent[1:]
        if tete in corps:
            self.etat = "perdu"
            return

    # =============================
    # Outils grille
    # =============================

    def case_dans_grille(self, case):
        x, y = case
        if x < 0 or x >= self.cfg.largeur_grille:
            return False
        if y < 0 or y >= self.cfg.hauteur_grille:
            return False
        return True

    def normaliser_case(self, case):
        # Retourne une case valide, ou None si on sort (si sans_murs=False)
        x, y = case

        if self.sans_murs:
            # wrap : on réapparaît de l'autre côté
            x = x % self.cfg.largeur_grille
            y = y % self.cfg.hauteur_grille
            return (x, y)

        # murs solides
        if not self.case_dans_grille((x, y)):
            return None
        return (x, y)

    def case_est_libre(self, case):
        # Une case est libre si elle n'est ni sur le snake, ni sur un obstacle, ni sur un portail
        if case in self.serpent:
            return False
        if self.obstacles_actifs and case in self.obstacles:
            return False
        if self.portails_actifs:
            if self.portail_a is not None and case == self.portail_a:
                return False
            if self.portail_b is not None and case == self.portail_b:
                return False
        return True

    def choisir_case_libre(self):
        # Méthode simple : on liste les cases libres puis on en choisit une au hasard.
        cases_libres = []
        for y in range(self.cfg.hauteur_grille):
            for x in range(self.cfg.largeur_grille):
                c = (x, y)
                if self.case_est_libre(c):
                    cases_libres.append(c)

        if len(cases_libres) == 0:
            # plus de place => fin de partie
            self.etat = "perdu"
            return (0, 0)

        return self.rng.choice(cases_libres)

    # =============================
    # Obstacles / Portails
    # =============================

    def generer_obstacles(self, nombre):
        # On place des obstacles loin du centre pour éviter de bloquer le départ.
        cx = self.cfg.largeur_grille // 2
        cy = self.cfg.hauteur_grille // 2

        candidats = []
        for y in range(self.cfg.hauteur_grille):
            for x in range(self.cfg.largeur_grille):
                # zone "safe" autour du spawn
                if abs(x - cx) <= 4 and abs(y - cy) <= 4:
                    continue
                candidats.append((x, y))

        self.rng.shuffle(candidats)

        places = 0
        i = 0
        while places < nombre and i < len(candidats):
            c = candidats[i]
            i += 1
            if self.case_est_libre(c):
                self.obstacles.add(c)
                places += 1

    def generer_portails(self):
        # Deux cases libres distinctes
        a = self.choisir_case_libre()
        # Pour la seconde, on "réserve" a temporairement en la considérant occupée
        # (le plus simple : boucle jusqu'à trouver différent)
        b = self.choisir_case_libre()
        tentatives = 0
        while b == a and tentatives < 50:
            b = self.choisir_case_libre()
            tentatives += 1

        self.portail_a = a
        self.portail_b = b

    def teleporter_si_portail(self, case):
        if not self.portails_actifs:
            return case
        if self.portail_a is None or self.portail_b is None:
            return case

        if case == self.portail_a:
            return self.portail_b
        if case == self.portail_b:
            return self.portail_a
        return case