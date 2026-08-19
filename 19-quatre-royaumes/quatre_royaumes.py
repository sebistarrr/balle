"""
Quatre royaumes — reproduction Manim du duel, format vertical.

Le plateau est coupé en quatre quarts égaux, un royaume par quart, une
balle par royaume. Toute case qui n'est pas à elle change de camp au contact et
la renvoie ailleurs : en avançant, chaque balle se creuse son propre couloir
dans le terrain d'en face.

À la fin de chaque manche, le plus petit royaume tombe. Ses cases deviennent
grises et sont reprises une à une en partant des bords — et rien n'empêche une
autre balle de venir se servir avant.

Repris de la guerre de territoire (10), à quatre camps. Deux règles héritées de
là-bas : une déviation tirée au sort à chaque case prise, sans quoi la direction
d'une balle reste coincée sur quatre valeurs et des coins entiers ne sont jamais
atteints ; et cette même déviation sur les murs, sans quoi une balle rentrée
dans son propre camp repart sur un circuit fermé qui ne revient jamais au
front.

Rendu :
    manim -r 1080,1920 --fps 60 quatre_royaumes.py QuatreRoyaumes

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python quatre_royaumes.py --graines` en essaie une série et affiche, pour chacune, la
durée et le vainqueur, de quoi choisir un duel serré.
"""

from manim import *
import colorsys
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#04060A"

W, H = 1080, 1920
ECHELLE = 9.0 / W           # un pixel vaut cela en unités de scène
FPS_ECH = 60                # un instantané par image de vidéo
APRES = 3.0                 # s de bandeau « vainqueur » après le duel
AVEC_SON = True


def vers_scene(x, y):
    return np.array([(x - W / 2) * ECHELLE, (H / 2 - y) * ECHELLE, 0.0])


def teinte(h, l=0.60, s=1.0):
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))

# --------------------------------------------------------------------------
#  Bande son. Écrite ici, rien d'emprunté.
#
#  Une cloche par choc, un souffle par coup dur, un accord montant à la
#  victoire, le tout passé dans une réverbération : la même note sèche sonne
#  comme un jouet, et dans une salle comme un instrument.
# --------------------------------------------------------------------------
def bande_son(evenements, duree, chemin, sr=44100, graine=3):
    """evenements : liste de (instant, genre, hauteur, pan, force).

    genre vaut "cloche" ou "souffle" ; hauteur est un demi-ton au-dessus de
    BASE pour les cloches, une fréquence de filtre pour les souffles.
    """
    import wave

    n = int((duree + 2.5) * sr)
    gauche, droite = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(graine)

    def poser(debut, onde, pan=0.0):
        i0 = max(0, int(debut * sr))
        fin = min(i0 + len(onde), n)
        if fin > i0:
            g = np.clip(0.5 * (1 - pan), 0, 1)
            gauche[i0:fin] += g * onde[: fin - i0]
            droite[i0:fin] += (1 - g) * onde[: fin - i0]

    def secondes(d):
        return np.arange(int(d * sr)) / sr

    def cloche(demi, force, base=196.0, duree_note=1.0):
        f = base * 2 ** (demi / 12)
        tt = secondes(duree_note)
        s = np.zeros_like(tt)
        #  Les harmoniques hautes s'éteignent plus vite que la fondamentale :
        #  c'est ce qui fait entendre un métal frappé plutôt qu'un orgue.
        for mult, amp, chute in ((1, 1.0, 3.0), (2, 0.34, 5.2), (3, 0.13, 7.6)):
            s += amp * np.exp(-tt * chute) * np.sin(TAU * f * mult * tt)
        return force * (1 - np.exp(-tt / 0.002)) * s

    def bruit(coupe, force, duree_note=0.45):
        tt = secondes(duree_note)
        s = rng.normal(0, 1, len(tt)) * (1 - tt / tt[-1]) ** 2.2
        #  Filtre à un pôle : passe-bas si la coupure est basse, et l'on prend
        #  le complément pour un passe-haut. Suffisant pour un souffle.
        a = np.exp(-TAU * coupe / sr)
        y = np.zeros_like(s)
        acc = 0.0
        for i in range(len(s)):
            acc = a * acc + (1 - a) * s[i]
            y[i] = acc
        return force * (y if coupe < 1200 else s - y)

    for instant, genre, hauteur, pan, force in evenements:
        if genre == "cloche":
            poser(instant, cloche(hauteur, force), pan)
        elif genre == "grave":
            poser(instant, cloche(hauteur, force, 98.0, 1.6), pan)
        elif genre == "aigu":
            poser(instant, cloche(hauteur, force, 392.0, 1.4), pan)
        else:
            poser(instant, bruit(hauteur, force), pan)

    def reverbe(sig, ir):
        taille = 1 << (len(sig) + len(ir) - 2).bit_length()
        return np.fft.irfft(np.fft.rfft(sig, taille) * np.fft.rfft(ir, taille),
                            taille)[: len(sig)]

    tt = secondes(1.6)
    lissage = np.ones(24) / 24
    for canal in (gauche, droite):
        ir = rng.normal(0, 1, len(tt)) * np.exp(-tt * 3.4)
        ir[: int(0.008 * sr)] *= np.linspace(0, 1, int(0.008 * sr))
        ir = np.convolve(ir, lissage, mode="same")
        canal += 0.35 * reverbe(canal, ir / np.abs(ir).sum() * 6.0)

    stereo = np.stack([np.tanh(gauche * 1.1), np.tanh(droite * 1.1)], axis=1)
    pcm = (stereo / max(1e-9, np.abs(stereo).max()) * 0.92 * 32767).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


