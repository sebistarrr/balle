# Vague de pendules

Deux fichiers :

- `index.html` — aperçu animé (canvas), autonome, sans dépendance. Boutons pause et son.
- `pendulum_wave.py` — la référence : scène [Manim](https://www.manim.community/) qui produit la vidéo 1080×1920.

16 pendules ; le *k*-ième effectue *30 − k* oscillations par cycle de 96 s, donc la
figure se resynchronise exactement à chaque cycle.

## Voir l'aperçu

En ligne via GitHub Pages, ou localement :

```sh
python3 -m http.server 8000   # puis http://localhost:8000
```

(Ouvrir `index.html` par double-clic marche aussi ; le serveur évite juste
les restrictions `file://`.)

## Rendre la vidéo

```sh
pip install manim numpy
manim -r 1080,1920 --fps 60 pendulum_wave.py PendulumWave
```

Les réglages sont en tête de `pendulum_wave.py` : `DUREE` (48 s = demi-cycle,
96 s = boucle parfaite), `FORME` (`"triangle"` comme la vidéo d'origine, ou
`"sinus"` pour un mouvement physiquement correct) et `AVEC_SON`.

## Déploiement

`.github/workflows/pages.yml` publie la racine du dépôt sur GitHub Pages à
chaque push.

Une manipulation manuelle est nécessaire **une seule fois**, car créer le site
Pages demande un droit d'administration que le `GITHUB_TOKEN` du workflow n'a
pas : **Settings → Pages → Source → GitHub Actions**. Ensuite, relancer le
workflow (**Actions → Deploy to GitHub Pages → Run workflow**) ou pousser un
commit ; le site sort sur `https://sebistarrr.github.io/balle/`.
