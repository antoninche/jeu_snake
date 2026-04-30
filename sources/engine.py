# engine.py
import random
import math
 
class Etat:
    """États possibles du jeu."""
    MENU              = "menu"
    COMPTE_A_REBOURS  = "compte_a_rebours"
    JEU               = "jeu"
    PAUSE             = "pause"
    PERDU             = "perdu"

class TypeEvenement:
    """Types d'événements publiés par le moteur."""
    POMME_MANGEE     = "pomme_mangee"
    BONUS_MANGE      = "bonus_mange"
    BONUS_EXPIRE     = "bonus_expire"
    RECORD_BATTU     = "record_battu"
    PARTIE_TERMINEE  = "partie_terminee"
    NIVEAU_MONTE     = "niveau_monte"
    COMPTE_DEBUT     = "compte_debut"
    COMBO_ACTIF      = "combo_actif"

class BusEvenements:
    """Bus d'événements (Observer pattern) pour découpler le moteur de l'affichage."""
    def __init__(self):
        self._abonnes = {}

    def abonner(self, type_ev, action):
        if type_ev not in self._abonnes:
            self._abonnes[type_ev] = []
        self._abonnes[type_ev].append(action)

    def publier(self, type_ev, donnees=None):
        if donnees is None:
            donnees = {}
        for action in self._abonnes.get(type_ev, []):
            action(donnees)

