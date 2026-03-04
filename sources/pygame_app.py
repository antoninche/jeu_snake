# pygame_app.py
# Interface Pygame : affichage, clavier, sons et particules.
#

import time    # pour mesurer le temps réel (horloges, animations)
import math    # pour les fonctions sin(), cos(), etc.
import random  # pour la dispersion des particules

import pygame  # bibliothèque graphique

# Import des éléments du moteur
from config import Config
from engine import Etat, TypeEvenement, MoteurSnake
from storage import charger_meilleur_score, sauvegarder_meilleur_score


# ==============================================================
# GÉNÉRATION DE SONS SYNTHÉTIQUES
# [NSI] On génère les sons en créant des tableaux d'octets (bytearray).
# Un son numérique = une série de nombres représentant l'amplitude sonore.
# On utilise une onde sinusoïdale (sin) pour produire un son pur.
# ==============================================================

TAUX_ECHANTILLONNAGE = 44100   # 44 100 échantillons par seconde (qualité CD)


def _generer_segment(frequence, duree, volume):
    """
    Génère un segment sonore (série d'octets) pour une fréquence donnée.

    frequence : en Hertz (ex: 440 Hz = La)
    duree     : en secondes
    volume    : de 0.0 à 1.0

    [NSI] Un son 16-bits = chaque échantillon est un entier entre -32768 et 32767.
    On encode chaque entier sur 2 octets en little-endian (octet de poids faible en premier).
    """
    n_echantillons = int(TAUX_ECHANTILLONNAGE * duree)
    donnees        = bytearray(n_echantillons * 2)   # 2 octets par échantillon (16 bits)

    for i in range(n_echantillons):
        t = i / TAUX_ECHANTILLONNAGE   # temps en secondes

        # Onde sinusoïdale : amplitude entre -1 et 1
        amplitude = math.sin(2 * math.pi * frequence * t)

        # Fade-out sur les 30 derniers % pour éviter le "clic" de fin
        ratio_fade = i / n_echantillons
        if ratio_fade > 0.7:
            amplitude *= 1.0 - (ratio_fade - 0.7) / 0.3

        # Conversion en entier 16 bits signé
        val = int(amplitude * 32767 * volume)
        # Clamp entre -32768 et 32767
        if val > 32767:
            val = 32767
        elif val < -32768:
            val = -32768

        # Encodage little-endian : octet bas d'abord, puis octet haut
        # val & 0xFF garde les 8 bits de poids faible
        # (val >> 8) & 0xFF garde les 8 bits de poids fort
        donnees[i * 2]     = val & 0xFF
        donnees[i * 2 + 1] = (val >> 8) & 0xFF

    return donnees


def _generer_son_compose(segments, volume=0.28):
    """
    Crée un son pygame.mixer.Sound à partir de plusieurs segments.
    segments : liste de tuples (frequence, duree)

    Chaque segment est une note jouée à la suite de la précédente.
    """
    donnees_totales = bytearray()
    for frequence, duree in segments:
        donnees_totales += _generer_segment(frequence, duree, volume)

    return pygame.mixer.Sound(buffer=donnees_totales)


def creer_sons():
    """
    Crée et renvoie un dictionnaire de sons synthétiques.
    Aucun fichier audio externe nécessaire.
    Si pygame.mixer n'est pas disponible, renvoie un dictionnaire vide.
    """
    sons = {}
    try:
        # Son "manger" : accord ascendant (Do-Mi-Sol)
        sons["manger"] = _generer_son_compose([
            (523.25, 0.06),   # Do5
            (659.25, 0.06),   # Mi5
            (783.99, 0.10),   # Sol5
        ])

        # Son "pomme bonus" : accord aigu brillant
        sons["bonus"] = _generer_son_compose([
            (880.0,  0.05),
            (1046.5, 0.05),
            (1318.5, 0.12),
        ], volume=0.30)

        # Son "nouveau meilleur_score" : fanfare courte
        sons["meilleur_score"] = _generer_son_compose([
            (523.25, 0.07),
            (659.25, 0.07),
            (783.99, 0.07),
            (1046.5, 0.18),
        ])

        # Son "game over" : descente sombre
        sons["perdu"] = _generer_son_compose([
            (311.13, 0.12),   # Eb4
            (261.63, 0.12),   # Do4
            (207.65, 0.20),   # Ab3
        ])

        # Son "compte à rebours" : bip court
        sons["bip"] = _generer_son_compose([
            (800.0, 0.08),
        ], volume=0.20)

        # Son "GO !" : bip aigu plus long
        sons["go"] = _generer_son_compose([
            (1000.0, 0.04),
            (1200.0, 0.12),
        ], volume=0.25)

        # Son "niveau" : deux notes montantes
        sons["niveau"] = _generer_son_compose([
            (659.25, 0.08),
            (880.0,  0.14),
        ], volume=0.25)

    except Exception:
        # Si une erreur se produit (ex: pas de carte son), on ignore les sons
        return {}

    return sons


# ==============================================================
# PARTICULES

