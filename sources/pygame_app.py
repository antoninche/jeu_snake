# pygame_app.py
# Interface Pygame (affichage + clavier).
# Objectifs :
# - Menu = vraie page (pas de jeu derrière)
# - HUD en jeu = petit, discret (ne gêne pas)
# - Animation fluide : interpolation entre serpent_precedent et serpent

import time
import pygame
import math

from config import Config
from engine import MoteurSnake
from storage import load_highscore, save_highscore


class ApplicationPygame:
    def __init__(self, cfg):
        self.cfg = cfg

        pygame.init()
        self.ecran = pygame.display.set_mode((cfg.largeur_ecran, cfg.hauteur_ecran))
        pygame.display.set_caption("Snake (style Google)")

        self.horloge = pygame.time.Clock()

        # Polices
        self.police = pygame.font.SysFont(None, 34)
        self.police_petite = pygame.font.SysFont(None, 26)
        self.police_grande = pygame.font.SysFont(None, 72)

        # Highscore
        highscore = load_highscore(cfg.fichier_highscore)

        # Moteur
        self.moteur = MoteurSnake(cfg, highscore=highscore, graine=int(time.time()))

        # ===== Couleurs =====
        self.couleur_fond_a = (170, 215, 81)
        self.couleur_fond_b = (162, 209, 73)

        self.couleur_ui_fond = (18, 20, 24)
        self.couleur_ui_bord = (40, 45, 55)

        self.couleur_serpent = (65, 110, 240)
        self.couleur_serpent_contour = (40, 75, 190)

        self.couleur_obstacle = (70, 70, 80)

        self.couleur_pomme = (230, 60, 60)
        self.couleur_pomme_reflet = (255, 160, 160)
        self.couleur_feuille = (70, 180, 90)

        self.couleur_portail_a = (120, 80, 220)
        self.couleur_portail_b = (70, 220, 180)

        self.couleur_texte = (245, 245, 245)
        self.couleur_texte_faible = (190, 195, 205)

        self.couleur_on = (80, 200, 120)
        self.couleur_off = (220, 90, 90)

        # Temps (petites animations UI)
        self.temps_debut = time.perf_counter()

    # =========================
    # Boucle principale
    # =========================

    def run(self):
        dernier_temps = time.perf_counter()
        continuer = True

        while continuer:
            maintenant = time.perf_counter()
            dt = maintenant - dernier_temps
            dernier_temps = maintenant

            for evenement in pygame.event.get():
                if evenement.type == pygame.QUIT:
                    continuer = False
                elif evenement.type == pygame.KEYDOWN:
                    continuer = self.gerer_touche(evenement.key)

            # Mise à jour moteur
            self.moteur.update(dt)

            # Sauvegarde highscore si besoin
            if self.moteur.highscore_a_sauver:
                save_highscore(self.cfg.fichier_highscore, self.moteur.highscore)
                self.moteur.highscore_a_sauver = False

            # Affichage
            self.afficher()

            self.horloge.tick(self.cfg.fps_affichage)

        pygame.quit()

    # =========================
    # Clavier
    # =========================

    def gerer_touche(self, touche):
        if touche == pygame.K_ESCAPE:
            return False

        etat = self.moteur.etat

        if etat == "menu":
            return self.gerer_touche_menu(touche)

        if etat == "perdu":
            return self.gerer_touche_perdu(touche)

        # jeu / pause
        if touche == pygame.K_p:
            self.moteur.basculer_pause()
            return True

        # directions
        if touche == pygame.K_UP:
            self.moteur.demander_direction(0, -1)
        elif touche == pygame.K_DOWN:
            self.moteur.demander_direction(0, 1)
        elif touche == pygame.K_LEFT:
            self.moteur.demander_direction(-1, 0)
        elif touche == pygame.K_RIGHT:
            self.moteur.demander_direction(1, 0)

        return True

    def gerer_touche_menu(self, touche):
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
        if touche == pygame.K_r:
            self.moteur.demarrer()
            return True
        if touche == pygame.K_m:
            self.moteur.retour_menu()
            return True
        return True

    # =========================
    # Affichage (menu / jeu)
    # =========================

    def afficher(self):
        # MENU : page dédiée
        if self.moteur.etat == "menu":
            self.afficher_menu_page()
            pygame.display.flip()
            return

        # JEU
        self.dessiner_fond_grille()

        if self.moteur.obstacles_actifs:
            for case in self.moteur.obstacles:
                self.dessiner_case(case, self.couleur_obstacle, rayon=10, marge=5)

        if self.moteur.portails_actifs and self.moteur.portail_a is not None:
            self.dessiner_portail(self.moteur.portail_a, self.couleur_portail_a)
            self.dessiner_portail(self.moteur.portail_b, self.couleur_portail_b)

        if self.moteur.pomme is not None:
            self.dessiner_pomme(self.moteur.pomme)

        # Serpent (fluide)
        self.dessiner_serpent_fluide()

        # HUD compact (ne gêne plus)
        self.afficher_hud_compact()

        # Pause / Perdu
        if self.moteur.etat == "pause":
            self.assombrir_ecran(120)
            self.overlay_pause()
        elif self.moteur.etat == "perdu":
            self.assombrir_ecran(140)
            self.overlay_perdu()

        pygame.display.flip()

    # =========================
    # MENU : page dédiée
    # =========================

    def afficher_menu_page(self):
        self.dessiner_degrade_menu()

        self.centrer_texte("SNAKE", self.police_grande, 80, self.couleur_texte)
        self.centrer_texte("Style Google - version NSI", self.police, 150, self.couleur_texte_faible)

        # Panneau central (options)
        largeur_panneau = 640
        hauteur_panneau = 330
        x = (self.cfg.largeur_ecran - largeur_panneau) // 2
        y = 205

        self.dessiner_panneau(x, y, largeur_panneau, hauteur_panneau)

        # Lignes options
        self.dessiner_ligne_option(x + 40, y + 42, "ESPACE", "Jouer", self.couleur_on)

        # Vitesse : pill à droite (plus propre, pas collé à la pomme)
        self.dessiner_ligne_option_pastille(
            x + 40, y + 102,
            "1/2/3",
            "Vitesse",
            self.moteur.vitesse.upper(),
            (110, 140, 255),
        )

        self.dessiner_ligne_option_on_off(x + 40, y + 162, "W", "Sans murs", self.moteur.sans_murs)
        self.dessiner_ligne_option_on_off(x + 40, y + 222, "T", "Portails", self.moteur.portails_actifs)
        self.dessiner_ligne_option_on_off(x + 40, y + 282, "O", "Obstacles", self.moteur.obstacles_actifs)

        # Highscore + aide
        self.centrer_texte("Highscore : " + str(self.moteur.highscore), self.police, 545, self.couleur_texte_faible)
        self.centrer_texte("ECHAP : Quitter", self.police_petite, 575, self.couleur_texte_faible)

        # Pomme décorative : on la sort du panneau (plus de chevauchement)
        # Petite animation "bounce" très simple
        t = time.perf_counter() - self.temps_debut
        decalage_y = int(6 * (1 + math.sin(t * 2.0)))  # 0..12 environ

        self.dessiner_pomme_deco(self.cfg.largeur_ecran - 110, 135 + decalage_y, 30)

    def dessiner_degrade_menu(self):
        haut = (12, 14, 18)
        bas = (28, 32, 40)

        hauteur = self.cfg.hauteur_ecran
        largeur = self.cfg.largeur_ecran

        for y in range(hauteur):
            t = y / float(hauteur)
            r = int(haut[0] + (bas[0] - haut[0]) * t)
            g = int(haut[1] + (bas[1] - haut[1]) * t)
            b = int(haut[2] + (bas[2] - haut[2]) * t)
            pygame.draw.line(self.ecran, (r, g, b), (0, y), (largeur, y))

        # grand panneau transparent léger derrière
        self.dessiner_rectangle_transparent(70, 70, 660, 460, 35, (255, 255, 255, 22))

    def dessiner_panneau(self, x, y, w, h):
        self.dessiner_rectangle_transparent(x + 6, y + 8, w, h, 18, (0, 0, 0, 90))
        self.dessiner_rectangle_transparent(x, y, w, h, 18, (18, 20, 24, 220))
        pygame.draw.rect(self.ecran, self.couleur_ui_bord, pygame.Rect(x, y, w, h), width=2, border_radius=18)

    def dessiner_ligne_option(self, x, y, touche, action, couleur_badge):
        self.dessiner_badge(x, y, 90, 40, touche, couleur_badge)
        img = self.police.render(action, True, self.couleur_texte)
        self.ecran.blit(img, (x + 110, y + 6))

    def dessiner_ligne_option_pastille(self, x, y, touche, action, valeur, couleur_pastille):
        self.dessiner_badge(x, y, 90, 40, touche, couleur_pastille)
        img = self.police.render(action, True, self.couleur_texte)
        self.ecran.blit(img, (x + 110, y + 6))
        # pastille valeur à droite
        self.dessiner_pastille(x + 460, y + 6, valeur, couleur_pastille)

    def dessiner_ligne_option_on_off(self, x, y, touche, action, est_on):
        self.dessiner_badge(x, y, 90, 40, touche, (150, 120, 255))
        img = self.police.render(action, True, self.couleur_texte)
        self.ecran.blit(img, (x + 110, y + 6))
        if est_on:
            self.dessiner_pastille(x + 460, y + 6, "ON", self.couleur_on)
        else:
            self.dessiner_pastille(x + 460, y + 6, "OFF", self.couleur_off)

    def dessiner_badge(self, x, y, w, h, texte, couleur):
        pygame.draw.rect(self.ecran, couleur, pygame.Rect(x, y, w, h), border_radius=10)
        img = self.police.render(texte, True, (10, 10, 12))
        tx = x + (w - img.get_width()) // 2
        ty = y + (h - img.get_height()) // 2
        self.ecran.blit(img, (tx, ty))

    def dessiner_pastille(self, x, y, texte, couleur):
        w = 110
        h = 34
        pygame.draw.rect(self.ecran, couleur, pygame.Rect(x, y, w, h), border_radius=14)
        img = self.police_petite.render(texte, True, (10, 10, 12))
        tx = x + (w - img.get_width()) // 2
        ty = y + (h - img.get_height()) // 2
        self.ecran.blit(img, (tx, ty))

    def centrer_texte(self, texte, police, y, couleur):
        img = police.render(texte, True, couleur)
        x = (self.cfg.largeur_ecran - img.get_width()) // 2
        self.ecran.blit(img, (x, y))

    # =========================
    # Jeu : fond / cases
    # =========================

    def dessiner_fond_grille(self):
        for y in range(self.cfg.hauteur_grille):
            for x in range(self.cfg.largeur_grille):
                couleur = self.couleur_fond_a if (x + y) % 2 == 0 else self.couleur_fond_b
                rect = pygame.Rect(
                    x * self.cfg.taille_case,
                    y * self.cfg.taille_case,
                    self.cfg.taille_case,
                    self.cfg.taille_case,
                )
                pygame.draw.rect(self.ecran, couleur, rect)

    def dessiner_case(self, case, couleur, rayon=10, marge=6):
        x, y = case
        rect = pygame.Rect(
            x * self.cfg.taille_case + marge,
            y * self.cfg.taille_case + marge,
            self.cfg.taille_case - 2 * marge,
            self.cfg.taille_case - 2 * marge,
        )
        pygame.draw.rect(self.ecran, couleur, rect, border_radius=rayon)

    # =========================
    # Serpent : animation fluide
    # =========================

    def dessiner_serpent_fluide(self):
        serpent_actuel = self.moteur.serpent
        serpent_avant = self.moteur.serpent_precedent

        if serpent_actuel is None or len(serpent_actuel) == 0:
            return

        # alpha : 0..1 (progression entre deux ticks)
        if self.moteur.etat != "jeu":
            alpha = 1.0
        else:
            alpha = self.moteur.progression_tick()

        if serpent_avant is None or len(serpent_avant) == 0:
            serpent_avant = list(serpent_actuel)

        for i in range(len(serpent_actuel)):
            case_courante = serpent_actuel[i]
            if i < len(serpent_avant):
                case_precedente = serpent_avant[i]
            else:
                case_precedente = case_courante

            x_case, y_case = self.interpoler_case(case_precedente, case_courante, alpha)

            if i == 0:
                marge = 4
                rayon = 14
            else:
                marge = 7
                rayon = 12

            x_px = int(x_case * self.cfg.taille_case + marge)
            y_px = int(y_case * self.cfg.taille_case + marge)
            taille = self.cfg.taille_case - 2 * marge

            rect = pygame.Rect(x_px, y_px, taille, taille)
            pygame.draw.rect(self.ecran, self.couleur_serpent, rect, border_radius=rayon)
            pygame.draw.rect(self.ecran, self.couleur_serpent_contour, rect, width=3, border_radius=rayon)

            if i == 0:
                self.dessiner_yeux_tete_fluide(x_case, y_case)

    def interpoler_case(self, case_depart, case_arrivee, alpha):
        x0, y0 = case_depart
        x1, y1 = case_arrivee

        largeur = self.cfg.largeur_grille
        hauteur = self.cfg.hauteur_grille

        # Wrap : corriger le "chemin" pour glisser par le bord
        if self.moteur.sans_murs:
            dx = x1 - x0
            dy = y1 - y0

            if abs(dx) > 1:
                x1 = x1 - largeur if dx > 0 else x1 + largeur
            if abs(dy) > 1:
                y1 = y1 - hauteur if dy > 0 else y1 + hauteur

        x = x0 + (x1 - x0) * alpha
        y = y0 + (y1 - y0) * alpha

        if self.moteur.sans_murs:
            x = x % largeur
            y = y % hauteur

        return x, y

    def dessiner_yeux_tete_fluide(self, x_case, y_case):
        taille = self.cfg.taille_case
        centre_x = int(x_case * taille + taille // 2)
        centre_y = int(y_case * taille + taille // 2)

        dx, dy = self.moteur.direction

        decalage = 7
        rayon_oeil = 4

        if dx == 1:
            oeil1 = (centre_x + decalage, centre_y - decalage)
            oeil2 = (centre_x + decalage, centre_y + decalage)
        elif dx == -1:
            oeil1 = (centre_x - decalage, centre_y - decalage)
            oeil2 = (centre_x - decalage, centre_y + decalage)
        elif dy == 1:
            oeil1 = (centre_x - decalage, centre_y + decalage)
            oeil2 = (centre_x + decalage, centre_y + decalage)
        else:
            oeil1 = (centre_x - decalage, centre_y - decalage)
            oeil2 = (centre_x + decalage, centre_y - decalage)

        pygame.draw.circle(self.ecran, (250, 250, 250), oeil1, rayon_oeil)
        pygame.draw.circle(self.ecran, (250, 250, 250), oeil2, rayon_oeil)

    # =========================
    # Pomme / portails
    # =========================

    def dessiner_pomme(self, case):
        x, y = case
        taille = self.cfg.taille_case
        centre_x = x * taille + taille // 2
        centre_y = y * taille + taille // 2

        rayon = int(taille * 0.42)
        pygame.draw.circle(self.ecran, self.couleur_pomme, (centre_x, centre_y), rayon)
        pygame.draw.circle(
            self.ecran, self.couleur_pomme_reflet, (centre_x - 7, centre_y - 7), max(3, rayon // 3)
        )

        rect_feuille = pygame.Rect(centre_x - 3, centre_y - rayon - 3, 9, 12)
        pygame.draw.rect(self.ecran, self.couleur_feuille, rect_feuille, border_radius=4)

    def dessiner_pomme_deco(self, centre_x, centre_y, rayon):
        pygame.draw.circle(self.ecran, self.couleur_pomme, (centre_x, centre_y), rayon)
        pygame.draw.circle(
            self.ecran, self.couleur_pomme_reflet, (centre_x - 10, centre_y - 10), max(5, rayon // 3)
        )
        rect_feuille = pygame.Rect(centre_x - 4, centre_y - rayon - 6, 12, 16)
        pygame.draw.rect(self.ecran, self.couleur_feuille, rect_feuille, border_radius=5)

    def dessiner_portail(self, case, couleur):
        x, y = case
        taille = self.cfg.taille_case
        centre_x = x * taille + taille // 2
        centre_y = y * taille + taille // 2
        rayon = int(taille * 0.42)
        pygame.draw.circle(self.ecran, couleur, (centre_x, centre_y), rayon, width=5)

    # =========================
    # HUD compact (en jeu)
    # =========================

    def afficher_hud_compact(self):
        # Petit chip discret en haut-gauche
        texte = "Score : " + str(self.moteur.score) + "   High : " + str(self.moteur.highscore)
        img = self.police_petite.render(texte, True, self.couleur_texte)

        padding_x = 14
        padding_y = 8
        w = img.get_width() + 2 * padding_x
        h = img.get_height() + 2 * padding_y

        x = 12
        y = 12

        self.dessiner_rectangle_transparent(x + 3, y + 4, w, h, 14, (0, 0, 0, 80))
        self.dessiner_rectangle_transparent(x, y, w, h, 14, (18, 20, 24, 135))
        pygame.draw.rect(self.ecran, self.couleur_ui_bord, pygame.Rect(x, y, w, h), width=2, border_radius=14)

        self.ecran.blit(img, (x + padding_x, y + padding_y))

    # =========================
    # Overlays
    # =========================

    def overlay_pause(self):
        self.centrer_texte("PAUSE", self.police_grande, 220, self.couleur_texte)
        self.centrer_texte("P : Reprendre", self.police, 310, self.couleur_texte_faible)

    def overlay_perdu(self):
        self.centrer_texte("PERDU", self.police_grande, 190, self.couleur_texte)
        self.centrer_texte("R : Rejouer   |   M : Menu", self.police, 290, self.couleur_texte_faible)
        self.centrer_texte("Score final : " + str(self.moteur.score), self.police, 330, self.couleur_texte_faible)

    def assombrir_ecran(self, alpha):
        couche = pygame.Surface((self.cfg.largeur_ecran, self.cfg.hauteur_ecran))
        couche.set_alpha(alpha)
        couche.fill((0, 0, 0))
        self.ecran.blit(couche, (0, 0))

    # =========================
    # Transparence
    # =========================

    def dessiner_rectangle_transparent(self, x, y, w, h, rayon, couleur_rgba):
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surface, couleur_rgba, pygame.Rect(0, 0, w, h), border_radius=rayon)
        self.ecran.blit(surface, (x, y))


def run():
    app = ApplicationPygame(Config())
    app.run()
