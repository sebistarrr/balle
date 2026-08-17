# Animations

Des mouvements réglés pour se resynchroniser exactement : au bout d'un cycle,
chaque figure retrouve sa position de départ. Aucune bibliothèque, tout est
calculé image par image sur un `<canvas>`.

En ligne : <https://sebistarrr.github.io/balle/>

| | Animation | Dossier | Script Manim |
|---|---|---|---|
| 01 | Vagues de pendule | [`1-vagues-de-pendule-intense/`](1-vagues-de-pendule-intense/) | `pendulum_wave_intense.py` |
| 02 | Billard en boucle | [`2-billard-en-boucle/`](2-billard-en-boucle/) | `billiard_loop.py` |
| 03 | La balle qui grossit | [`3-balle-qui-grossit/`](3-balle-qui-grossit/) | `growing_ball.py` |
| 04 | Rayons de rebond | [`4-rayons-de-rebond/`](4-rayons-de-rebond/) | `bounce_rays.py` |
| 05 | La balle et les pointes | [`5-balle-et-pointes/`](5-balle-et-pointes/) | `balle_et_pointes.py` |

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
oscillations par cycle de 96 s. Les périodes étant dans un rapport entier, tous
se retrouvent alignés au bout d'un cycle et la figure repart à l'identique.
Traînées lumineuses, ondes de choc et gerbes de particules à chaque contact,
traits obliques en dégradé qui s'avivent à l'impact. Vitesse réglable de 0,5×
à 4×.

**02 — Billard en boucle.** Douze balles dans un carré. Sans frottement, chaque
axe suit une onde triangulaire ; en choisissant un nombre **entier**
d'allers-retours par axe et par cycle, la trajectoire se referme — une figure
de Lissajous polygonale, que les traînées dessinent peu à peu. Les balles se
traversent : c'est la condition pour que la boucle reste exacte. Le bouton
« trajectoires » révèle les courbes complètes.

**03 — La balle qui grossit.** Une balle rebondit sans frottement dans le
carré ; à chaque contact avec une paroi son rayon gagne un cran. L'espace laissé
à son centre se resserre d'autant, donc la cadence s'emballe toute seule : le
premier rebond arrive après 0,8 s, les derniers s'enchaînent en centièmes de
seconde. Au 45e elle est inscrite dans le carré, puis tout recommence à
l'identique.

**04 — Rayons de rebond.** Une balle tombe dans un récipient en U — deux parois
verticales fermées en bas par un demi-cercle, ouvert en haut — et gagne un cran
de rayon chaque fois qu'elle retombe sur le fond. Le sujet est le tracé : ce
n'est pas la trajectoire qui est dessinée, chaque choc laisse un point fixe sur
la paroi, et à chaque image on relie le centre de la balle à tous ces points.
L'éventail balaie l'espace à mesure qu'elle se déplace, et les traits sont
rigoureusement droits. C'est ce tracé-là, et non la trajectoire, qui donne
l'aspect en rayons de l'animation d'origine.

**05 — La balle et les pointes.** Partie d'une reproduction d'animation du genre
« ball simulator », puis emmenée ailleurs. Une balle file **en ligne droite**
dans un cercle — pas de gravité, elle atteint donc tout le bord. **Chaque rebond
joue la note suivante d'une mélodie et la fait grossir**, jusqu'à ce qu'elle
éclate en billes qui **gardent sa couleur**. Une nouvelle balle repart à la
taille de départ, dans une autre teinte. Trois pointes tournent sur le bord et
peuvent l'attraper avant.

Le décor vient de mesures sur la vidéo de référence, ramenées d'un cadre de
576 × 1024 au nôtre (facteur 1,875) : trois pointes espacées de **120°** tournant
à **−52 °/s** (un tour en 6,94 s), teinte du bord **égale à l'angle**, rebonds
élastiques à vitesse constante.

Ce qui fait la différence :

- **La croissance n'est pas qu'un effet.** En grossissant, la balle laisse moins
  de place : ses trajets raccourcissent et les rebonds se rapprochent. La
  musique accélère donc toute seule à mesure que l'éclatement approche. De 24 px
  à 112 px par pas de 11, cela fait **huit rebonds entre deux éclatements**.
  On grossit *avant* de repositionner la balle sur le bord : dans l'autre ordre
  elle mord encore le bord et déclenche un second rebond au pas suivant.
- **Les billes ne s'endorment jamais** : de vraies collisions entre elles,
  rangées dans une **grille**, sinon le test coûterait le carré du nombre. Sans
  gravité elles n'ont plus de fond où s'entasser et occupent tout le disque —
  d'où une restitution montée à 0,92 et un frottement quasi nul, faute de quoi
  tout s'immobiliserait au milieu.
- **La balle et les billes se bousculent.** Même échange qu'entre billes, mais
  avec un rapport de masse de **quarante** : la bille part, la balle n'est que
  déviée. Sa vitesse est ensuite ramenée à V₀, seule sa direction retient le
  choc. Sans ce rapport elle serait ballottée par le nuage, n'atteindrait plus
  le bord, et la musique s'arrêterait.
- **Le débordement est repris en fin de pas.** Une bille poussée par ses
  voisines ou par la balle peut franchir le bord : on la ramène dedans et on
  annule sa vitesse sortante. Mesuré, le dépassement maximal tombe à 1 × 10⁻¹³ px.

