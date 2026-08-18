# Animations

Deux familles : des figures réglées pour se refermer exactement, et des duels
dont on ne connaît l'issue qu'à la fin. Aucune bibliothèque, tout est calculé
image par image sur un `<canvas>`.

En ligne : <https://sebistarrr.github.io/balle/>

| | Animation | Dossier | Script Manim |
|---|---|---|---|
| 01 | Vagues de pendule | [`1-vagues-de-pendule-intense/`](1-vagues-de-pendule-intense/) | `pendulum_wave_intense.py` |
| 02 | Billard en boucle | [`2-billard-en-boucle/`](2-billard-en-boucle/) | `billiard_loop.py` |
| 03 | La balle qui grossit | [`3-balle-qui-grossit/`](3-balle-qui-grossit/) | `growing_ball.py` |
| 04 | Rayons de rebond | [`4-rayons-de-rebond/`](4-rayons-de-rebond/) | `bounce_rays.py` |
| 05 | La balle et les pointes | [`5-balle-et-pointes/`](5-balle-et-pointes/) | `balle_et_pointes.py` |

Et dix **duels**, où deux concurrentes au moins s'affrontent et où l'on ne
connaît l'issue qu'à la fin :

| | Duel | Dossier | Script Manim |
|---|---|---|---|
| 06 | Cinq vies | [`6-cinq-vies/`](6-cinq-vies/) | `cinq_vies.py` |
| 07 | Course en spirale | [`7-course-en-spirale/`](7-course-en-spirale/) | `course_spirale.py` |
| 08 | Le sol qui s'effrite | [`8-sol-qui-s-effrite/`](8-sol-qui-s-effrite/) | `sol_effrite.py` |
| 09 | Le grand plongeon | [`9-grand-plongeon/`](9-grand-plongeon/) | `grand_plongeon.py` |
| 10 | Guerre de territoire | [`10-guerre-de-territoire/`](10-guerre-de-territoire/) | `guerre_territoire.py` |
| 11 | Les pointes qui poussent | [`11-pointes-qui-poussent/`](11-pointes-qui-poussent/) | `pointes_poussent.py` |
| 12 | Sumo | [`12-sumo/`](12-sumo/) | `sumo.py` |
| 13 | Les portes | [`13-les-portes/`](13-les-portes/) | `les_portes.py` |
| 14 | Le dernier debout | [`14-le-dernier-debout/`](14-le-dernier-debout/) | `dernier_debout.py` |
| 15 | Le mur qui pousse | [`15-le-mur-qui-pousse/`](15-le-mur-qui-pousse/) | `mur_qui_pousse.py` |

Et deux **courses à cinq**, sur des parcours d'obstacles plus longs que
l'écran :

| | Animation | Dossier | Script Manim |
|---|---|---|---|
| 17 | Le parcours | [`17-le-parcours/`](17-le-parcours/) | `parcours.py` |
| 18 | Les deux épreuves | [`18-les-deux-epreuves/`](18-les-deux-epreuves/) | `deux_epreuves.py` |

Et une **évasion**, seule de son espèce — c'est aussi la seule dont la vidéo
n'est pas rendue par Manim, pour une raison mesurée plus bas :

| | Animation | Dossier | Script |
|---|---|---|---|
| 16 | La prison | [`16-la-prison/`](16-la-prison/) | `prison.py` *(Cairo)* |

`index.html` à la racine est la page d'accueil : la liste des titres, qui sert
de menu.

## Organisation

**Chaque animation est un dossier autonome**, avec son propre `index.html`
contenant tout son HTML, son CSS et son JavaScript, plus le script Manim qui en
produit la version vidéo. Rien n'est mis en commun : modifier ou refondre une
animation ne peut pas altérer les autres. Ajouter une animation = créer un
dossier `N-nom/` et ajouter une ligne sur la page d'accueil.

La page web et le script d'une même animation partagent les mêmes constantes,
converties d'un repère à l'autre. La page est l'aperçu ; le script est la
référence.

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

