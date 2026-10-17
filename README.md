# 🐣 DevPet

Un animal virtuel qui grandit avec ton activité de développement. Il se nourrit de tes **commits GitHub**, de tes **dépôts** et de ta **régularité**, et son humeur reflète tes habitudes (séries de jours, commits de nuit, longues pauses).

<!-- ![Aperçu de DevPet](docs/screenshot.png) -->

## Fonctionnement

| Habitude détectée | Effet sur l'animal |
|---|---|
| Commits des 90 derniers jours, nombre de dépôts, série en cours | **XP** et stade d'évolution : Œuf → Bébé → Jeune → Adulte |
| Langage principal des dépôts récents | **Forme finale** : Backend → Golem, Frontend → Chat, IA / data → Hibou, profil mixte → Dragon |
| Commits récents et série de jours consécutifs | **Bonheur** |
| Commits de nuit (23h–5h) et grosses journées | **Énergie** (elle remonte quand tu te reposes) |
| Plusieurs jours sans activité | L'animal s'ennuie et te le dit |

Le widget affiche aussi les habitudes détectées (moment préféré, commits de nuit, profil dominant) et les 28 derniers jours d'activité.

## Architecture

```
Navigateur ──► index.html (widget, JavaScript sans dépendance)
                 │
                 ├─ sans backend : API publique GitHub (dépôts publics, 60 requêtes/h par visiteur)
                 └─ avec backend : backend/main.py (FastAPI) ──► API GitHub avec jeton
                                   (activité privée incluse, seules des statistiques agrégées sortent)
```

- **Frontend** : un seul fichier HTML/CSS/JS, sans build ni dépendance. Thème clair/sombre automatique.
- **Backend (optionnel)** : FastAPI + httpx. Il garde le jeton GitHub côté serveur et ne renvoie que des chiffres agrégés, jamais de noms de dépôts privés.

## Démarrage rapide

### Version simple (sans backend)

```powershell
python -m http.server 5500
```

Ouvre `http://localhost:5500/`. Le widget lit l'activité **publique** du compte défini dans `CONFIG.user` (en haut du script de `index.html`). Un champ permet d'essayer n'importe quel nom d'utilisateur GitHub, et un **mode démo** simule plusieurs profils.

### Version complète (avec jeton GitHub)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # puis renseigne GITHUB_TOKEN dans .env
uvicorn main:app --reload --port 8000
```

Dans un second terminal, à la racine du projet : `python -m http.server 5500`. En `localhost`, le widget utilise automatiquement le backend sur le port 8000.

Vérifications : `http://localhost:8000/health` doit renvoyer `"token_configured": true`, et `http://localhost:8000/api/stats` un JSON de statistiques.

## Configuration

Variables du fichier `backend/.env` :

| Variable | Rôle |
|---|---|
| `GITHUB_TOKEN` | Jeton GitHub *fine-grained* (lecture seule) |
| `GITHUB_USER` | Compte analysé |
| `TIMEZONE` | Fuseau horaire pour les heures de commit (défaut : `Africa/Niamey`) |
| `ALLOWED_ORIGINS` | Origines autorisées (CORS), séparées par des virgules |
| `CACHE_SECONDS` | Durée du cache côté serveur (défaut : 600) |

En production, renseigne `apiBase` dans `CONFIG` (`index.html`) avec l'URL du backend déployé, et `ALLOWED_ORIGINS` avec le domaine du site qui héberge le widget.

## Sécurité

- Le jeton ne doit **jamais** apparaître dans le HTML ni dans le dépôt : `.env` est ignoré par Git.
- Utilise un jeton *fine-grained* en lecture seule, avec une date d'expiration.
- Si un jeton fuite, révoque-le immédiatement dans les paramètres GitHub.
- Les données reçues (API ou cache du navigateur) sont converties en nombres avant tout affichage.

## Limites connues

- L'API d'événements GitHub ne remonte que les ~90 derniers jours (300 événements maximum) : l'XP reflète l'activité récente, pas toute une carrière.
- Les commits non poussés (`git push`) ne sont pas visibles.
- Le langage dominant vient du langage principal de chaque dépôt : un projet FastAPI + React compte pour un seul langage.
- Sans backend, la limite de 60 requêtes/h s'applique à chaque visiteur.

## Pistes d'évolution

- Calendrier de contributions sur un an via l'API GraphQL de GitHub.
- Plus de formes d'évolution et d'accessoires.
- Intégration d'un suivi du temps de code (WakaTime).

## Licence

MIT — voir [LICENSE](LICENSE).
