# Animations

Des mouvements réglés pour se resynchroniser exactement : au bout d'un cycle,
chaque figure retrouve sa position de départ. Aucune bibliothèque, tout est
calculé image par image sur un `<canvas>`.

En ligne : <https://sebistarrr.github.io/balle/>

| | Animation | Dossier |
|---|---|---|
| 01 | Vagues de pendule | [`1-vagues-de-pendule/`](1-vagues-de-pendule/) |
| 02 | Vagues de pendule, intensifié | [`2-vagues-de-pendule-intense/`](2-vagues-de-pendule-intense/) |
| 03 | Billard en boucle | [`3-billard-en-boucle/`](3-billard-en-boucle/) |

`index.html` à la racine est la page d'accueil : une vignette animée par
animation, qui sert de menu.

## Organisation

**Chaque animation est un dossier autonome**, avec son propre `index.html`
contenant tout son HTML, son CSS et son JavaScript. Rien n'est mis en commun :
modifier ou refondre une animation ne peut pas altérer les autres. Ajouter une
animation = créer un dossier `N-nom/` et ajouter une carte sur la page
d'accueil.

## Les trois animations

**01 — Vagues de pendule.** Seize pendules ; le *k*-ième effectue *30 − k*
oscillations par cycle de 96 s. La version d'origine, sobre. Le script
[Manim](https://www.manim.community/) qui produit la vidéo verticale
l'accompagne : [`pendulum_wave.py`](1-vagues-de-pendule/pendulum_wave.py).

**02 — Vagues de pendule, intensifié.** Mêmes constantes, même géométrie que la
01, jouée deux fois plus vite : traînées lumineuses, ondes de choc et gerbes de
particules à chaque contact, traits obliques en dégradé qui s'avivent à
l'impact. Vitesse réglable de 0,5× à 4×.

**03 — Billard en boucle.** Douze balles dans un carré. Sans frottement, chaque
axe suit une onde triangulaire ; en choisissant un nombre **entier**
d'allers-retours par axe et par cycle, la trajectoire se referme — une figure
de Lissajous polygonale, que les traînées dessinent peu à peu. Les balles se
traversent : c'est la condition pour que la boucle reste exacte. Le bouton
« trajectoires » révèle les courbes complètes.

Les trois ont un son facultatif : une note par impact, pentatonique mineure,
grave pour les éléments lents.

## Rendre la vidéo de la 01

```sh
pip install manim numpy
manim -r 1080,1920 --fps 60 1-vagues-de-pendule/pendulum_wave.py PendulumWave
```

Les réglages sont en tête du script : `DUREE` (48 s = demi-cycle, 96 s = boucle
parfaite), `FORME` (`"triangle"` comme la vidéo d'origine, ou `"sinus"` pour un
mouvement physiquement correct) et `AVEC_SON`.

## Voir en local

```sh
python3 -m http.server 8000   # puis http://localhost:8000
```

## Déploiement

`.github/workflows/pages.yml` publie la racine du dépôt sur GitHub Pages à
chaque push. Le réglage **Settings → Pages → Source → GitHub Actions** a déjà
été fait ; il n'y a plus rien à faire à la main.