L'habillage suit la même idée : tout s'accroche à la **tension**, qui va de 0
juste après un éclatement à 1 juste avant le suivant. Halo qui enfle, anneau de
charge qui se referme autour de la balle, traînée, gerbe d'étincelles au rebond,
éclair blanc à l'éclatement. Le halo et la traînée débordent largement du cercle
— sur la page on découpe au disque, et comme Manim n'a pas de découpage, le film
pose par-dessus un **anneau noir** qui va du bord jusqu'au-delà du cadre, avant
de redessiner le bord dessus.

**La musique est écrite pour cette animation.** Celle de la vidéo de référence
est un morceau du commerce — la vidéo demande d'ailleurs aux spectateurs de le
reconnaître — et ne peut être ni extraite ni rediffusée. Le principe, lui, est
le même et fonctionne avec n'importe quelle musique.

Ce qui la fait sonner comme de la musique et non comme une gamme&nbsp;:

- **Une suite d'accords**, Am – F – C – G, deux fois, quatre notes de mélodie par
  accord. L'accord change donc tous les quatre rebonds, et c'est la physique qui
  décide *quand*. Les quatre premiers accords montent, les quatre suivants
  redescendent : sur trente secondes cela dessine une arche.
- **Trois couches** : la note du rebond, une basse sur la fondamentale, une
  nappe tenue sur la triade. Les deux dernières ne sonnent qu'au changement
  d'accord.
- **Un timbre de métal frappé** : quatre partiels dont les aigus s'éteignent plus
  vite que la fondamentale, le dernier inharmonique (× 4,17) pour le « ping ».
  Des partiels de même durée donneraient un orgue.
- **Une réverbération**, par convolution avec un bruit qui décroît sur deux
  secondes, différent pour chaque oreille. C'est le seul écart le plus net entre
  « un jouet » et « un instrument ».

Les trois niveaux sont réglés à la mesure et non à l'oreille : sur le mélange,
la bande 300 Hz – 1 kHz, celle de la mélodie, porte **59 %** de l'énergie, et
seuls **21 %** passent sous 300 Hz. Une basse plus forte noie la mélodie sur un
haut-parleur de téléphone, qui ne descend guère plus bas.

Le script Manim ne met que 55 billes par éclatement contre 110 sur la page :
Manim dessine du vectoriel. Pour que le rendu reste faisable, les billes y sont
groupées, chacune dessinée comme quatre cubiques — les sous-chemins se séparant
d'eux-mêmes entre deux disques. Le groupement se fait par **teinte exacte**, et
non plus par tranche de 60° : les billes d'un même éclatement partageant
précisément la couleur de la balle qui les a produites, une tranche large
fondrait deux éclatements voisins dans une seule couleur — exactement ce que
l'animation doit montrer.

Toutes ont un son facultatif : une note par impact, grave pour les éléments
lents ou gros. Les quatre premières jouent une gamme pentatonique mineure ; la
05 suit une suite d'accords, détaillée plus haut.

## Télécharger les vidéos

Chaque dossier contient `shorts.mp4` : l'animation rendue en **1080×1920, 60 fps,
H.264 + AAC**, prête à publier sur YouTube Shorts, TikTok ou Reels. Le bouton
« ↓ mp4 1080×1920 » de chaque page y renvoie.

| | Animation | Durée | Poids |
|---|---|---|---|
| 01 | Vagues de pendule | 24 s | 16 Mo |
| 02 | Billard en boucle | 24 s | 8,6 Mo |
| 03 | La balle qui grossit | 24 s | 2,7 Mo |
| 04 | Rayons de rebond | 56 s | 31 Mo |
| 05 | La balle et les pointes | 30 s | 8,2 Mo |

Les animations 02 et 03 sont carrées, la 04 en 720:1244 : elles sont mises à
l'échelle sans déformation puis complétées en noir jusqu'au cadre 9:16.
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

manim -r 1080,1920 --fps 60 1-vagues-de-pendule-intense/pendulum_wave_intense.py PendulumWaveIntense
manim -r 1080,1080 --fps 60 2-billard-en-boucle/billiard_loop.py BilliardLoop
manim -r 1080,1080 --fps 60 3-balle-qui-grossit/growing_ball.py GrowingBall
manim -r 720,1244  --fps 60 4-rayons-de-rebond/bounce_rays.py BounceRays
manim -r 1080,1920 --fps 60 5-balle-et-pointes/balle_et_pointes.py BalleEtPointes
```

Garder le format indiqué : carré pour les 02 et 03, 720:1244 pour la 04, 9:16
pour les 01 et 05. Les réglages sont en tête de chaque script — durée, vitesse,
`AVEC_SON` pour la bande son, et pour la 01 `FORME` (`"triangle"` comme la vidéo
d'origine, ou `"sinus"` pour un mouvement physiquement correct).

Aucun de ces scripts n'a besoin de LaTeX : les seuls textes affichés (les
compteurs des 03 et 05, les légendes de la 04) passent par Pango.

## Voir en local

```sh
python3 -m http.server 8000   # puis http://localhost:8000
```

## Déploiement

`.github/workflows/pages.yml` publie la racine du dépôt sur GitHub Pages à
chaque push. Le réglage **Settings → Pages → Source → GitHub Actions** a déjà
été fait ; il n'y a plus rien à faire à la main.