## Les duels

Même règle pour les dix : au moins deux concurrentes, une seule à l'arrivée, et
l'issue doit rester indécise le plus longtemps possible. Trois principes s'en
déduisent, et ils ont dicté à peu près tous les réglages.

1. **L'enjeu est lisible dès la première image.** Une accroche en haut pose la
   question, et un tableau de bord donne l'état de chaque concurrente — vies,
   avance, terrain, marge. Sans lui il n'y a rien à deviner, donc rien à
   regarder.
2. **L'écart se voit à tout instant**, et il est fait de la même matière que le
   jeu : la jauge de la 15 *est* la position du mur, les pastilles de la 14
   *sont* les tailles réelles des balles.
3. **Ça s'emballe.** Chaque duel a une escalade qui garantit une fin — pointes
   qui s'élargissent, gravité qui monte, marée qui ronge le camp en retard.

Un mot sur la méthode : chaque duel a été passé au banc d'essai avant d'être
gardé — trente parties simulées à toute vitesse, sans affichage, pour vérifier
deux choses. Que les deux camps gagnent à peu près autant, et que la durée
tombe dans la bonne fourchette. Cinq des dix ont dû être repensés à cause de ce
banc, et c'est ce qui suit.

**06 — Cinq vies.** Deux balles, six pointes tournant en sens contraires, cinq
vies chacune. Les pointes s'élargissent d'un cran toutes les six secondes.

Le départ est **tiré au sort**. Avec des positions fixes, tout ce qui précède la
première perte de vie est déterminé d'avance : c'est toujours la même balle qui
encaisse en premier, et elle court après son retard tout le reste du duel —
mesuré, cinq victoires sur cinq pour la même couleur. Après correction :
19 – 21 sur quarante duels, durée médiane 23 s.

**07 — Course en spirale.** La gravité est dirigée **vers le centre**, comme dans
un entonnoir à pièces. Sous une gravité verticale, un toboggan en spirale monte
autant qu'il descend et la balle oscille au fond du premier creux venu.

Deux pièges y sont tombés l'un après l'autre. D'abord la réaction des parois,
prise **radialement** : à 5° près ce n'est pas la normale à la spirale, et
l'erreur annule à chaque pas la composante par laquelle la balle glisse vers
l'intérieur — c'est-à-dire exactement le travail moteur de la gravité. Mesuré :
250 px/s au départ, 3 px/s après vingt secondes, aucune arrivée sur trente
essais. Ensuite le **couloir partagé** : trop étroit pour doubler, celle qui part
devant gagne les trente courses. D'où deux couloirs entrelacés, comme les deux
départs d'une vis à double filet — la même piste à un demi-tour près, donc de
même longueur exactement. 14 – 16 sur trente, 10 à 12 s.

**08 — Le sol qui s'effrite.** Seize dalles, trois coups chacune, et le vide en
dessous. Le rebond sur une dalle est **parfaitement élastique** : la balle
remonte toujours à la même hauteur, la cadence des coups reste régulière, et le
duel ne s'éteint pas de lui-même. Ce qui le termine, c'est le sol. Le tableau du
haut ne compte pas les dalles restantes mais l'état de celle qu'a chaque balle
*sous les pieds* : c'est là qu'est le danger. 17 – 13 sur trente, médiane 19 s.

**09 — Le grand plongeon.** Champ de clous en quinconce, première au fond.
Chaque ligne est **symétrique par rapport à l'axe** du puits : neuf clous sur les
lignes paires, huit sur les impaires. Décaler simplement d'un demi-pas en
gardant neuf clous fait sortir le dernier du cadre, la ligne penche à gauche, et
le puits favorise un côté — mesuré, 21 victoires sur 30 pour la balle de droite.
Gravité faible et clous très élastiques, sinon la descente se règle en trois
secondes. 19 – 21 sur quarante, 6 à 15 s.