class Particule:
    """
    Représente une petite particule animée.

    Attributs :
        x, y     : position en pixels (flottants pour la précision)
        vx, vy   : vitesse en pixels/seconde
        rayon    : taille du cercle en pixels
        couleur  : tuple (R, G, B)
        duree    : durée de vie totale en secondes
        age      : âge courant en secondes
    """

    def __init__(self, x, y, vx, vy, rayon, couleur, duree):
        self.x       = x
        self.y       = y
        self.vx      = vx      # vitesse horizontale
        self.vy      = vy      # vitesse verticale
        self.rayon   = rayon
        self.couleur = couleur
        self.duree   = duree
        self.age     = 0.0

    def est_vivante(self):
        """Renvoie True si la particule n'a pas encore atteint sa durée de vie."""
        return self.age < self.duree

    def ratio_mort(self):
        """
        Renvoie un flottant entre 0 et 1 (0 = neuf, 1 = mort).
        Utilisé pour calculer la transparence (fade-out).
        """
        r = self.age / self.duree
        if r < 0.0:
            return 0.0
        if r > 1.0:
            return 1.0
        return r

    def mettre_a_jour(self, delta_temps):
        """
        Avance la particule de delta_temps secondes.
        Applique la vitesse et une légère gravité.
        """
        self.age += delta_temps
        self.x   += self.vx * delta_temps
        self.y   += self.vy * delta_temps
        # Gravité : accélère vers le bas (en pixels/s²)
        self.vy  += 180 * delta_temps


def creer_explosion(cx, cy, couleur, nombre=14):
    """
    Crée une liste de particules partant toutes de (cx, cy).
    cx, cy   : centre de l'explosion en pixels
    couleur  : couleur de base (R, G, B)
    nombre   : nombre de particules
    """
    rc, gc, bc = couleur
    particules = []
    for _ in range(nombre):
        angle   = random.uniform(0, 2 * math.pi)
        vitesse = random.uniform(60, 200)
        vx = math.cos(angle) * vitesse
        vy = math.sin(angle) * vitesse - random.uniform(30, 80)
        r  = random.randint(3, 7)
        d  = random.uniform(0.4, 0.8)
        # Variation de couleur pour un effet naturel
        cr = max(0, min(255, rc + random.randint(-30, 30)))
        cg = max(0, min(255, gc + random.randint(-30, 30)))
        cb = max(0, min(255, bc + random.randint(-30, 30)))
        particules.append(Particule(cx, cy, vx, vy, r, (cr, cg, cb), d))
    return particules


# ==============================================================
# APPLICATION PYGAME PRINCIPALE
# ==============================================================

