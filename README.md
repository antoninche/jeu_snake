# 🐍 Snake — Projet Personnel
## Recréation du Snake Google en Python (Pygame) avec animation fluide et architecture propre

---

## 📌 Présentation

Ce dépôt contient un **jeu Snake** développé en **Python**, avec une interface graphique réalisée en **Pygame**, inspiré du **Snake Google**.

Le projet ne se limite pas à “faire un Snake” :  
il vise aussi une **architecture claire** (niveau Terminale NSI) pour pouvoir **complexifier** facilement ensuite.

Il intègre :

- 🎮 Une interface moderne (menu + HUD discret)
- 🧱 Un moteur de jeu **indépendant** de l’interface (testable, propre)
- 🌀 Une **animation fluide** (interpolation entre deux états en cases)
- ⚙️ Des modes inspirés du Snake Google (wrap / portails / obstacles)
- 🏆 Un highscore persistant (stocké dans un dossier utilisateur)

---

## 🎮 Règles du jeu

- Le serpent se déplace sur une **grille en cases**.
- Le joueur dirige le serpent avec les flèches.
- Le but est de **manger des pommes** pour grandir et gagner des points.
- La partie se termine si le serpent :
  - se mord (collision avec lui-même)
  - touche un obstacle (si activé)
  - touche un mur (si “sans murs” désactivé)

---

## 🚀 Fonctionnalités principales

### 🎮 Gameplay
- Déplacement en cases (stable, simple, fidèle à l’esprit “Google Snake”)
- Score et highscore
- Pause
- Game Over avec relance rapide

### ⚙️ Options (menu)
- **Sans murs (wrap)** : le serpent réapparaît de l’autre côté
- **Portails** : téléportation entre 2 cases
- **Obstacles** : cases bloquantes
- Vitesses : **lent / normal / rapide**

### 🎨 Rendu moderne
- Grille verte “Google”
- Snake arrondi, pomme lisible
- HUD compact (ne gêne pas le plateau)
- Menu sur une vraie page (le jeu n’apparaît pas derrière)


## 🏆 Highscore (cross-platform)

Le highscore est :

- une **variable Python** pendant la partie
- sauvegardé dans un fichier **dans un dossier utilisateur** 

Ce choix permet :
- ✅ compatibilité macOS `.app`
- ✅ compatibilité Windows `.exe`

---

## 🧩 Architecture du projet

Séparation claire des responsabilités :

- `engine.py` → **moteur du jeu** (règles, collisions, score, génération) **sans Pygame**
- `pygame_app.py` → **interface graphique** (menu, affichage, inputs, overlays)
- `config.py` → réglages (taille grille, fps, vitesses…)
- `storage.py` → lecture/écriture du highscore (dossier utilisateur)
- `main.py` → point d’entrée

Cette organisation permet :
- un moteur testable indépendamment
- une maintenance plus simple
- une évolution facile (modes, power-ups, niveaux…)

---

## 📂 Structure du projet

```text
jeu_snake/
│
├── requirements.txt
├── README.md
│
├── sources/
│   ├── main.py
│   ├── config.py
│   ├── engine.py
│   ├── pygame_app.py
│   └── storage.py
│
└── docs/
    ├── index.html
    ├── styles.css
    └── assets/
        ├── screen-menu.png
        └── screen-gameover.png
```
---

## 📦 Lancer le jeu via la Release (sans installer Python)

Pour les utilisateurs qui ne veulent pas installer Python, le jeu est disponible en version packagée dans l’onglet **Releases** du dépôt GitHub.

### 🍎 macOS (.app)
1. Va dans **Releases** (sur GitHub, à droite du dépôt)
2. Télécharge le fichier : `SnakeGoogle-vX.X.X-macos.zip`
3. Dézippe → tu obtiens `SnakeGoogle.app`
4. Lance le jeu :
   - Double-clic sur l’app  
   - ou si macOS bloque : clic droit → **Ouvrir** → **Ouvrir**

⚠️ Si macOS affiche un blocage de sécurité (“développeur non identifié”), c’est normal pour une app non signée.

### 🪟 Windows (.exe) *(si disponible)*
1. Va dans **Releases**
2. Télécharge : `SnakeGoogle-vX.X.X-windows.zip`
3. Dézippe → `SnakeGoogle.exe`
4. Double-clique pour lancer

⚠️ Windows Defender peut afficher un avertissement sur un `.exe` non signé : choisir “Informations complémentaires” puis “Exécuter quand même” si tu fais confiance à la source (ce dépôt).

---