**10 — Guerre de territoire.** Chaque balle repeint le camp adverse, case par
case. Trois corrections, chacune tirée d'une mesure :

- Les balles ne changeaient que le **signe** de leurs composantes : leur
  direction restait coincée sur quatre valeurs, elles parcouraient un damier
  fixe, et les dernières cases d'un coin n'étaient jamais atteintes. D'où une
  petite déviation tirée au sort à chaque case prise.
- Et aussi **sur les murs** : une balle rentrée dans son propre camp n'y trouve
  plus rien à conquérir, donc plus rien qui la dévie, et repart sur un circuit
  fermé. Les parties se figeaient à 276 cases contre 204.
- Même avec cela, la partie ne se décide jamais : les deux camps s'équilibrent
  autour de 50 % et y restent — aucune partie tranchée en sept minutes de
  simulation. D'où la **marée** : passé douze secondes, le camp en retard perd du
  terrain tout seul, de plus en plus vite. Un équilibre sans fin devient un
  compte à rebours. 18 – 12 sur trente, 15 à 20 s.

**11 — Les pointes qui poussent.** Sept pointes qui s'allongent vers le centre,
trois vies chacune. Sept pointes de 3,2° couvrent 12 % du bord ; à dix-huit
pointes de 5,2°, elles en couvraient **52 %**, et la balle mourait au premier ou
au deuxième rebond — les trente duels réglés en moins de deux secondes. La
couronne tourne pendant qu'elle pousse, ce qui déplace les intervalles sûrs.
16 – 14 sur trente, médiane 11 s.

**12 — Sumo.** Une plateforme, pas de mur, une cuvette harmonique qui ramène les
balles vers le centre. Deux corrections :

- Les deux balles étaient lancées **dans le même sens** ; diamétralement
  opposées, la symétrie centrale les maintenait éternellement aux antipodes
  l'une de l'autre. Aucun choc n'avait lieu de tout le duel, et c'est l'anneau
  qui tranchait à heure fixe — trente duels réglés entre 34 et 41 secondes.
  Elles tournent maintenant en sens contraires et se croisent deux fois par tour.
- La restitution des chocs est **supérieure à 1** : chaque contact ajoute de
  l'élan, comme deux lutteurs qui se poussent. À restitution 1 l'énergie totale
  ne bouge pas, les orbites restent sages, et rien n'éjecte jamais personne.
  15 – 9 sur vingt-quatre, 4 à 18 s.

**13 — Les portes.** Deux puits, des portes qui montent, chacune donne ou retire
une vie. Ce ne sont pas les balles qui tombent, c'est le décor qui monte : elles
restent à hauteur fixe, ce qui tient le regard au même endroit et permet de
garnir le haut du puits sans jamais bouger la caméra. Chaque puits a son propre
chapelet de portes — avec le même, les deux balles subiraient exactement le même
sort. 15 – 15 sur trente, médiane 23 s.

**14 — Le dernier debout.** Huit balles, et à chaque contact la plus grosse
arrache un morceau de la plus petite. À taille égale un choc ne transfère rien :
c'est ce qui rend les premières secondes indécises, avant que les écarts ne
s'amplifient d'eux-mêmes. Une part du transfert se perd au passage, sinon les
tailles s'envolent. Huit jauges seraient illisibles : la rangée du haut montre
les huit **tailles réelles**, et c'est le classement en direct. Les huit balles
gagnent au moins une fois sur vingt-quatre parties, médiane 24 s.

**15 — Le mur qui pousse.** Deux chambres, un mur mobile, et chaque coup le
pousse vers l'adversaire. C'est le duel qui a demandé le plus de tâtonnements.