def accord_victoire(instant, aigu=False):
    """Les quatre notes montantes de la fin."""
    return [(instant + i * 0.11, "aigu" if aigu else "cloche", d, 0.0, 0.26)
            for i, d in enumerate((0, 4, 7, 12))]

# --------------------------------------------------------------------------
#  Éléments communs à tous les duels : l'accroche du haut et le bandeau de fin.
# --------------------------------------------------------------------------
def accroche(texte):
    m = Text(texte, weight=SEMIBOLD, color="#EBF4F8")
    return m.scale_to_fit_height(0.30).move_to(vers_scene(W / 2, 96))


def bandeau_fin(nom, couleur_nom, detail, t, fin):
    """Renvoie (voile, bandeau) — le voile porte l'updater des deux."""
    voile = Rectangle(width=config.frame_width, height=config.frame_height,
                      stroke_width=0, fill_color="#04060A", fill_opacity=0)
    bloc = VGroup(
        Text("vainqueur", color="#C8D7DC").scale_to_fit_height(0.30),
        Text(nom, weight=BOLD, color=couleur_nom).scale_to_fit_height(0.82),
        Text(detail, color="#A0B4BE").scale_to_fit_height(0.26),
    ).arrange(DOWN, buff=0.30).move_to(vers_scene(W / 2, H / 2))
    bloc.set_opacity(0)

    def maj(_):
        v = float(np.clip((t.get_value() - fin) / 0.4, 0, 1))
        voile.set_fill(opacity=0.66 * v)
        for m in bloc:
            m.set_opacity(v)

    voile.add_updater(maj)
    return voile, bloc


def balle_mobject(h, rayon):
    return Circle(radius=rayon * ECHELLE, stroke_color="#FFFFFF",
                  stroke_width=2.5, stroke_opacity=0.5,
                  fill_color=teinte(h, 0.62), fill_opacity=1)


def halo_mobject(h, rayon, couches=((1.7, 0.14), (2.6, 0.07))):
    return VGroup(*[
        Circle(radius=rayon * f * ECHELLE, stroke_width=0,
               fill_color=teinte(h, 0.58), fill_opacity=o) for f, o in couches])

# --------------------------------------------------------------------------
#  Réglages, identiques à la page voisine
# --------------------------------------------------------------------------
X0, X1, Y0, Y1 = 40, 1040, 210, 1460
COLS, RANGS = 24, 30           # cases carrées : 1000/24 = 1250/30
LC, LR = (X1 - X0) / COLS, (Y1 - Y0) / RANGS
TOTAL = COLS * RANGS
R_BALLE = 20
V0 = 760.0
V_MONTE = 20.0
V_PLAFOND = 1700.0
#  La morsure : la case touchée tombe, et avec elle ses voisines ennemies. Sans
#  cet élargissement, un contact ne prend qu'une case et renvoie la balle
#  aussitôt — mesuré, les quatre camps restaient à 180 cases ± 5 pendant toute
#  une manche, et l'élimination du plus petit paraissait tirée au sort. La
#  morsure fait avancer le front pour de bon : on voit qui grignote qui.
MORSURE = 1                    # rangs de voisines emportées avec la case
#  Déviation tirée au sort à chaque case prise. Sans elle la balle ne fait que
#  changer le signe de ses composantes : sa direction reste coincée sur quatre
#  valeurs et des coins entiers ne sont jamais atteints. Leçon de la 10.
DEVIATION = 0.16
DT = 1 / 480

