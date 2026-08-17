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
| 05 | Plus grosse à chaque rebond | [`5-plus-grosse-a-chaque-rebond/`](5-plus-grosse-a-chaque-rebond/) | `growing_bounce.py` |
| 06 | Rayons de rebond | [`6-rayons-de-rebond/`](6-rayons-de-rebond/) | `bounce_rays.py` |
| 07 | Résonance *(film)* | [`7-resonance/`](7-resonance/) | `resonance.py` |

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

## Les animations

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

**05 — Plus grosse à chaque rebond.** Reproduction d'une animation existante.
Une balle tombe dans un récipient en U — deux parois verticales fermées en bas
par un demi-cercle, ouvert en haut — et gagne un cran de rayon chaque fois
qu'elle retombe sur le fond, jusqu'à occuper toute la largeur en 54 s. Sa
trajectoire reste inscrite, et la teinte de l'ensemble tourne en continu.

Géométrie, gravité et croissance sont relevées image par image sur la vidéo
d'origine : récipient de 550 px de large, gravité 6500 px/s², sommet de la
course à 500 px. La courbe du rayon suit celle du modèle à 14 px près en
moyenne (sur 275), et la teinte fait 10 tours comme l'original.

Un billard sous gravité est chaotique. Deux précautions en découlent : le pas
de temps est **fixe** (sinon la partie dépendrait de la cadence d'affichage), et
les distances passent par `sqrt(dx*dx+dy*dy)` plutôt que par `hypot`, dont
l'arrondi n'est pas spécifié et diffère entre JavaScript et Python. À ce prix,
la page et le script Manim jouent exactement la même partie : 447 chocs, 53,75 s.

**06 — Rayons de rebond.** Même mécanique et mêmes constantes que la 05 — au
choc près, c'est la même partie — mais l'autre tracé, celui du modèle. Ce n'est
pas la trajectoire qui est dessinée : chaque choc laisse un point fixe sur la
paroi, et à chaque image on relie le centre de la balle à tous ces points.
L'éventail balaie l'espace à mesure qu'elle se déplace, et les traits sont
rigoureusement droits. C'est ce tracé-là, et non la trajectoire, qui donne
l'aspect en rayons de l'animation d'origine.

**07 — Résonance.** Celle-ci n'est pas une page interactive mais un **film de
10 s au format vertical**, rendu par Manim et destiné à être publié tel quel.
Sur un cercle de 240 points, on relie le point *k* au point *m·k* ; le
multiplicateur monte de 2 à 15 par paliers rythmés, traversant la cardioïde
(m = 2), la néphroïde (m = 3), puis des rosaces de plus en plus fines jusqu'à
la dentelle de m = 15. Une accroche en haut du cadre annonce le sujet.

Trois temps : une détonation qui déploie le cercle, treize paliers scandés par
des ondes de choc, un effondrement vers le centre. Faute de flou dans Manim,
la lueur est obtenue en superposant le même tracé en trois épaisseurs, aux
teintes légèrement décalées.

Tout boucle exactement : la teinte fait deux tours entiers du spectre, les
poussières de fond dérivent sur des périodes entières, et la dernière image est
au pixel près la première. La bande son est synthétisée par le script — coup
grave et note montante à chaque palier, montée de bruit sur la fin.

Toutes ont un son facultatif : une note par impact, pentatonique mineure, grave
pour les éléments lents ou gros.

## Télécharger les vidéos

Chaque dossier contient `shorts.mp4` : l'animation rendue en **1080×1920, 60 fps,
H.264 + AAC**, prête à publier sur YouTube Shorts, TikTok ou Reels. Le bouton
« ↓ mp4 1080×1920 » de chaque page y renvoie.

| | Animation | Durée | Poids |
|---|---|---|---|
| 01 | Vagues de pendule | 48 s | 18 Mo |
| 02 | Vagues de pendule, intensifié | 24 s | 16 Mo |
| 03 | Billard en boucle | 24 s | 8,6 Mo |
| 04 | La balle qui grossit | 24 s | 2,7 Mo |
| 05 | Plus grosse à chaque rebond | 56 s | 15 Mo |
| 06 | Rayons de rebond | 56 s | 31 Mo |
| 07 | Résonance | 10 s | 20 Mo |

Les animations 03 et 04 sont carrées, les 05 et 06 en 720:1244 : elles sont
mises à l'échelle sans déformation puis complétées en noir jusqu'au cadre 9:16.
Le fond étant noir, le raccord ne se voit pas.

Pour les regénérer après avoir modifié une animation :

```sh
./outils/vers-shorts.sh
```

Le script part des rendus Manim présents dans `media/` (voir ci-dessous), retient
la plus haute définition disponible, et coupe la traîne d'image figée que Manim
ajoute pour aligner la vidéo sur la piste sonore.

## Rendre les vidéos

```sh
pip install manim numpy

manim -r 1080,1920 --fps 60 1-vagues-de-pendule/pendulum_wave.py PendulumWave
manim -r 1080,1920 --fps 60 2-vagues-de-pendule-intense/pendulum_wave_intense.py PendulumWaveIntense
manim -r 1080,1080 --fps 60 3-billard-en-boucle/billiard_loop.py BilliardLoop
manim -r 1080,1080 --fps 60 4-balle-qui-grossit/growing_ball.py GrowingBall
manim -r 720,1244  --fps 60 5-plus-grosse-a-chaque-rebond/growing_bounce.py GrowingBounce
manim -r 720,1244  --fps 60 6-rayons-de-rebond/bounce_rays.py BounceRays
manim -r 1080,1920 --fps 60 7-resonance/resonance.py Resonance
```

Garder le format indiqué : 9:16 pour les deux premières, carré pour les 03 et
04, 720:1244 pour les 05 et 06, 9:16 pour la 07. Les réglages sont en tête de chaque script — durée, vitesse, `AVEC_SON`
pour la bande son, et pour la 01 `FORME` (`"triangle"` comme la vidéo d'origine,
ou `"sinus"` pour un mouvement physiquement correct).

Aucun de ces scripts n'a besoin de LaTeX : les seuls textes affichés (le
compteur de la 04, les légendes des 05 à 07) passent par Pango.

## Voir en local

```sh
python3 -m http.server 8000   # puis http://localhost:8000
```

## Déploiement

`.github/workflows/pages.yml` publie la racine du dépôt sur GitHub Pages à
chaque push. Le réglage **Settings → Pages → Source → GitHub Actions** a déjà
été fait ; il n'y a plus rien à faire à la main.