Sans lien entre la poussée et la largeur, il ne finit jamais : la balle enfermée
dans la chambre étroite revient plus souvent au mur, puisqu'elle a moins de
chemin à faire, et rend exactement les coups qu'elle prend. Médiane mesurée :
quatre minutes. Une poussée **proportionnelle** à la largeur ne change rien non
plus — la fréquence des coups variant comme l'inverse de la largeur, le produit
est constant et les deux camps se compensent toujours. Il faut un exposant
supérieur à un : c'est le **cube** de la largeur qui est retenu, et un étau qui
se referme après seize secondes pour les parties encore serrées. 13 – 17 sur
trente, médiane 26 s.

## Les courses

**17 — Le parcours.** Reprise de la 09, mais à cinq balles et sur un vrai
parcours : **sept mille six cents pixels**, huit fois la hauteur de l'écran, que
la caméra suit en restant accrochée à la tête de course. Six sections
s'enchaînent — champ de clous, trois barres tournantes, entonnoir, chicane de
plans inclinés, moulins, ligne droite finale hérissée de clous serrés. La
première en bas gagne ; le film s'arrête dès que le podium est complet, regarder
les deux dernières finir n'apprenant plus rien.

**Un obstacle, une primitive.** Tout est une capsule — un segment doté d'une
épaisseur — ou un disque. Clous, parois inclinées, entonnoir, barres et pales de
moulin passent donc par le même test de contact, ce qui permet de varier le
parcours sans multiplier les cas.

**Les rotors ajoutent une chose, et c'est la plus importante** : au point de
contact, la pale a une vitesse propre, ω ∧ r. On rebondit sur cette vitesse-là
et non sur zéro. Sans cela une pale balaie la balle sans jamais la propulser —
et c'est justement là que les places se prennent et se perdent, une pale prise à
contretemps renvoyant la balle vers l'amont.

Deux réglages tirés des captures de contrôle :

- **Le monde est découpé sous le tableau de bord.** Sans découpage, une pale de
  moulin ou une balle distancée vient se dessiner par-dessus le classement et le
  rend illisible. Manim n'ayant pas de découpage, le film pose un bandeau opaque
  au même endroit.
- **L'ordre des couloirs de départ est tiré au sort.** Sur un parcours fixe la
  position de départ compte, et il ne faut pas qu'elle avantage toujours la même
  couleur. Mesuré sur vingt-quatre courses : les cinq balles gagnent entre trois
  et sept fois chacune, durée médiane 36 s.

Le tableau du haut n'est pas une liste de jauges mais **le classement lui-même** :
les lignes s'y échangent en direct, et il suffit de regarder l'ordre.

**18 — Les deux épreuves.** Même principe, mais réglé pour une arrivée serrée.
Le problème est là dès l'énoncé : **un parcours ordinaire étale le peloton**.
Chaque obstacle ajoute du hasard, les écarts s'additionnent, et à la fin la
première a deux écrans d'avance. Pour une course serrée il faut des obstacles
qui *rassemblent* — donc qui **font attendre les premiers arrivés**. Il y en a
deux, et le second donne directement sur la ligne droite finale.

**La herse** barre toute la largeur : une seule fenêtre, qui va et vient. Les
battants descendent vers cette fenêtre, et cette pente n'est pas décorative :
sur une barre horizontale une balle se pose et n'en repart plus — rien ne la
déséquilibre. Pire, l'entraînement latéral de la barre la déplace *avec* la
fenêtre, si bien qu'elle ne la rencontre jamais. Mesuré sur douze courses avant
correction : cinquante-huit blocages sur la herse, contre une poignée partout
ailleurs. Avec la pente, une balle posée roule vers l'ouverture et finit par
tomber.

**Le sas** est un entonnoir fermé par une trappe. Première version, une trappe à
cycle fixe — 3,6 s, ouverte 0,85 s. Elle ne rassemble rien : elle **découpe le
temps en tranches**. Les instants de passage mesurés se rangent sur la grille
17,9 / 21,1 / 24,7 / 28,3, et deux balles séparées d'une seconde repartent
souvent à une tranche entière d'écart. L'écart au sas valait 3,5 s — exactement
la période. La trappe **attend donc le peloton au lieu de compter** : elle
s'ouvre dès que quatre balles patientent dessus, ou au bout de neuf secondes si
elles ne viennent pas. Écart au sas après correction : **0,3 s**. Une seule
ouverture par course, cinq secondes d'attente en médiane — et c'est le meilleur
moment du film, tout le monde entassé derrière une trappe qui verdit.