class ApplicationPygame:
    """
    Classe principale : gère la fenêtre, les events, l'affichage et les sons.
    C'est le "chef d'orchestre" côté interface.
    """

    def __init__(self, config):
        self.config = config

        # Initialisation de pygame (obligatoire avant tout)
        pygame.init()
        # Initialisation du mixeur audio (fréquence, profondeur, mono, tampon)
        pygame.mixer.init(frequency=TAUX_ECHANTILLONNAGE, size=-16, channels=1, buffer=512)

        # Création de la fenêtre
        self.ecran = pygame.display.set_mode((config.largeur_ecran, config.hauteur_ecran))
        pygame.display.set_caption("Snake (style Google)")

        # Horloge pour contrôler les FPS
        self.horloge = pygame.time.Clock()

        # --- Polices de caractères ---
        # On utilise Arial en gras (police système standard, plus propre que la police par défaut de pygame)
        self.police        = pygame.font.SysFont("arial", 34, bold=True)
        self.police_petite = pygame.font.SysFont("arial", 22, bold=True)
        self.police_grande = pygame.font.SysFont("arial", 72, bold=True)
        self.police_xg     = pygame.font.SysFont("arial", 110, bold=True)

        # Chargement du meilleur_score depuis le fichier
        meilleur_score = charger_meilleur_score(config.fichier_meilleur_score)

        # Création du moteur de jeu
        self.moteur = MoteurSnake(config, meilleur_score=meilleur_score, graine=int(time.time()))

        # Génération des sons (peut échouer sans carte son)
        self.sons = creer_sons()
        self._son_meilleur_score_joue = False  # pour ne jouer la fanfare qu'une fois par partie

        # === OPTIONS D'ACCESSIBILITÉ ===
        self.son_coupe   = False   # True = sons coupés (touche M)
        
        # Liste des particules actives
        self.particules = []

        # Variables pour les overlays temporaires
        self._dernier_compte = -1   # pour détecter le changement de chiffre

        # Abonnement aux événements du moteur (Observer pattern)
        # Chaque ligne dit : "quand tel événement se produit, appelle cette méthode"
        self.moteur.bus.abonner(TypeEvenement.POMME_MANGEE,    self._sur_pomme_mangee)
        self.moteur.bus.abonner(TypeEvenement.BONUS_MANGE,     self._sur_bonus_mange)
        self.moteur.bus.abonner(TypeEvenement.RECORD_BATTU, self._sur_meilleur_score_battu)
        self.moteur.bus.abonner(TypeEvenement.PARTIE_TERMINEE, self._sur_partie_terminee)
        self.moteur.bus.abonner(TypeEvenement.NIVEAU_MONTE,    self._sur_niveau_monte)

        # === PALETTE DE COULEURS ===
        # [NSI] Les couleurs sont des tuples (R, G, B) avec des valeurs de 0 à 255.
        self.coul_fond_a          = (170, 215, 81)    # cases vertes claires
        self.coul_fond_b          = (162, 209, 73)    # cases vertes foncées
        self.coul_ui_bord         = (40, 45, 55)      # bord des panneaux UI
        self.coul_serpent         = (65, 110, 240)    # bleu serpent
        self.coul_serpent_contour = (40, 75, 190)     # contour serpent
        self.coul_obstacle        = (70, 70, 80)      # gris obstacles
        self.coul_pomme           = (230, 60, 60)     # rouge pomme
        self.coul_pomme_reflet    = (255, 160, 160)   # reflet pomme
        self.coul_feuille         = (70, 180, 90)     # vert feuille
        self.coul_pomme_bonus     = (255, 185, 30)    # or pomme bonus
        self.coul_pomme_br        = (255, 230, 160)   # reflet bonus
        self.coul_portail_a       = (120, 80, 220)    # violet portail A
        self.coul_portail_b       = (70, 220, 180)    # cyan portail B
        self.coul_texte           = (245, 245, 245)   # blanc texte
        self.coul_texte_faible    = (190, 195, 205)   # gris texte secondaire
        self.coul_on              = (80, 200, 120)    # vert "ON"
        self.coul_off             = (220, 90, 90)     # rouge "OFF"
        self.coul_combo           = (255, 200, 0)     # or combo ×2

        # Temps depuis le lancement (pour les animations basées sur le temps)
        self.temps_debut = time.perf_counter()

    # ==============================================================
    # CALLBACKS ÉVÉNEMENTS (abonnés au bus du moteur)
    # ==============================================================

    def _sur_pomme_mangee(self, donnees):
        """Appelé automatiquement quand une pomme normale est mangée."""
        self._jouer_son("manger")
        # Crée des particules à la position de la tête du serpent
        if len(self.moteur.serpent) > 0:
            x, y   = self.moteur.serpent[0]
            t      = self.config.taille_case
            cx, cy = x * t + t // 2, y * t + t // 2
            self.particules += creer_explosion(cx, cy, self.coul_pomme)

    def _sur_bonus_mange(self, donnees):
        """Appelé automatiquement quand la pomme bonus est mangée."""
        self._jouer_son("bonus")
        if len(self.moteur.serpent) > 0:
            x, y   = self.moteur.serpent[0]
            t      = self.config.taille_case
            cx, cy = x * t + t // 2, y * t + t // 2
            self.particules += creer_explosion(cx, cy, self.coul_pomme_bonus, nombre=20)

    def _sur_meilleur_score_battu(self, donnees):
        """Appelé quand un nouveau record est atteint."""
        if not self._son_meilleur_score_joue:
            self._jouer_son("meilleur_score")
            self._son_meilleur_score_joue = True
        # Sauvegarde immédiate dans le fichier
        sauvegarder_meilleur_score(self.config.fichier_meilleur_score, donnees.get("score", 0))

    def _sur_partie_terminee(self, donnees):
        """Appelé au game over."""
        self._jouer_son("perdu")
        self._son_meilleur_score_joue = False

    def _sur_niveau_monte(self, donnees):
        """Appelé quand le joueur passe un niveau."""
        self._jouer_son("niveau")

    def _jouer_son(self, nom):
        """Joue un son par son nom. Si les sons sont coupés (mute), ne fait rien."""
        if self.son_coupe:
            return   # mute actif : on ne joue aucun son
        son = self.sons.get(nom)
        if son is not None:
            try:
                son.play()
            except Exception:
                pass  # on ignore si la carte son n'est pas disponible

    

    # ==============================================================
    # BOUCLE PRINCIPALE
        # La boucle tourne ~60 fois par seconde (selon fps_affichage).
    # Chaque itération : lire les events → mettre à jour → afficher.
    # ==============================================================

    def lancer(self):
        """Boucle de jeu principale. Tourne jusqu'à ce que le joueur quitte."""
        dernier_temps = time.perf_counter()
        continuer     = True

        while continuer:
            # Calcul du delta-time (delta_temps) : temps écoulé depuis la dernière frame
            maintenant    = time.perf_counter()
            delta_temps            = maintenant - dernier_temps
            dernier_temps = maintenant

            # 1) Lecture des événements pygame (clavier, fermeture de fenêtre)
            for evenement in pygame.event.get():
                if evenement.type == pygame.QUIT:
                    continuer = False
                elif evenement.type == pygame.KEYDOWN:
                    continuer = self.gerer_touche(evenement.key)

            # 2) Mise à jour du moteur de jeu
            self.moteur.mettre_a_jour(delta_temps)

            # Gestion du compte à rebours : son à chaque changement de chiffre
            if self.moteur.etat == Etat.COMPTE_A_REBOURS:
                chiffre = self.moteur.compte_affiche
                if chiffre != self._dernier_compte:
                    self._dernier_compte = chiffre
                    if chiffre == 0:
                        self._jouer_son("go")
                    else:
                        self._jouer_son("bip")

            # 3) Mise à jour des particules : on enlève celles mortes
            particules_vivantes = []
            for p in self.particules:
                if p.est_vivante():
                    p.mettre_a_jour(delta_temps)
                    particules_vivantes.append(p)
            self.particules = particules_vivantes

            # 4) Affichage
            self.afficher()

            # 5) Limitation du framerate (FPS)
            self.horloge.tick(self.config.fps_affichage)

        pygame.quit()

    # ==============================================================
    # GESTION CLAVIER
    # ==============================================================

    def gerer_touche(self, touche):
        """
        Traite une touche pressée.
        Renvoie False si le jeu doit se fermer (ECHAP), True sinon.

        Touches globales (actives dans TOUS les états) :
          M   → mute (sauf en game over où M = retour menu)
        """
        if touche == pygame.K_ESCAPE:
            return False

        # M : mute/unmute — sauf en game over où M sert à revenir au menu
        if touche == pygame.K_m and self.moteur.etat != Etat.PERDU:
            self.son_coupe = not self.son_coupe
            return True

        etat = self.moteur.etat

        if etat == Etat.MENU:
            return self.gerer_touche_menu(touche)

        if etat == Etat.PERDU:
            return self.gerer_touche_perdu(touche)

        # En jeu ou en pause
        if touche == pygame.K_p:
            self.moteur.basculer_pause()
            return True

        # Directions : flèches OU ZQSD
        if touche in (pygame.K_UP, pygame.K_z):
            self.moteur.demander_direction(0, -1)
        elif touche in (pygame.K_DOWN, pygame.K_s):
            self.moteur.demander_direction(0, 1)
        elif touche in (pygame.K_LEFT, pygame.K_q):
            self.moteur.demander_direction(-1, 0)
        elif touche in (pygame.K_RIGHT, pygame.K_d):
            self.moteur.demander_direction(1, 0)

        return True

    def gerer_touche_menu(self, touche):
        """Traite les touches du menu principal."""
        if touche == pygame.K_SPACE:
            self.moteur.demarrer()
            return True
        if touche == pygame.K_w:
            self.moteur.basculer_sans_murs()
            return True
        if touche == pygame.K_t:
            self.moteur.basculer_portails()
            return True
        if touche == pygame.K_o:
            self.moteur.basculer_obstacles()
            return True
        if touche == pygame.K_1:
            self.moteur.choisir_vitesse("lent")
            return True
        if touche == pygame.K_2:
            self.moteur.choisir_vitesse("normal")
            return True
        if touche == pygame.K_3:
            self.moteur.choisir_vitesse("rapide")
            return True
        return True

    def gerer_touche_perdu(self, touche):
        """Traite les touches de l'écran game over."""
        if touche == pygame.K_r:
            self.moteur.demarrer()
            return True
        if touche == pygame.K_m:
            self.moteur.retour_menu()
            return True
        return True

    # ==============================================================
    # AFFICHAGE PRINCIPAL
    # ==============================================================

    def afficher(self):
        """Choisit quoi afficher selon l'état courant du jeu."""

        # Menu : page dédiée (fond sombre, pas de grille)
        if self.moteur.etat == Etat.MENU:
            self.afficher_menu_page()
            pygame.display.flip()
            return

        # --- Jeu, Pause, Perdu, Compte à rebours ---

        # 1) Fond (grille verte)
        self.dessiner_fond_grille()

        # 2) Obstacles
        if self.moteur.obstacles_actifs:
            for case in self.moteur.obstacles:
                self.dessiner_case(case, self.coul_obstacle, rayon=10, marge=5)

        # 3) Portails
        if self.moteur.portails_actifs and self.moteur.portail_a is not None:
            self.dessiner_portail(self.moteur.portail_a, self.coul_portail_a)
            self.dessiner_portail(self.moteur.portail_b, self.coul_portail_b)

        # 4) Pomme normale
        if self.moteur.pomme is not None:
            self.dessiner_pomme(self.moteur.pomme)

        # 5) Pomme bonus (avec timer visuel)
        if self.moteur.pomme_bonus is not None:
            ratio = self.moteur._timer_bonus / self.config.duree_pomme_bonus
            self.dessiner_pomme_bonus(self.moteur.pomme_bonus, ratio)

        # 6) Serpent (avec animation fluide)
        self.dessiner_serpent_fluide()

        # 7) Particules
        self.dessiner_particules()

        # 8) HUD (en jeu seulement)
        if self.moteur.etat in (Etat.JEU, Etat.PAUSE, Etat.COMPTE_A_REBOURS):
            self.afficher_hud_compact()

        # 9) Overlays selon l'état
        if self.moteur.etat == Etat.COMPTE_A_REBOURS:
            self.overlay_compte_a_rebours()
        elif self.moteur.etat == Etat.PAUSE:
            self.assombrir_ecran(120)
            self.overlay_pause()
        elif self.moteur.etat == Etat.PERDU:
            self.assombrir_ecran(140)
            self.overlay_perdu()

        # 10) Message "NIVEAU X" temporaire (s'affiche par-dessus tout)
        if self.moteur._timer_message_lvl > 0:
            self.overlay_niveau()

        pygame.display.flip()

    # ==============================================================
    # MENU
    # ==============================================================

    def afficher_menu_page(self):
        """Affiche la page de menu avec toutes les options."""
        self.dessiner_degrade_menu()

        # Titre principal
        self.centrer_texte("SNAKE", self.police_grande, 70, self.coul_texte)
        self.centrer_texte("Style Google - Édition Python", self.police, 145, self.coul_texte_faible)

        # Panneau central des options
        lp = 640
        hp = 330
        x  = (self.config.largeur_ecran - lp) // 2
        y  = 190
        self.dessiner_panneau(x, y, lp, hp)

        # === BOUTON JOUER ANIMÉ ===
        # L'opacité du badge ESPACE oscille pour attirer l'attention
        t       = time.perf_counter() - self.temps_debut
        pulse   = 0.5 + 0.5 * math.sin(t * 3.0)   # entre 0 et 1
        r_vert  = int(60 + 40 * pulse)              # vert qui pulse
        g_vert  = int(180 + 20 * pulse)
        coul_play = (r_vert, g_vert, 80)
        self.dessiner_ligne_option(x + 40, y + 42, "ESPACE", "Jouer", coul_play)

        # === OPTIONS ===
        self.dessiner_ligne_option_pastille(
            x + 40, y + 102, "1/2/3", "Vitesse",
            self.moteur.vitesse.upper(), (110, 140, 255)
        )
        self.dessiner_ligne_option_on_off(x + 40, y + 162, "W", "Sans murs",  self.moteur.sans_murs)
        self.dessiner_ligne_option_on_off(x + 40, y + 222, "T", "Portails",   self.moteur.portails_actifs)
        self.dessiner_ligne_option_on_off(x + 40, y + 282, "O", "Obstacles",  self.moteur.obstacles_actifs)

        # === BARRE BAS : raccourcis ===
        coul_mute   = (220, 90, 90)  if self.son_coupe else self.coul_texte_faible
        label_mute  = "M : Son ON" if self.son_coupe else "M : Son OFF"
        icone_mute  = "[MUTE]"      if self.son_coupe else "[SON]"
        legende_bas = f"{label_mute}   ECHAP : Quitter"
        self.centrer_texte(legende_bas, self.police_petite, 560, self.coul_texte_faible)

        # === MEILLEUR SCORE (en haut à droite pour ne pas surcharger le bas) ===
        texte_score = f"Record : {self.moteur.meilleur_score}"
        img_score = self.police_petite.render(texte_score, True, self.coul_combo)
        w_score = img_score.get_width() + 20
        h_score = img_score.get_height() + 10
        x_score = self.config.largeur_ecran - w_score - 20
        y_score = 20
        self.dessiner_rect_transparent(x_score, y_score, w_score, h_score, 10, (18, 20, 24, 200))
        pygame.draw.rect(self.ecran, self.coul_ui_bord, pygame.Rect(x_score, y_score, w_score, h_score), width=2, border_radius=10)
        self.ecran.blit(img_score, (x_score + 10, y_score + 5))

        # Pastille mute bien visible si actif (décalée un peu plus à gauche)
        if self.son_coupe:
            self.dessiner_rect_transparent(x_score - 80, 20, 64, h_score, 10, (180, 40, 40, 200))
            img_m = self.police_petite.render("MUTE", True, (255, 255, 255))
            self.ecran.blit(img_m, (x_score - 80 + 12, 20 + 5))

        # === POMME DÉCORATIVE ANIMÉE ===
        decalage_y = int(6 * (1 + math.sin(t * 2.0)))
        self.dessiner_pomme_deco(self.config.largeur_ecran - 110, 130 + decalage_y, 30)

    def dessiner_degrade_menu(self):
        """Dessine un fond avec un dégradé du haut vers le bas."""
        haut    = (12, 14, 18)
        bas     = (28, 32, 40)
        hauteur = self.config.hauteur_ecran
        largeur = self.config.largeur_ecran

        for y in range(hauteur):
            # Interpolation linéaire : t = 0 (haut) → t = 1 (bas)
            t = y / float(hauteur)
            r = int(haut[0] + (bas[0] - haut[0]) * t)
            g = int(haut[1] + (bas[1] - haut[1]) * t)
            b = int(haut[2] + (bas[2] - haut[2]) * t)
            pygame.draw.line(self.ecran, (r, g, b), (0, y), (largeur, y))

        self.dessiner_rect_transparent(70, 60, 660, 480, 35, (255, 255, 255, 22))

    def dessiner_panneau(self, x, y, w, h):
        """Dessine un panneau sombre avec bordure arrondie."""
        self.dessiner_rect_transparent(x + 6, y + 8, w, h, 18, (0, 0, 0, 90))
        self.dessiner_rect_transparent(x, y, w, h, 18, (18, 20, 24, 220))
        pygame.draw.rect(self.ecran, self.coul_ui_bord, pygame.Rect(x, y, w, h), width=2, border_radius=18)

    def dessiner_ligne_option(self, x, y, touche, action, coul_badge):
        self.dessiner_badge(x, y, 90, 40, touche, coul_badge)
        img = self.police.render(action, True, self.coul_texte)
        self.ecran.blit(img, (x + 110, y + 6))

    def dessiner_ligne_option_pastille(self, x, y, touche, action, valeur, coul_pastille):
        self.dessiner_badge(x, y, 90, 40, touche, coul_pastille)
        img = self.police.render(action, True, self.coul_texte)
        self.ecran.blit(img, (x + 110, y + 6))
        self.dessiner_pastille(x + 460, y + 6, valeur, coul_pastille)

    def dessiner_ligne_option_on_off(self, x, y, touche, action, est_on):
        self.dessiner_badge(x, y, 90, 40, touche, (150, 120, 255))
        img = self.police.render(action, True, self.coul_texte)
        self.ecran.blit(img, (x + 110, y + 6))
        if est_on:
            self.dessiner_pastille(x + 460, y + 6, "ON",  self.coul_on)
        else:
            self.dessiner_pastille(x + 460, y + 6, "OFF", self.coul_off)

    def dessiner_badge(self, x, y, w, h, texte, couleur):
        """Dessine un badge coloré avec du texte centré."""
        pygame.draw.rect(self.ecran, couleur, pygame.Rect(x, y, w, h), border_radius=10)
        # Ajustement dynamique : on réduit la police si le texte est long (ex: ESPACE)
        pol = self.police_petite if len(texte) > 3 else self.police
        img = pol.render(texte, True, (10, 10, 12))
        self.ecran.blit(img, (x + (w - img.get_width()) // 2, y + (h - img.get_height()) // 2))

    def dessiner_pastille(self, x, y, texte, couleur):
        """Dessine une petite pastille colorée (badge secondaire)."""
        w, h = 110, 34
        pygame.draw.rect(self.ecran, couleur, pygame.Rect(x, y, w, h), border_radius=14)
        img = self.police_petite.render(texte, True, (10, 10, 12))
        self.ecran.blit(img, (x + (w - img.get_width()) // 2, y + (h - img.get_height()) // 2))

    def centrer_texte(self, texte, police, y, couleur):
        """Affiche du texte centré horizontalement à la hauteur y."""
        img = police.render(texte, True, couleur)
        x   = (self.config.largeur_ecran - img.get_width()) // 2
        self.ecran.blit(img, (x, y))



    # ==============================================================
    # FOND ET CASES
    # ==============================================================

    def dessiner_fond_grille(self):
        """Dessine le damier vert (alternance de deux teintes)."""
        for y in range(self.config.hauteur_grille):
            for x in range(self.config.largeur_grille):
                # Damier : (x+y) pair → couleur A, impair → couleur B
                if (x + y) % 2 == 0:
                    couleur = self.coul_fond_a
                else:
                    couleur = self.coul_fond_b
                rect = pygame.Rect(
                    x * self.config.taille_case,
                    y * self.config.taille_case,
                    self.config.taille_case,
                    self.config.taille_case
                )
                pygame.draw.rect(self.ecran, couleur, rect)

    def dessiner_case(self, case, couleur, rayon=10, marge=6):
        """Dessine un élément (obstacle, etc.) dans une case avec marges."""
        x, y = case
        ts   = self.config.taille_case
        rect = pygame.Rect(x * ts + marge, y * ts + marge, ts - 2*marge, ts - 2*marge)
        pygame.draw.rect(self.ecran, couleur, rect, border_radius=rayon)

    # ==============================================================
    # SERPENT AVEC ANIMATION FLUIDE
    # ==============================================================

    def dessiner_serpent_fluide(self):
        """
        Dessine le serpent avec interpolation entre deux états (animation fluide).

        [NSI - Animation]
        Sans interpolation, le serpent "saute" d'une case à l'autre.
        Avec interpolation, on calcule une position intermédiaire entre
        l'état avant (serpent_precedent) et l'état après (serpent courant).
        alpha représente la progression entre ces deux états (0.0 à 1.0).
        """
        serpent_actuel = self.moteur.serpent
        serpent_avant  = self.moteur.serpent_precedent

        if len(serpent_actuel) == 0:
            return

        if self.moteur.etat == Etat.JEU:
            alpha = self.moteur.progression_etape()
        else:
            alpha = 1.0  # pas d'interpolation quand on n'est pas en jeu

        if len(serpent_avant) == 0:
            serpent_avant = list(serpent_actuel)

        for i in range(len(serpent_actuel)):
            case_courante = serpent_actuel[i]
            if i < len(serpent_avant):
                case_prec = serpent_avant[i]
            else:
                case_prec = case_courante

            # Position interpolée (flottante, pas entière)
            x_case, y_case = self.interpoler_case(case_prec, case_courante, alpha)

            # La tête est légèrement plus grande que le corps
            if i == 0:
                marge, rayon = 4, 14
            else:
                marge, rayon = 7, 12

            ts    = self.config.taille_case
            x_px  = int(x_case * ts + marge)
            y_px  = int(y_case * ts + marge)
            taille = ts - 2 * marge

            rect = pygame.Rect(x_px, y_px, taille, taille)
            pygame.draw.rect(self.ecran, self.coul_serpent,         rect, border_radius=rayon)
            pygame.draw.rect(self.ecran, self.coul_serpent_contour, rect, width=3, border_radius=rayon)

            if i == 0:
                self.dessiner_yeux(x_case, y_case)

    def interpoler_case(self, depart, arrivee, alpha):
        """
        Calcule la position intermédiaire entre deux cases.
        alpha = 0 → position de départ, alpha = 1 → position d'arrivée.
        Gère le cas du wrap (sans murs) pour ne pas traverser l'écran.
        """
        x0, y0 = depart
        x1, y1 = arrivee
        larg    = self.config.largeur_grille
        haut    = self.config.hauteur_grille

        if self.moteur.sans_murs:
            dx = x1 - x0
            dy = y1 - y0
            if abs(dx) > 1:
                x1 = x1 - larg if dx > 0 else x1 + larg
            if abs(dy) > 1:
                y1 = y1 - haut if dy > 0 else y1 + haut

        x = x0 + (x1 - x0) * alpha
        y = y0 + (y1 - y0) * alpha

        if self.moteur.sans_murs:
            x = x % larg
            y = y % haut

        return x, y

    def dessiner_yeux(self, x_case, y_case):
        """Dessine les deux yeux de la tête du serpent selon sa direction."""
        ts       = self.config.taille_case
        cx       = int(x_case * ts + ts // 2)
        cy       = int(y_case * ts + ts // 2)
        dx, dy   = self.moteur.direction
        decalage = 7
        rayon    = 4

        if dx == 1:
            oeil1 = (cx + decalage, cy - decalage)
            oeil2 = (cx + decalage, cy + decalage)
        elif dx == -1:
            oeil1 = (cx - decalage, cy - decalage)
            oeil2 = (cx - decalage, cy + decalage)
        elif dy == 1:
            oeil1 = (cx - decalage, cy + decalage)
            oeil2 = (cx + decalage, cy + decalage)
        else:
            oeil1 = (cx - decalage, cy - decalage)
            oeil2 = (cx + decalage, cy - decalage)

        pygame.draw.circle(self.ecran, (250, 250, 250), oeil1, rayon)
        pygame.draw.circle(self.ecran, (250, 250, 250), oeil2, rayon)

    # ==============================================================
    # PARTICULES
    # ==============================================================

    def dessiner_particules(self):
        """Dessine toutes les particules vivantes avec fade-out."""
        for p in self.particules:
            # Calcul de la transparence : 255 (opaque) → 0 (invisible)
            a = int(255 * (1.0 - p.ratio_mort()))
            # Surface temporaire avec canal alpha pour la transparence
            surf = pygame.Surface((p.rayon * 2, p.rayon * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (p.couleur[0], p.couleur[1], p.couleur[2], a),
                               (p.rayon, p.rayon), p.rayon)
            self.ecran.blit(surf, (int(p.x) - p.rayon, int(p.y) - p.rayon))

    # ==============================================================
    # POMMES ET PORTAILS
    # ==============================================================

    def dessiner_pomme(self, case):
        """Dessine la pomme normale (rouge avec reflet et feuille)."""
        x, y    = case
        ts      = self.config.taille_case
        cx, cy  = x * ts + ts // 2, y * ts + ts // 2
        rayon   = int(ts * 0.42)

        pygame.draw.circle(self.ecran, self.coul_pomme,        (cx, cy), rayon)
        pygame.draw.circle(self.ecran, self.coul_pomme_reflet, (cx - 7, cy - 7), max(3, rayon // 3))
        pygame.draw.rect(  self.ecran, self.coul_feuille,
                           pygame.Rect(cx - 3, cy - rayon - 3, 9, 12), border_radius=4)

    def dessiner_pomme_bonus(self, case, ratio_temps):
        """
        Dessine la pomme bonus dorée avec un arc indicateur de temps.
        ratio_temps : 1.0 = plein temps, 0.0 = va expirer.
        """
        x, y   = case
        ts     = self.config.taille_case
        cx, cy = x * ts + ts // 2, y * ts + ts // 2

        # Pulsation légère (effet "vivant")
        t     = time.perf_counter() - self.temps_debut
        pulse = 1.0 + 0.08 * math.sin(t * 8.0)
        rayon = int(ts * 0.42 * pulse)

        pygame.draw.circle(self.ecran, self.coul_pomme_bonus, (cx, cy), rayon)
        pygame.draw.circle(self.ecran, self.coul_pomme_br,    (cx - 7, cy - 7), max(3, rayon // 3))
        pygame.draw.rect(  self.ecran, self.coul_feuille,
                           pygame.Rect(cx - 3, cy - rayon - 3, 9, 12), border_radius=4)

        # Arc de timer : cercle partiel autour de la pomme
        r_arc    = rayon + 7
        rect_arc = pygame.Rect(cx - r_arc, cy - r_arc, r_arc * 2, r_arc * 2)
        angle    = int(360 * ratio_temps)
        if angle > 0:
            pygame.draw.arc(self.ecran, self.coul_pomme_bonus, rect_arc,
                            math.radians(90), math.radians(90 + angle), 3)

    def dessiner_pomme_deco(self, cx, cy, rayon):
        """Dessine une pomme décorative (utilisée dans le menu)."""
        pygame.draw.circle(self.ecran, self.coul_pomme,        (cx, cy), rayon)
        pygame.draw.circle(self.ecran, self.coul_pomme_reflet, (cx - 10, cy - 10), max(5, rayon // 3))
        pygame.draw.rect(  self.ecran, self.coul_feuille,
                           pygame.Rect(cx - 4, cy - rayon - 6, 12, 16), border_radius=5)

    def dessiner_portail(self, case, couleur):
        """Dessine un portail (cercle vide coloré)."""
        if case is None:
            return
        x, y   = case
        ts     = self.config.taille_case
        cx, cy = x * ts + ts // 2, y * ts + ts // 2
        pygame.draw.circle(self.ecran, couleur, (cx, cy), int(ts * 0.42), width=5)

    # ==============================================================
    # HUD (Heads-Up Display) — informations en jeu
    # ==============================================================

    def afficher_hud_compact(self):
        """
        Affiche un panneau en haut à gauche avec :
        - le niveau, score, meilleur_score
        - la vitesse en t/s (feedback de l'accélération)
        - le combo ×2 si actif
        - l'icône MUTE si les sons sont coupés
        """
        tps   = self.moteur.tps_actuel()
        combo = "  ×2 !" if self.moteur.combo_actif else ""
        mute  = "  🔇" if self.son_coupe else ""

        # On utilise une grande police pour le score (lisible de loin)
        score_txt  = str(self.moteur.score)
        high_txt   = "Best:" + str(self.moteur.meilleur_score)
        niv_txt    = "Niv." + str(self.moteur.niveau)
        vit_txt    = f"{tps:.0f}t/s"
        extra      = combo + mute

        ligne = f"{niv_txt}  Score:{score_txt}  {high_txt}  {vit_txt}{extra}"

        coul  = self.coul_combo if self.moteur.combo_actif else self.coul_texte
        img   = self.police.render(ligne, True, coul)   # police normale (plus grosse qu'avant)

        px, py = 16, 10
        w      = img.get_width()  + 2 * px
        h      = img.get_height() + 2 * py
        x, y   = 10, 10

        self.dessiner_rect_transparent(x + 3, y + 4, w, h, 14, (0, 0, 0, 100))
        self.dessiner_rect_transparent(x,     y,     w, h, 14, (18, 20, 24, 160))
        pygame.draw.rect(self.ecran, self.coul_ui_bord, pygame.Rect(x, y, w, h), width=2, border_radius=14)
        self.ecran.blit(img, (x + px, y + py))

    # ==============================================================
    # OVERLAYS
    # ==============================================================

    def overlay_compte_a_rebours(self):
        """
        Affiche le compte à rebours (3-2-1-GO) au centre de l'écran.
        Le chiffre grossit et s'efface progressivement (effet "pop").
        """
        self.assombrir_ecran(80)
        chiffre = self.moteur.compte_affiche

        if chiffre == 0:
            texte  = "GO !"
            couleur = self.coul_on
        else:
            texte  = str(chiffre)
            couleur = self.coul_texte

        self.centrer_texte(texte,          self.police_xg,     200, couleur)
        self.centrer_texte("Prépare toi !", self.police_petite, 310, self.coul_texte_faible)

    def overlay_niveau(self):
        """Affiche brièvement 'NIVEAU X !' quand le joueur monte de niveau."""
        # Le message s'assombrit progressivement (fade-out)
        ratio  = self.moteur._timer_message_lvl / self.config.duree_message_lvl
        alpha  = int(ratio * 255)
        surf   = pygame.Surface((self.config.largeur_ecran, 80), pygame.SRCALPHA)
        surf.fill((0, 0, 0, int(alpha * 0.5)))
        self.ecran.blit(surf, (0, 250))

        texte  = f"NIVEAU {self.moteur.niveau} !"
        img    = self.police_grande.render(texte, True, self.coul_combo)
        img.set_alpha(alpha)
        x      = (self.config.largeur_ecran - img.get_width()) // 2
        self.ecran.blit(img, (x, 255))

    def overlay_pause(self):
        """Affiche l'écran de pause."""
        self.centrer_texte("PAUSE",         self.police_grande, 220, self.coul_texte)
        self.centrer_texte("P : Reprendre", self.police,        310, self.coul_texte_faible)

    def overlay_perdu(self):
        """Affiche l'écran game over avec le score final."""
        self.centrer_texte("PERDU",                          self.police_grande, 190, self.coul_texte)
        self.centrer_texte("R : Rejouer   |   M : Menu",    self.police,        290, self.coul_texte_faible)
        self.centrer_texte("Score final : " + str(self.moteur.score), self.police, 330, self.coul_texte_faible)

    def assombrir_ecran(self, alpha):
        """
        Pose une couche noire semi-transparente sur tout l'écran.
        alpha : opacité de 0 (invisible) à 255 (opaque).
        """
        couche = pygame.Surface((self.config.largeur_ecran, self.config.hauteur_ecran))
        couche.set_alpha(alpha)
        couche.fill((0, 0, 0))
        self.ecran.blit(couche, (0, 0))

    # ==============================================================
    # TRANSPARENCE
    # ==============================================================

    def dessiner_rect_transparent(self, x, y, w, h, rayon, couleur_rgba):
        """
        Dessine un rectangle arrondi semi-transparent.
        couleur_rgba : tuple (R, G, B, A) avec A = opacité 0..255.
        On crée une surface avec canal alpha (SRCALPHA), on y dessine,
        puis on la colle sur l'écran principal.
        """
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surface, couleur_rgba, pygame.Rect(0, 0, w, h), border_radius=rayon)
        self.ecran.blit(surface, (x, y))


# ==============================================================
# POINT D'ENTRÉE
# [NSI] Cette fonction est appelée par main.py.
# Elle crée la config et lance l'application.
# ==============================================================

def lancer():
    """Lance le jeu."""
    app = ApplicationPygame(Config())
    app.lancer()
