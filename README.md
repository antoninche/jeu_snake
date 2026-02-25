# Jeu Snake (Python + Pygame)

Un Snake **inspiré du Snake Google** : déplacement **en cases**, interface moderne, et surtout un code **simple et propre** (niveau Terminale NSI).

## ✨ Fonctionnalités
- Déplacement en cases (logique claire côté moteur).
- Rendu moderne (grille verte “Google”, snake arrondi, pomme lisible).
- Menu complet avant de jouer (pas de jeu derrière).
- Modes :
  - **Sans murs** (wrap)
  - **Portails**
  - **Obstacles**
- Vitesses : **lent / normal / rapide**
- Highscore sauvegardé dans `highscore.txt`.

## 🧱 Architecture
- `config.py` : réglages (fenêtre, grille, vitesses…)
- `engine.py` : logique du jeu (sans Pygame)
- `pygame_app.py` : affichage + inputs Pygame
- `storage.py` : lecture/écriture highscore
- `main.py` : lance le jeu

## ▶️ Installation
### Prérequis
- Python 3.10+ (3.11 recommandé)
- Pygame

### Lancer
```bash
git clone https://github.com/antoninche/jeu_snake.git
cd jeu_snake
python -m pip install -r requirements.txt
cd sources
python main.py