class MoteurSnake:
    """Moteur de jeu gérant les règles, l'état, et les déplacements du Serpent."""

    def __init__(self, config, meilleur_score=0, graine=None):
        self.config = config
        self.aleatoire = random.Random(graine)
        self.bus = BusEvenements()
        self.etat = Etat.MENU

        # Options du menu
        self.sans_murs       = self.config.sans_murs_defaut
        self.portails_actifs = self.config.portails_defaut
        self.obstacles_actifs = self.config.obstacles_defaut
        self.vitesse         = "normal"

        self.score          = 0
        self.meilleur_score = meilleur_score

        # Timing
        self.accumulateur = 0.0
        self.duree_etape  = 0.1
        self._bonus_tps   = 0.0

        # Données de jeu
        self.serpent           = []
        self.serpent_precedent = []
        self.longueur_voulue   = 0
        self.direction         = (1, 0)
        self._file_directions  = []

        self.pomme       = None
        self.pomme_bonus = None
        self._timer_bonus = 0.0

        self.obstacles = set()
        self.portail_a = None
        self.portail_b = None

        # Niveaux
        self.niveau               = 1
        self._timer_message_lvl   = 0.0

        # Multiplicateur
        self._timer_depuis_pomme = 0.0
        self.combo_actif         = False

        # Compte à rebours
        self._timer_compte      = 0.0
        self.compte_affiche     = 0

        self.reinitialiser_partie()
        self.etat = Etat.MENU

    def basculer_sans_murs(self):
        if self.etat == Etat.MENU:
            self.sans_murs = not self.sans_murs

    def basculer_portails(self):
        if self.etat == Etat.MENU:
            self.portails_actifs = not self.portails_actifs

    def basculer_obstacles(self):
        if self.etat == Etat.MENU:
            self.obstacles_actifs = not self.obstacles_actifs

    def choisir_vitesse(self, vitesse):
        if self.etat == Etat.MENU and vitesse in ("lent", "normal", "rapide"):
            self.vitesse = vitesse

    def demarrer(self):
        if self.etat in (Etat.MENU, Etat.PERDU):
            self.reinitialiser_partie()
        self.etat           = Etat.COMPTE_A_REBOURS
        self._timer_compte  = self.config.duree_compte_a_rebours
        self.compte_affiche = 3
        self.bus.publier(TypeEvenement.COMPTE_DEBUT)

    def retour_menu(self):
        self.etat = Etat.MENU

    def basculer_pause(self):
        if self.etat == Etat.JEU:
            self.etat = Etat.PAUSE
        elif self.etat == Etat.PAUSE:
            self.etat = Etat.JEU

    def demander_direction(self, dx, dy):
        """Ajoute une direction à la file pour le prochain mouvement."""
        if self.etat not in (Etat.JEU, Etat.PAUSE):
            return

        if len(self._file_directions) > 0:
            dx_ref, dy_ref = self._file_directions[-1]
        else:
            dx_ref, dy_ref = self.direction

        if dx == -dx_ref and dy == -dy_ref:
            return

        if len(self._file_directions) < 2:
            self._file_directions.append((dx, dy))

    def tps_actuel(self):
        """Vitesse actuelle en Ticks Par Seconde."""
        if self.vitesse == "lent":
            base = self.config.tps_lent
        elif self.vitesse == "rapide":
            base = self.config.tps_rapide
        else:
            base = self.config.tps_normal

        tps = base + self._bonus_tps
        return min(tps, self.config.tps_max)

    def progression_etape(self):
        """Retourne l'avancée (0.0 à 1.0) entre deux mouvements pour le rendu fluide."""
        if self.duree_etape <= 0:
            return 0.0
        t = self.accumulateur / self.duree_etape
        return max(0.0, min(t, 1.0))

    def mettre_a_jour(self, delta_temps):
        """Appelé à chaque cycle pour avancer le jeu."""
        if self.etat == Etat.COMPTE_A_REBOURS:
            self._timer_compte -= delta_temps
            restant = max(0.0, self._timer_compte)
            self.compte_affiche = int(restant) + 1
            if self._timer_compte <= 0:
                self.etat           = Etat.JEU
                self.compte_affiche = 0
            return

        if self.etat != Etat.JEU:
            return

        # Cap anti-lag (évite les sursauts si un calcul est long)
        delta_temps = min(delta_temps, 0.25)

        if self.pomme_bonus is not None:
            self._timer_bonus -= delta_temps
            if self._timer_bonus <= 0:
                self.pomme_bonus  = None
                self._timer_bonus = 0.0
                self.bus.publier(TypeEvenement.BONUS_EXPIRE)

        if self._timer_depuis_pomme > 0:
            self._timer_depuis_pomme -= delta_temps
            if self._timer_depuis_pomme <= 0:
                self._timer_depuis_pomme = 0.0
                self.combo_actif         = False

        if self._timer_message_lvl > 0:
            self._timer_message_lvl -= delta_temps
            if self._timer_message_lvl < 0:
                self._timer_message_lvl = 0.0

        self.duree_etape = 1.0 / self.tps_actuel()
        self.accumulateur += delta_temps

        while self.accumulateur >= self.duree_etape and self.etat == Etat.JEU:
            self.accumulateur -= self.duree_etape
            self.avancer()

    def reinitialiser_partie(self):
        cx = self.config.largeur_grille // 2
        cy = self.config.hauteur_grille // 2
        self.serpent = [(cx - i, cy) for i in range(self.config.longueur_initiale)]
        self.serpent_precedent = list(self.serpent)

        self.longueur_voulue = self.config.longueur_initiale
        self.direction       = (1, 0)
        self._file_directions = []

        self.score            = 0
        self._bonus_tps       = 0.0
        self.accumulateur     = 0.0
        self.duree_etape      = 1.0 / self.tps_actuel()

        self.niveau               = 1
        self._timer_message_lvl   = 0.0

        self._timer_depuis_pomme = 0.0
        self.combo_actif         = False

        self.pomme_bonus  = None
        self._timer_bonus = 0.0

        self.obstacles = set()
        if self.obstacles_actifs:
            self.generer_obstacles(self.config.nombre_obstacles)

        self.portail_a = None
        self.portail_b = None
        if self.portails_actifs:
            self.generer_portails()

        self.pomme = self.choisir_case_libre()

    def avancer(self):
        """Logique de mouvement et collision lors d'un avancement du Serpent."""
        self.serpent_precedent = list(self.serpent)

        if len(self._file_directions) > 0:
            self.direction = self._file_directions.pop(0)

        tete_x, tete_y = self.serpent[0]
        dx, dy         = self.direction
        prochaine      = (tete_x + dx, tete_y + dy)

        prochaine = self.normaliser_case(prochaine)
        if prochaine is None:
            self._fin_partie()
            return

        prochaine = self.teleporter_si_portail(prochaine)

        if self.obstacles_actifs and prochaine in self.obstacles:
            self._fin_partie()
            return

        self.serpent.insert(0, prochaine)

        if prochaine == self.pomme:
            self._manger_pomme_normale()
        elif self.pomme_bonus is not None and prochaine == self.pomme_bonus:
            self._manger_pomme_bonus()
        else:
            while len(self.serpent) > self.longueur_voulue:
                self.serpent.pop()

        tete = self.serpent[0]
        corps = self.serpent[1:]
        if tete in corps:
            self._fin_partie()

    def _manger_pomme_normale(self):
        if self._timer_depuis_pomme > 0:
            points_gagnes    = self.config.score_multi
            self.combo_actif = True
            self.bus.publier(TypeEvenement.COMBO_ACTIF, {"score": self.score})
        else:
            points_gagnes    = 1
            self.combo_actif = False

        self.score           += points_gagnes
        self.longueur_voulue += self.config.croissance_par_pomme
        self._timer_depuis_pomme = self.config.delai_multi
        self._bonus_tps += self.config.tps_acceleration

        self._verifier_meilleur_score()
        self.bus.publier(TypeEvenement.POMME_MANGEE, {"score": self.score, "combo": self.combo_actif})
        self._verifier_niveau()

        self.pomme = self.choisir_case_libre()

        if self.pomme_bonus is None and self.config.duree_pomme_bonus > 0:
            if self.aleatoire.random() < self.config.proba_pomme_bonus:
                bonus = self.choisir_case_libre()
                if bonus != (0, 0):
                    self.pomme_bonus  = bonus
                    self._timer_bonus = self.config.duree_pomme_bonus

    def _manger_pomme_bonus(self):
        self.score           += self.config.score_pomme_bonus
        self.longueur_voulue += self.config.croissance_par_pomme
        self._bonus_tps      += self.config.tps_acceleration * 0.5
        self._timer_depuis_pomme = self.config.delai_multi

        self._verifier_meilleur_score()
        self.pomme_bonus  = None
        self._timer_bonus = 0.0
        self.bus.publier(TypeEvenement.BONUS_MANGE, {"score": self.score})

    def _verifier_meilleur_score(self):
        if self.score > self.meilleur_score:
            self.meilleur_score = self.score
            self.bus.publier(TypeEvenement.RECORD_BATTU, {"score": self.meilleur_score})

    def _verifier_niveau(self):
        nouveau_niveau = (self.score // self.config.pommes_par_niveau) + 1
        if nouveau_niveau > self.niveau:
            self.niveau             = nouveau_niveau
            self._timer_message_lvl = self.config.duree_message_lvl
            if self.obstacles_actifs:
                self.generer_obstacles(self.config.obstacles_par_lvl)
            self.bus.publier(TypeEvenement.NIVEAU_MONTE, {"niveau": self.niveau})

    def _fin_partie(self):
        self.etat = Etat.PERDU
        self.bus.publier(TypeEvenement.PARTIE_TERMINEE, {"score": self.score})

    def case_dans_grille(self, case):
        x, y = case
        return 0 <= x < self.config.largeur_grille and 0 <= y < self.config.hauteur_grille

    def normaliser_case(self, case):
        x, y = case
        if self.sans_murs:
            return x % self.config.largeur_grille, y % self.config.hauteur_grille
        if not self.case_dans_grille((x, y)):
            return None
        return (x, y)

    def case_est_libre(self, case):
        if case in self.serpent:
            return False
        if self.obstacles_actifs and case in self.obstacles:
            return False
        if self.portails_actifs and case in (self.portail_a, self.portail_b):
            return False
        return True

    def choisir_case_libre(self):
        cases_libres = [
            (x, y)
            for y in range(self.config.hauteur_grille)
            for x in range(self.config.largeur_grille)
            if self.case_est_libre((x, y))
        ]
        if not cases_libres:
            self._fin_partie()
            return (0, 0)
        return self.aleatoire.choice(cases_libres)

    def generer_obstacles(self, nombre):
        cx, cy = self.config.largeur_grille // 2, self.config.hauteur_grille // 2
        candidats = [
            (x, y) for y in range(self.config.hauteur_grille) for x in range(self.config.largeur_grille)
            if not (abs(x - cx) <= 4 and abs(y - cy) <= 4)
        ]
        self.aleatoire.shuffle(candidats)

        places = 0
        for c in candidats:
            if places >= nombre:
                break
            if self.case_est_libre(c):
                self.obstacles.add(c)
                places += 1

    def generer_portails(self):
        self.portail_a = self.choisir_case_libre()
        tentatives = 0
        b = self.choisir_case_libre()
        while b == self.portail_a and tentatives < 80:
            b = self.choisir_case_libre()
            tentatives += 1
        self.portail_b = b

    def teleporter_si_portail(self, case):
        if not self.portails_actifs or self.portail_a is None:
            return case
        if case == self.portail_a:
            return self.portail_b
        if case == self.portail_b:
            return self.portail_a
        return case