**Toute fente plus étroite qu'une balle est un piège.** C'est la troisième leçon,
et la plus coûteuse : une course sur vingt-quatre durait **833 secondes**. Les
positions d'arrêt relevées étaient toujours les mêmes — x = 986, soit la paroi
moins un rayon, au contact du dernier clou de la rangée. Entre ce clou et la
paroi il restait 39 px pour une balle qui en fait 48 : elle s'y coinçait, à
l'arrêt, définitivement. Les rangées se construisent donc sous contrainte — jeu
minimal de trois rayons partout, et les clous des rangées paires plantés *sur*
les parois pour qu'il n'y subsiste aucune fente. Un garde-fou secoue en dernier
recours une balle qui n'avance plus, avec plus de patience devant la herse et le
sas où l'attente fait partie du jeu.

Mesuré sur quarante courses après ces trois corrections : durées 27 à 45 s,
médiane 31 s, les cinq balles gagnent entre 5 et 13 fois, et **l'écart entre la
première et la deuxième est inférieur à une seconde une fois sur deux**. Le
chiffre affiché sous le classement est l'écart au sein du trio de tête — pas des
cinq, car la course s'arrête à la troisième arrivée et une traînarde à
mi-parcours ne dit rien de ce qui se joue devant.

## La prison, et le choix de la bibliothèque

**16 — La prison.** Une balle au centre, quarante murs concentriques autour
d'elle, aucune porte. Chaque choc pulvérise le morceau de mur touché ; les
débris tombent et s'entassent en bas ; le compteur du milieu dit combien de
briques tiennent encore. Reproduction d'une vidéo existante, sur laquelle le
pas radial des anneaux a été mesuré — 5,8 px dans un cadre de 576, soit 10,9 px
ramené au nôtre — et le compte de départ relevé : 1 773 briques, contre 1 759
ici.

Un anneau de rayon *r* est découpé en briques d'environ soixante-dix pixels : les
anneaux extérieurs en comptent donc davantage, et les briques gardent la même
taille apparente d'un bout à l'autre du dessin.

Trois corrections, chacune tirée d'une mesure :

- **La balle ne part pas du centre exact.** De là, elle n'a aucun moment
  angulaire — et le rebond sur un anneau, dont la normale est radiale, le
  conserve. Elle fait l'aller-retour dans un couloir pour l'éternité : mesuré,
  5 à 10 briques abattues par anneau, les mêmes tout du long, et 1 497 briques
  encore debout sur 1 759 au bout de 85 secondes.
- **Le rebond dévie au hasard.** Même décalée du départ, la balle garde son
  moment angulaire d'un rebond à l'autre : elle reste prisonnière d'une couronne
  étroite, n'effleure les murs qu'à ses points de rebroussement, et n'en abat
  que 370. Casser cette conservation, c'est lui rendre tout le disque.
- **Le contact se teste sur toute la largeur de la balle**, et non sur la seule
  brique qui est sous son centre. Sinon une brique abattue suffit à la laisser
  passer quelle que soit sa taille : elle perce un tunnel radial et sort en
  n'ayant rien détruit.

Le jeu entre deux briques vaut trois pixels, donc un angle qui décroît avec le
rayon. Un jeu angulaire constant paraît anodin et ne l'est pas : sur les anneaux
extérieurs, où le pas angulaire est petit, l'arc restant devient négatif, ses
extrémités s'inversent, et Canvas comme Cairo dessinent alors presque le tour
complet. Les anneaux du bord semblaient intacts quel que soit le nombre de
briques abattues.

### Manim ou autre chose ?

