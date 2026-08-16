# Animations

Des mouvements réglés pour se resynchroniser exactement : au bout d'un cycle,
chaque figure retrouve sa position de départ. Aucune bibliothèque, tout est
calculé image par image sur un `<canvas>`.

En ligne : <https://sebistarrr.github.io/balle/>

| | Animation | Dossier | Script Manim |
|---|---|---|---|
| 01 | Vagues de pendule | [`1-vagues-de-pendule/`](1-vagues-de-pendule/) | `pendulum_wave.py` |
| 02 | Vagues de pendule, intensifié | [`2-vagues-de-pendule-intense/`](2-vagues-de-pendule-intense/) | `pendulum_wave_intense.py` |
| 03 | Billard en boucle | [`3-billard-en-boucle/`](3-billard-en-boucle/) | `billiard_loop.py` |
| 04 | La balle qui grossit | [`4-balle-qui-grossit/`](4-balle-qui-grossit/) | `growing_ball.py` |

`index.html` à la racine est la page d'accueil : la liste des titres, qui sert
de menu.

## Organisation

**Chaque animation est un dossier autonome**, avec son propre `index.html`
contenant tout son HTML, son CSS et son JavaScript, plus le script Manim qui en
produit la version vidéo. Rien n'est mis en commun : modifier ou refondre une
animation ne peut pas altérer les autres. Ajouter une animation = créer un
dossier `N-nom/` et ajouter une ligne sur la page d'accueil.

La page web et le script Manim d'une même animation partagent les mêmes
constantes, converties d'un repère à l'autre. La page est l'aperçu ; le script
Manim est la référence.

## Les trois animations

**01 — Vagues de pendule.** Seize pendules ; le *k*-ième effectue *30 − k*
oscillations par cycle de 96 s. La version d'origine, sobre.

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

**04 — La balle qui grossit.** Une balle rebondit sans frottement dans le
carré ; à chaque contact avec une paroi son rayon gagne un cran. L'espace laissé
à son centre se resserre d'autant, donc la cadence s'emballe toute seule : le
premier rebond arrive après 0,8 s, les derniers s'enchaînent en centièmes de
seconde. Au 45e elle est inscrite dans le carré, puis tout recommence à
l'identique.

Toutes ont un son facultatif : une note par impact, pentatonique mineure, grave
pour les éléments lents ou gros.

## Rendre les vidéos

```sh
pip install manim numpy

manim -r 1080,1920 --fps 60 1-vagues-de-pendule/pendulum_wave.py PendulumWave
manim -r 1080,1920 --fps 60 2-vagues-de-pendule-intense/pendulum_wave_intense.py PendulumWaveIntense
manim -r 1080,1080 --fps 60 3-billard-en-boucle/billiard_loop.py BilliardLoop
manim -r 1080,1080 --fps 60 4-balle-qui-grossit/growing_ball.py GrowingBall
```

Garder le format indiqué : 9:16 pour les deux premières, carré pour les deux
autres. Les réglages sont en tête de chaque script — durée, vitesse, `AVEC_SON`
pour la bande son, et pour la 01 `FORME` (`"triangle"` comme la vidéo d'origine,
ou `"sinus"` pour un mouvement physiquement correct).

Aucun de ces scripts n'a besoin de LaTeX : le seul texte affiché (le compteur de
la 04) passe par Pango.

## Voir en local

```sh
python3 -m http.server 8000   # puis http://localhost:8000
```

## Déploiement

`.github/workflows/pages.yml` publie la racine du dépôt sur GitHub Pages à
chaque push. Le réglage **Settings → Pages → Source → GitHub Actions** a déjà
été fait ; il n'y a plus rien à faire à la main.