NEUTRE = 4                     # cases d'un royaume tombé, à prendre

#  Le lever de rideau. Rien ne bouge avant : on laisse le temps de choisir une
#  couleur, puis on décompte. Les pastilles et le décompte se partagent le même
#  temps — les quatre couleurs restent sous les yeux pendant que le compte
#  tourne, au lieu de disparaître au moment précis où il faudrait choisir.
PRE_CHOIX = 1.3
PRE_COMPTE = 3.2
DEPART = PRE_CHOIX + PRE_COMPTE

#  Les manches. À la fin de chacune, le plus petit royaume tombe. C'est ce qui
#  garantit une fin : quatre balles qui se mangent mutuellement du terrain
#  s'équilibrent et n'en bougent plus.
MANCHES = (10.5, 8.5, 7.0)
PARTAGE = 1.3                  # s pour dépecer un royaume tombé
SACRE = 1.6                    # s pour que le vainqueur recouvre le reste

NOMS = ("ROUGE", "JAUNE", "VERT", "BLEU")
TEINTES = (354.0, 44.0, 132.0, 205.0)
QUARTS = ((0, 0), (1, 0), (0, 1), (1, 1))
N = len(NOMS)

#  Graine 6, la meilleure partie des vingt essayées. BLEU tombe le premier à
#  23 % contre 28 au plus gros — cinq points séparent les quatre royaumes. À la
#  manche suivante, ROUGE et JAUNE sont exactement à égalité, 30 % chacun, et
#  c'est le tirage qui départage. La finale se joue à deux points : 51 contre 49
#  pour VERT, qui ne menait à aucune des deux premières chutes.
GRAINE = 6