C'est la seule animation du dépôt dont la vidéo n'est pas rendue par Manim, et
le choix a été tranché par une mesure. Sur exactement ce contenu — deux mille
arcs et deux mille grains en 1080 × 1920 :

| | Par seconde de film | Pour 30 s |
|---|---|---|
| Manim | 33 s | ~16 min |
| **Cairo** | **1,4 s** | **~42 s** |

Manim est fait pour des *scènes* : des objets nommés, peu nombreux, qu'on anime.
Il reconstruit ses objets vectoriels à chaque image, ce qui est parfait pour une
démonstration et ruineux pour deux mille éléments qui changent tous les seize
millisecondes. Cairo est un moteur de rasterisation : on lui donne des chemins,
il remplit des pixels, et rien ne survit d'une image à l'autre — ce qui tombe
bien, puisque tout change.

`prison.py` simule et dessine dans la même passe, et envoie les images brutes
dans ffmpeg par un tube, sans écrire des milliers de PNG sur le disque. Le film
de 39 s se rend en 91 secondes.

**La règle qui s'en dégage** : Manim tant qu'on met en scène des objets qu'on
peut nommer — c'est le cas des quinze autres —, Cairo dès qu'on peint des
milliers d'éléments par image.

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
| 06 | Cinq vies | 24 s | 2,2 Mo |
| 07 | Course en spirale | 14 s | 0,95 Mo |
| 08 | Le sol qui s'effrite | 23 s | 1,3 Mo |
| 09 | Le grand plongeon | 17 s | 1,1 Mo |
| 10 | Guerre de territoire | 21 s | 1,7 Mo |
| 11 | Les pointes qui poussent | 17 s | 1,5 Mo |
| 12 | Sumo | 21 s | 1,5 Mo |
| 13 | Les portes | 25 s | 2,9 Mo |
| 14 | Le dernier debout | 25 s | 2,1 Mo |
| 15 | Le mur qui pousse | 24 s | 1,3 Mo |
| 16 | La prison | 39 s | 7,4 Mo |
| 17 | Le parcours | 38 s | 4,7 Mo |
| 18 | Les deux épreuves | 33 s | 4,4 Mo |

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

manim -r 1080,1920 --fps 60 6-cinq-vies/cinq_vies.py CinqVies
manim -r 1080,1920 --fps 60 7-course-en-spirale/course_spirale.py CourseSpirale
manim -r 1080,1920 --fps 60 8-sol-qui-s-effrite/sol_effrite.py SolEffrite
manim -r 1080,1920 --fps 60 9-grand-plongeon/grand_plongeon.py GrandPlongeon
manim -r 1080,1920 --fps 60 10-guerre-de-territoire/guerre_territoire.py GuerreTerritoire
manim -r 1080,1920 --fps 60 11-pointes-qui-poussent/pointes_poussent.py PointesPoussent
manim -r 1080,1920 --fps 60 12-sumo/sumo.py Sumo
manim -r 1080,1920 --fps 60 13-les-portes/les_portes.py LesPortes
manim -r 1080,1920 --fps 60 14-le-dernier-debout/dernier_debout.py DernierDebout
manim -r 1080,1920 --fps 60 15-le-mur-qui-pousse/mur_qui_pousse.py MurQuiPousse
manim -r 1080,1920 --fps 60 17-le-parcours/parcours.py LeParcours
manim -r 1080,1920 --fps 60 18-les-deux-epreuves/deux_epreuves.py DeuxEpreuves
```

Les dix duels et les deux courses sont tous en 9:16. Chacun accepte
`--graines`, qui simule une série de tirages et affiche pour chacun la durée et
le vainqueur : de quoi choisir un autre duel que celui retenu, sans toucher au
reste.

Garder le format indiqué : carré pour les 02 et 03, 720:1244 pour la 04, 9:16
pour la 01, la 05, les dix duels et les deux courses. Les réglages sont en tête de chaque script — durée, vitesse,
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
