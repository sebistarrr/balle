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
| 08 | Comprendre les tables *(film)* | [`8-comprendre-les-tables/`](8-comprendre-les-tables/) | `explication.py` |
| 09 | Les tables expliquées, avec voix *(film)* | [`9-tables-expliquees/`](9-tables-expliquees/) | `explication.py` |
| 10 | La balle et les pointes | [`10-balle-et-pointes/`](10-balle-et-pointes/) | `balle_et_pointes.py` |

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

**08 — Comprendre les tables.** La même figure que la 07, mais expliquée depuis
le début, pour qui ne l'a jamais vue. Cinquante-deux secondes, en cinq temps :
dix points numérotés en cercle comme un cadran ; la table de 2 tracée une corde
à la fois avec le calcul écrit dessous ; le passage qui bloque tout le monde —
5 × 2 = 10, donc on retombe sur 0 ; la densification à 40, 120 puis 240 points,
où le cœur apparaît ; le défilé des tables, chacune avec ses *m − 1* pointes.

Le minutage est en tête du script : chaque étape a son instant de départ, et
texte, cordes et bande son s'y accrochent. C'est ce qui permet de régler le
rythme d'une explication sans reprendre le reste.

**09 — Les tables expliquées, avec voix.** Le même sujet que la 08, mais
commenté : une voix off porte l'explication, et c'est elle qui donne le tempo.
39 s au lieu de 52, sans temps mort — onze phrases courtes qui s'enchaînent.

Le script lit la **durée réelle** de chaque phrase enregistrée et cale les
étapes dessus : le tracé d'une corde par sous-phrase de « un donne deux, deux
donne quatre, trois donne six », l'arc qui fait le tour du cercle au moment
exact où la voix dit qu'il n'y a pas de dix, les trois densifications sur
« quarante, cent vingt, deux cent quarante ». Refaire une phrase ne dérègle
donc pas le reste du montage, et le dessin ne devance jamais le commentaire.

La voix est synthétisée par [piper](https://github.com/OHF-Voice/piper1-gpl)
(modèle `fr_FR-siwis-medium`) ; `outils/faire-la-voix.py` régénère les onze
phrases à l'identique. Les fichiers sont versionnés dans
`9-tables-expliquees/voix/` : 1,5 Mo, et sans eux le film ne se rend qu'en muet
— le minutage étant conservé par des durées de repli.

**10 — La balle et les pointes.** Partie d'une reproduction d'animation du genre
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
| 08 | Comprendre les tables | 52 s | 6,1 Mo |
| 09 | Les tables expliquées, avec voix | 39 s | 11,3 Mo |
| 10 | La balle et les pointes | 30 s | 7,6 Mo |

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
manim -r 1080,1920 --fps 60 8-comprendre-les-tables/explication.py Explication
manim -r 1080,1920 --fps 60 9-tables-expliquees/explication.py TablesExpliquees
manim -r 1080,1920 --fps 60 10-balle-et-pointes/balle_et_pointes.py BalleEtPointes
```

Garder le format indiqué : 9:16 pour les deux premières, carré pour les 03 et
04, 720:1244 pour les 05 et 06, 9:16 pour les 07 à 10. Les réglages sont en tête de chaque script — durée, vitesse, `AVEC_SON`
pour la bande son, et pour la 01 `FORME` (`"triangle"` comme la vidéo d'origine,
ou `"sinus"` pour un mouvement physiquement correct).

Aucun de ces scripts n'a besoin de LaTeX : les seuls textes affichés (le
compteur de la 04, les légendes et textes des 05 à 10) passent par Pango.

## Voir en local

```sh
python3 -m http.server 8000   # puis http://localhost:8000
```

## Déploiement

`.github/workflows/pages.yml` publie la racine du dépôt sur GitHub Pages à
chaque push. Le réglage **Settings → Pages → Source → GitHub Actions** a déjà
été fait ; il n'y a plus rien à faire à la main.