#  La balle sonde quatre points — haut, bas, gauche, droite. Tester le centre
#  seul ferait traverser les cases en diagonale ; tester le cercle entier
#  coûterait cher pour rien.
SONDES = ((1, 0), (-1, 0), (0, 1), (0, -1))


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    terrain = np.empty(TOTAL, dtype=np.int8)
    for r in range(RANGS):
        for c in range(COLS):
            qx, qy = (0 if c < COLS / 2 else 1), (0 if r < RANGS / 2 else 1)
            terrain[r * COLS + c] = QUARTS.index((qx, qy))
    comptes = [TOTAL // N] * N + [0]
    vivant = [1] * N
    vivants = N

    balles = []
    for i, (qx, qy) in enumerate(QUARTS):
        #  Chaque balle au centre de son quart, lancée vers le milieu du
        #  plateau : c'est là qu'elle trouvera de l'ennemi.
        x = X0 + (X1 - X0) * (0.75 if qx else 0.25)
        y = Y0 + (Y1 - Y0) * (0.75 if qy else 0.25)
        a = np.arctan2((Y0 + Y1) / 2 - y, (X0 + X1) / 2 - x) + rng.uniform(-0.55, 0.55)
        balles.append({"i": i, "x": x, "y": y,
                       "vx": np.cos(a) * V0, "vy": np.sin(a) * V0})

    t = 0.0
    prochaine = DEPART + MANCHES[0]
    manche = 0
    a_repartir, dette_rep, taux_rep, sacre = [], 0.0, 0.0, 0
    tombes, vainqueur, fin = [], -1, None
    images, chocs = [], []
    changements = []
    prochain_cliche = 0.0

    def vitesse_de(i):
        return min(V_PLAFOND,
                   V0 * (0.72 + 0.42 * comptes[i] * vivants / TOTAL) + V_MONTE * t)

    def prendre(k, i):
        comptes[terrain[k]] -= 1
        terrain[k] = i
        comptes[i] += 1
        changements.append((k, i))

    def mordre(c, r, i):
        #  Les voisines de la case touchée tombent avec elle, sauf celles qui
        #  sont déjà à moi. C'est ce qui donne au front sa forme dentelée.
        for dc in range(-MORSURE, MORSURE + 1):
            for dr in range(-MORSURE, MORSURE + 1):
                if abs(dc) + abs(dr) != 1:
                    continue
                cc, rr = c + dc, r + dr
                if cc < 0 or cc >= COLS or rr < 0 or rr >= RANGS:
                    continue
                k = rr * COLS + cc
                if terrain[k] == i:
                    continue
                perdant = int(terrain[k])
                prendre(k, i)
                if perdant != NEUTRE and vivant[perdant] and comptes[perdant] <= 0:
                    eliminer(perdant)
                    return

    def devier(b):
        v = vitesse_de(b["i"])
        a = rng.uniform(-DEVIATION, DEVIATION)
        ca, sa = np.cos(a), np.sin(a)
        vx = b["vx"] * ca - b["vy"] * sa
        vy = b["vx"] * sa + b["vy"] * ca
        s = np.sqrt(vx * vx + vy * vy)
        if s > 1e-9:
            b["vx"], b["vy"] = vx * v / s, vy * v / s

    def eliminer(p):
        #  Ses cases ne passent pas d'un bloc au vainqueur : elles deviennent
        #  neutres et sont reprises une à une en partant des bords. Rien
        #  n'empêche une autre balle de venir se servir avant : la curée est
        #  ouverte à tous, et c'est le moment le plus disputé de la partie.
        nonlocal vivants, manche, prochaine, a_repartir, dette_rep, taux_rep
        nonlocal sacre, vainqueur, balles
        vivant[p] = 0
        vivants -= 1
        tombes.append(p)
        bx = next(b for b in balles if b["i"] == p)
        balles = [b for b in balles if b["i"] != p]
        chocs.append((t, "chute", p))

        cases = []
        for k in range(TOTAL):
            if terrain[k] != p:
                continue
            cx = X0 + (k % COLS + 0.5) * LC
            cy = Y0 + (k // COLS + 0.5) * LR
            cible, mieux = -1, float("inf")
            for b in balles:
                d = (b["x"] - cx) ** 2 + (b["y"] - cy) ** 2
                if d < mieux:
                    mieux, cible = d, b["i"]
            cases.append([k, cible, (bx["x"] - cx) ** 2 + (bx["y"] - cy) ** 2])
            comptes[p] -= 1
            comptes[NEUTRE] += 1
            terrain[k] = NEUTRE
            changements.append((k, NEUTRE))
        cases.sort(key=lambda c: -c[2])          # les bords d'abord
        a_repartir = cases
        dette_rep = 0.0

        if vivants == 1:
            #  Le sacre : le dernier debout recouvre tout le plateau. Sans cette
            #  dernière image, la partie s'arrête sur un terrain encore bariolé.
            vainqueur = balles[0]["i"]
            for c in a_repartir:
                c[1] = vainqueur
            taux_rep = len(a_repartir) / SACRE
            sacre = 1
            chocs.append((t, "sacre", vainqueur))
        else:
            taux_rep = len(a_repartir) / PARTAGE
            manche += 1
            prochaine = t + MANCHES[min(manche, len(MANCHES) - 1)]

    def conquerir(b):
        #  Les quatre sondes sont dépouillées ensemble, et le rebond n'est
        #  décidé qu'après. Appliquer chaque sonde au fil de la boucle donne un
        #  biais : si la gauche et la droite touchent toutes deux, c'est la
        #  dernière testée qui l'emporte, donc toujours la même direction —
        #  mesuré, onze victoires d'écart sur soixante parties. En sommant, deux
        #  sondes opposées s'annulent.
        pris = hx = hy = 0
        for sx, sy in SONDES:
            px, py = b["x"] + sx * R_BALLE, b["y"] + sy * R_BALLE
            if px < X0 or px >= X1 or py < Y0 or py >= Y1:
                continue
            c, r = int((px - X0) / LC), int((py - Y0) / LR)
            k = r * COLS + c
            if terrain[k] == b["i"]:
                continue
            perdant = int(terrain[k])
            prendre(k, b["i"])
            mordre(c, r, b["i"])
            pris = 1
            hx += sx
            hy += sy
            chocs.append((t, "case", b["i"], (b["x"] - W / 2) / (W / 2)))
            if perdant != NEUTRE and vivant[perdant] and comptes[perdant] <= 0:
                eliminer(perdant)
                if sacre:
                    return
        if hx:
            b["vx"] = -np.sign(hx) * abs(b["vx"])
        if hy:
            b["vy"] = -np.sign(hy) * abs(b["vy"])
        if pris:
            devier(b)

    def cliche():
        images.append((tuple((b["i"], b["x"], b["y"]) for b in balles),
                       tuple(changements), tuple(comptes), tuple(vivant),
                       t, prochaine, sacre, vainqueur))
        changements.clear()

    while fin is None and t < 120.0:
        t += DT
        if t >= DEPART:
            if a_repartir:
                dette_rep += taux_rep * DT
                while dette_rep >= 1 and a_repartir:
                    dette_rep -= 1
                    k, cible, _ = a_repartir.pop()
                    if terrain[k] != NEUTRE:
                        continue            # une balle est passée avant
                    prendre(k, cible)
            if sacre and not a_repartir:
                fin = t
            elif not sacre and vivants > 1 and t >= prochaine:
                #  Le plus petit royaume tombe. À égalité, le tirage départage.
                pire, moins = -1, float("inf")
                for i in range(N):
                    if not vivant[i]:
                        continue
                    c = comptes[i] + rng.uniform(0, 0.5)
                    if c < moins:
                        moins, pire = c, i
                eliminer(pire)

            if fin is None:
                #  L'ordre de passage est tiré au sort à chaque pas : deux
                #  balles qui visent la même case au même instant, la première
                #  servie l'emporte, et un ordre fixe donne un avantage
                #  systématique au premier de la liste.
                for b in [balles[j] for j in rng.permutation(len(balles))]:
                    b["x"] += b["vx"] * DT
                    b["y"] += b["vy"] * DT
                    mur = 0
                    if b["x"] < X0 + R_BALLE:
                        b["x"], b["vx"], mur = X0 + R_BALLE, abs(b["vx"]), 1
                    if b["x"] > X1 - R_BALLE:
                        b["x"], b["vx"], mur = X1 - R_BALLE, -abs(b["vx"]), 1
                    if b["y"] < Y0 + R_BALLE:
                        b["y"], b["vy"], mur = Y0 + R_BALLE, abs(b["vy"]), 1
                    if b["y"] > Y1 - R_BALLE:
                        b["y"], b["vy"], mur = Y1 - R_BALLE, -abs(b["vy"]), 1
                    #  La déviation s'applique aussi sur les murs : une balle
                    #  rentrée au fond de son propre camp n'y rencontre plus
                    #  rien à conquérir, donc plus rien qui la dévie, et repart
                    #  sur un circuit fermé qui ne revient jamais au front.
                    if mur:
                        devier(b)
                    conquerir(b)
                    if fin is not None:
                        break

        if t >= prochain_cliche:
            cliche()
            prochain_cliche += 1 / FPS_ECH

    fin = fin or t
    while prochain_cliche < fin + APRES + 0.5:
        cliche()
        prochain_cliche += 1 / FPS_ECH
    return images, chocs, tuple(tombes), fin, vainqueur


IMAGES, CHOCS, TOMBES, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def vers_case(k):
    return vers_scene(X0 + (k % COLS + 0.5) * LC, Y0 + (k // COLS + 0.5) * LR)


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class QuatreRoyaumes(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- le plateau -------------------------------------------------------
        #  Sept cent vingt cases. On ne les reconstruit jamais : la simulation
        #  n'enregistre que les changements d'une image à l'autre — quelques
        #  dizaines au plus — et l'on ne repeint que ceux-là. Repositionner sept
        #  cent vingt carrés à chaque image coûterait cent fois plus cher.
        cases = VGroup()
        for k in range(TOTAL):
            m = Rectangle(width=(LC - 2) * ECHELLE, height=(LR - 2) * ECHELLE,
                          stroke_width=0, fill_opacity=1)
            m.move_to(vers_case(k))
            cases.add(m)

        COUL_CASE = [teinte(h, 0.26, 0.62) for h in TEINTES] + ["#3F464D"]
        for k in range(TOTAL):
            qx, qy = (0 if k % COLS < COLS / 2 else 1), (0 if k // COLS < RANGS / 2 else 1)
            cases[k].set_fill(COUL_CASE[QUARTS.index((qx, qy))])

        cadre = Rectangle(width=(X1 - X0) * ECHELLE, height=(Y1 - Y0) * ECHELLE,
                          stroke_color="#8CAABE", stroke_opacity=0.22,
                          stroke_width=4, fill_opacity=0)
        cadre.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))

        cases.vu = -1

        def maj_cases(g):
            n = min(int(t.get_value() * FPS_ECH), len(IMAGES) - 1)
            if n < g.vu:                       # marche arrière : on repart de zéro
                g.vu = -1
            debut = g.vu + 1
            for m in range(debut, n + 1):
                for k, i in IMAGES[m][1]:
                    g[k].set_fill(COUL_CASE[i])
            g.vu = n

        cases.add_updater(maj_cases)

        # --- les ondes de conquête --------------------------------------------
        #  Un cercle qui s'ouvre et s'efface à chaque case prise. C'est ce qui
        #  fait vivre le plateau : sans elles, un damier qui change de couleur
        #  se lit comme une suite d'images fixes.
        #
        #  Pas de création à la volée : une réserve de cercles est allouée une
        #  fois, et chaque image y puise les prises des douze dernières — l'âge
        #  donne le rayon et l'opacité. Le rendu est donc sans état, et une
        #  image se dessine identique quel que soit l'ordre des appels.
        ONDE_AGE, ONDE_PAR_IMAGE = 12, 7
        vagues = VGroup(*[Circle(radius=0.1, stroke_width=0, fill_opacity=0)
                          for _ in range(ONDE_AGE * ONDE_PAR_IMAGE)])
        COUL_ONDE = [teinte(h, 0.78) for h in TEINTES] + ["#A6B0BA"]

        def maj_vagues(g):
            n = min(int(t.get_value() * FPS_ECH), len(IMAGES) - 1)
            s = 0
            for age in range(min(ONDE_AGE, n + 1)):
                v = 1 - age / ONDE_AGE
                for k, i in IMAGES[n - age][1][:ONDE_PAR_IMAGE]:
                    m = g[s]
                    s += 1
                    m.move_to(vers_case(k))
                    m.set(width=(16 + 190 * (1 - v)) * ECHELLE)
                    m.set_fill(COUL_ONDE[i], opacity=0.62 * v * v)
            for m in g[s:]:
                m.set_fill(opacity=0)

        vagues.add_updater(maj_vagues)

        # --- les balles -------------------------------------------------------
        #  set_opacity écrase l'opacité de chaque partie sans distinction : un
        #  halo fait de deux voiles à 14 % et 7 % devient un disque plein, et la
        #  balle qu'il est censé entourer disparaît dedans. On retient donc les
        #  opacités d'origine pour ne faire que les moduler.
        def memoriser(m):
            m.base_op = [(x, x.get_fill_opacity(), x.get_stroke_opacity())
                         for x in m.family_members_with_points()]
            return m

        def poser(m, k):
            for x, fo, so in m.base_op:
                x.set_fill(opacity=fo * k)
                x.set_stroke(opacity=so * k)

        balles = VGroup(*[memoriser(balle_mobject(TEINTES[i], R_BALLE))
                          for i in range(N)])
        halos = VGroup(*[memoriser(halo_mobject(TEINTES[i], R_BALLE))
                         for i in range(N)])

        def maj_balles(_):
            etats = instantane()[0]
            vus = set()
            for i, x, y in etats:
                vus.add(i)
                balles[i].move_to(vers_scene(x, y))
                halos[i].move_to(vers_scene(x, y))
                poser(balles[i], 1)
                poser(halos[i], 1)
            for i in range(N):
                if i not in vus:
                    poser(balles[i], 0)
                    poser(halos[i], 0)

        balles.add_updater(maj_balles)

        def instantane():
            return IMAGES[min(int(t.get_value() * FPS_ECH), len(IMAGES) - 1)]

        # --- l'accroche du haut -----------------------------------------------
        titre_a = accroche("choisis ta couleur")
        titre_b = accroche("qui sera le dernier debout ?")
        titre_b.set_opacity(0)

        def maj_titre(_):
            avant = instantane()[4] < DEPART
            titre_a.set_opacity(1 if avant else 0)
            titre_b.set_opacity(0 if avant else 1)

        titre_a.add_updater(maj_titre)

        # --- les pastilles du choix -------------------------------------------
        #  Les quatre couleurs, posées une à une : le spectateur en choisit une
        #  avant que la première case ne change de camp.
        PAS, YP = 240, 1616
        pastilles = VGroup()
        for i in range(N):
            x = W / 2 - PAS * 1.5 + i * PAS
            d = VGroup(halo_mobject(TEINTES[i], 46, ((1.8, 0.22),)),
                       balle_mobject(TEINTES[i], 46))
            d.move_to(vers_scene(x, YP))
            n = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.66))
            n.scale_to_fit_height(0.22).move_to(vers_scene(x, YP + 96))
            pastilles.add(memoriser(VGroup(d, n)))

        def maj_pastilles(g):
            tt = instantane()[4]
            if tt >= DEPART:
                for m in g:
                    poser(m, 0)
                return
            for i, m in enumerate(g):
                v = float(np.clip((tt - 0.25 - i * 0.16) / 0.32, 0, 1))
                poser(m, v)
                #  Un léger dépassement à l'arrivée : la pastille rebondit au
                #  lieu de simplement apparaître.
                e = v * (1 + 0.35 * np.sin(np.pi * v) * (1 - v))
                m.set(width=g.larg[i] * max(e, 1e-3))

        pastilles.larg = [m.width for m in pastilles]
        pastilles.add_updater(maj_pastilles)

        # --- le compte à rebours ----------------------------------------------
        voile = Rectangle(width=(X1 - X0) * ECHELLE, height=380 * ECHELLE,
                          stroke_width=0, fill_color="#04060A", fill_opacity=0)
        voile.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))
        chiffre = Text("3", weight=BOLD, color="#F6FBFE").scale_to_fit_height(1.5)
        chiffre.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))
        chiffre.set_opacity(0)
        chiffre.vu = None

        def maj_compte(_):
            tt = instantane()[4]
            if not (PRE_CHOIX <= tt < DEPART):
                voile.set_fill(opacity=0)
                chiffre.set_opacity(0)
                return
            #  3, 2, 1, puis GO, un temps chacun. Le chiffre entre grand et se
            #  resserre : le mouvement fait le compte à rebours autant que lui.
            temps = PRE_COMPTE / 4
            n = min(3, int((tt - PRE_CHOIX) / temps))
            f = (tt - PRE_CHOIX - n * temps) / temps
            if chiffre.vu != n:
                m = Text("GO !" if n == 3 else str(3 - n), weight=BOLD,
                         color="#4BFFA0" if n == 3 else "#F6FBFE")
                m.scale_to_fit_height(1.5 if n < 3 else 1.15)
                m.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))
                chiffre.become(m)
                chiffre.vu = n
                chiffre.base = m.height
            e = 1 + 0.6 * (1 - min(1.0, f / 0.3)) ** 2
            chiffre.scale_to_fit_height(chiffre.base * e)
            chiffre.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))
            chiffre.set_opacity(1 - 0.5 * max(0.0, (f - 0.72) / 0.28))
            voile.set_fill(opacity=0.62)

        voile.add_updater(maj_compte)

        # --- la barre : la carte du plateau ramenée à une ligne ----------------
        BX, BL, BY, BE = 40, 1000, 1520, 44
        piste = RoundedRectangle(width=BL * ECHELLE, height=BE * ECHELLE,
                                 corner_radius=BE / 2 * ECHELLE, stroke_width=0,
                                 fill_color="#FFFFFF", fill_opacity=0.07)
        piste.move_to(vers_scene(BX + BL / 2, BY + BE / 2))
        parts = VGroup(*[Rectangle(width=0.01, height=BE * ECHELLE, stroke_width=0,
                                   fill_color=teinte(h, 0.56), fill_opacity=1)
                         for h in TEINTES],
                       Rectangle(width=0.01, height=BE * ECHELLE, stroke_width=0,
                                 fill_color="#67707A", fill_opacity=1))

        def maj_parts(g):
            _, _, comptes, _, tt, _, _, _ = instantane()
            #  Rien de tout cela n'existe avant le départ : pendant le choix et
            #  le décompte, le bas de l'écran est aux pastilles.
            if tt < DEPART:
                piste.set_opacity(0)
                g.set_opacity(0)
                return
            piste.set_fill(opacity=0.07)
            x = BX
            for i, m in enumerate(g):
                l = BL * comptes[i] / TOTAL
                if l <= 0.5:
                    m.set_opacity(0)
                    continue
                m.set_opacity(1)
                m.stretch_to_fit_width(l * ECHELLE)
                m.move_to(vers_scene(x + l / 2, BY + BE / 2))
                x += l

        parts.add_updater(maj_parts)

        noms_m, parts_m = [], []
        for i in range(N):
            cx = BX + BL * (i + 0.5) / N
            n = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.64))
            n.scale_to_fit_height(0.235).move_to(vers_scene(cx, 1610))
            p = Text("25 %", weight=SEMIBOLD, color="#D7E4EB")
            p.scale_to_fit_height(0.19).move_to(vers_scene(cx, 1656))
            p.vu = None
            noms_m.append(n)
            parts_m.append(p)

        def maj_legende(_):
            _, _, comptes, vivant, tt, _, _, _ = instantane()
            if tt < DEPART:
                for m in legende:
                    m.set_opacity(0)
                return
            for i in range(N):
                if not vivant[i]:
                    noms_m[i].set_color("#78868F").set_opacity(0.5)
                texte = ("%d %%" % round(100 * comptes[i] / TOTAL)) if vivant[i] else "éliminé"
                if parts_m[i].vu != texte:
                    cx = BX + BL * (i + 0.5) / N
                    m = Text(texte, weight=SEMIBOLD,
                             color="#D7E4EB" if vivant[i] else "#78868F")
                    m.scale_to_fit_height(0.19).move_to(vers_scene(cx, 1656))
                    m.set_opacity(1 if vivant[i] else 0.5)
                    parts_m[i].become(m)
                    parts_m[i].vu = texte
                noms_m[i].set_opacity(0.5 if not vivant[i] else 1)
                parts_m[i].set_opacity(0.5 if not vivant[i] else 1)

        legende = VGroup(*noms_m, *parts_m)
        legende.add_updater(maj_legende)

        # --- le sablier de la manche ------------------------------------------
        sablier = Text("élimination dans 11 s", weight=BOLD, color="#AABEC8")
        sablier.scale_to_fit_height(0.30).move_to(vers_scene(W / 2, 1748))
        sablier.vu = None
        soustitre = Text("le plus petit royaume tombe", color="#8C9EA8")
        soustitre.scale_to_fit_height(0.185).move_to(vers_scene(W / 2, 1806))

        def maj_sablier(_):
            _, _, _, _, tt, prochaine, sacre, gagnant = instantane()
            if tt < DEPART:
                sablier.set_opacity(0)
                soustitre.set_opacity(0)
                return
            sablier.set_opacity(1)
            soustitre.set_opacity(0 if sacre else 1)
            if sacre:
                texte, couleur = "DERNIER DEBOUT", teinte(TEINTES[gagnant], 0.66)
            else:
                reste = max(0.0, prochaine - tt)
                if reste < 3:
                    #  Rouge et au dixième dans les trois dernières secondes :
                    #  c'est là qu'un royaume au bord du gouffre joue sa peau.
                    texte = "ÉLIMINATION DANS %s s" % ("%.1f" % reste).replace(".", ",")
                    couleur = "#FF6E6E"
                else:
                    texte = "élimination dans %d s" % int(np.ceil(reste))
                    couleur = "#AABEC8"
            if sablier.vu != texte:
                m = Text(texte, weight=BOLD, color=couleur)
                m.scale_to_fit_height(0.30).move_to(vers_scene(W / 2, 1748))
                sablier.become(m)
                sablier.vu = texte

        sablier.add_updater(maj_sablier)

        # --- bandeau de fin ---------------------------------------------------
        fin_voile, fin_bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "seul royaume debout", t, FIN)

        self.add(cases, cadre, vagues, halos, balles, voile, chiffre, pastilles,
                 piste, parts, legende, sablier, soustitre,
                 titre_a, titre_b, fin_voile, fin_bloc)

        if AVEC_SON:
            gamme = (0, 3, 7, 10, 12)
            ev = []
            for k, c in enumerate(CHOCS):
                if c[1] == "case":
                    if k % 4:
                        continue
                    ev.append((c[0], "cloche", gamme[k % 5] + c[2] * 5, c[3], 0.11))
                elif c[1] == "chute":
                    ev.append((c[0], "souffle", 200, 0.0, 0.55))
            #  Trois notes pour le décompte, une quatrième pour le départ.
            for j in range(3):
                ev.append((PRE_CHOIX + j * PRE_COMPTE / 4, "cloche", 7, 0.0, 0.30))
            ev.append((DEPART - PRE_COMPTE / 4, "cloche", 19, 0.0, 0.40))
            ev += accord_victoire(FIN - SACRE + 0.1, VAINQUEUR % 2 == 1)
            self.add_sound(bande_son(ev, DUREE, "quatre_royaumes.wav"))

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if "--graines" in sys.argv:
        #  De quoi choisir un duel ni trop court ni joué d'avance.
        print("graine   durée  vainqueur")
        for g in range(30):
            res = simuler(g)
            print("%5d %7.1f %10s" % (g, res[-2], NOMS[res[-1]]))
    else:
        config.pixel_width, config.pixel_height = 1080, 1920
        config.frame_rate = 60
        QuatreRoyaumes().render()
