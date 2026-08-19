"""
Les gloutons — reproduction Manim du duel, format vertical.

Quatre balles, toutes de la même taille au départ, dans une arène presque
deux fois plus grande que celle du dernier debout. À chaque rencontre, la plus
grosse arrache un morceau de la plus petite ; sous quatorze pixels de rayon, on
éclate.

Le terrain porte quinze pastilles grises, remplacées dès qu'elles sont avalées.
Elles font l'inverse d'un choc : leur gain décroît avec la taille de qui les
mange — nul au plafond, maximal au bord de la mort. C'est le seul mécanisme du
film qui pousse vers l'égalité, et c'est lui qui fait les retournements. Passé
treize secondes, elles ne repoussent plus.

Rendu :
    manim -r 1080,1920 --fps 60 gloutons.py LesGloutons

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python gloutons.py --graines` en essaie une série et affiche, pour chacune, la
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
#  L'arène est un rectangle, et non le disque de la 14 : à cadre égal il tient
#  presque deux fois plus de surface, et il en fallait pour que les pastilles
#  grises aient où se poser loin de tout le monde.
X0, X1, Y0, Y1 = 40, 1040, 392, 1752
N = 4
R_DEPART = 34.0                # même taille pour tout le monde au départ
R_MORT = 14.0                  # en deçà, la balle éclate
R_MAX = 76.0                   # au-delà, manger ne rapporte plus rien
V0 = 660.0                     # px/s, constante : pas de gravité

#  Ce qu'un choc transfère : une part du rayon du plus petit passe au plus
#  gros, et la part grandit avec le temps.
#
#  Deux versions ont été essayées et mesurées. Prélever sur l'ÉCART des rayons
#  paraît plus juste — à taille rigoureusement égale, un choc ne transfère rien
#  — mais crée un point fixe : les pastilles poussant vers l'égalité et le
#  transfert s'annulant à l'égalité, les quatre balles s'installent au même
#  rayon et n'en bougent plus. Aucune partie terminée en quatorze minutes de
#  simulation. On prélève donc sur le rayon du plus petit, ce qui mord toujours.
#
#  Reste que cela transfère aussi à égalité parfaite, et c'est alors l'ordre de
#  la boucle qui désigne le gros : au premier choc, toutes les balles étant au
#  même rayon, le plus petit indice l'emportait — 17 victoires sur trente pour
#  la première couleur, aucune pour la quatrième. L'égalité se tranche donc à
#  pile ou face.
TRANSFERT0 = 0.09
TRANSFERT_ACCEL = 0.036        # par seconde
TRANSFERT_MAX = 0.6
GARDE = 0.75                   # part conservée : les tailles ne s'envolent pas
#  Un délai de garde entre deux morsures d'une même paire. Sans lui, deux balles
#  qui restent au contact — coincées contre un mur, par exemple — se transfèrent
#  du rayon à *chaque pas de calcul*, soit quatre cent quatre-vingts fois par
#  seconde : mesuré, une balle mourait dès la première seconde de jeu.
CHOC_REPOS = 0.15              # s

#  Les pastilles grises. Elles sont l'inverse d'un choc : un choc prend au plus
#  petit, une pastille profite surtout à lui. Le gain décroît avec la taille —
#  nul pour une balle au plafond, maximal pour une balle au bord de la mort.
#
#  Et elles se tarissent. C'est indispensable, pas décoratif : tant qu'une balle
#  drainée peut se refaire sur le terrain, elle se refait — mesuré, aucune
#  partie ne se terminait en quatorze minutes, les quatre balles oscillant
#  indéfiniment autour de la même taille.
GRIS_N = 15
R_GRIS = 16.0
GRIS_GAIN = 7.0
GRIS_ECART = 150.0             # px : distance minimale d'apparition d'une balle
GRIS_FIN = 13.0                # s de jeu après quoi plus rien ne repousse

#  L'étau. Une grande arène rend les rencontres rares, et c'est de là que
#  venaient les parties interminables : la médiane tenait en 29 s mais une
#  partie sur dix dépassait 42 s, les deux dernières balles tournant sans se
#  croiser. Accélérer le transfert n'y changeait rien — le problème n'est pas ce
#  qu'un choc coûte, c'est qu'il n'y a plus de choc.
ETAU = 15.0
ETAU_V = 16.0
ETAU_MAX = 300.0

DT = 1 / 480

#  Le lever de rideau. La simulation ne connaît que le temps de jeu : le film
#  lui ajoute six secondes en tête.
PRE_CHOIX = 2.8
PRE_COMPTE = 3.2
LANCEMENT = PRE_CHOIX + PRE_COMPTE

NOMS = ("ROUGE", "JAUNE", "VERT", "BLEU")
TEINTES = (354.0, 44.0, 132.0, 205.0)

#  Graine 16, choisie sur vingt. BLEU tombe à 11 s, JAUNE à 14 s, et il reste
#  douze secondes de face-à-face entre ROUGE et VERT — la plus longue finale des
#  vingt, et ROUGE la gagne après avoir été, un moment, la plus petite encore en
#  vie. 26 s de jeu.
GRAINE = 16


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)

    def marge(t):
        return min(ETAU_MAX, max(0.0, (t - ETAU) * ETAU_V))

    def bords(t):
        m = marge(t)
        return X0 + m, X1 - m, Y0 + m, Y1 - m

    balles = []
    for i in range(N):
        #  Les quatre balles aux quatre coins, à égale distance du centre et
        #  toutes du même rayon : aucune ne commence avantagée. Seul le cap est
        #  tiré au sort.
        qx, qy = i % 2, i >> 1
        cap = rng.uniform(0, TAU)
        balles.append({"i": i, "vivant": 1, "r": R_DEPART, "manges": 0,
                       "x": X0 + (X1 - X0) * (0.72 if qx else 0.28),
                       "y": Y0 + (Y1 - Y0) * (0.72 if qy else 0.28),
                       "vx": np.cos(cap) * V0, "vy": np.sin(cap) * V0})

    t = 0.0
    gris = []

    def place_libre():
        #  Un point de l'arène à bonne distance des balles — une pastille née
        #  sous une balle serait avalée sans qu'on l'ait vue — et des autres
        #  pastilles, qui en tas se liraient comme une seule.
        ax0, ax1, ay0, ay1 = bords(t)
        for _ in range(40):
            x = rng.uniform(ax0 + R_GRIS, ax1 - R_GRIS)
            y = rng.uniform(ay0 + R_GRIS, ay1 - R_GRIS)
            if any(b["vivant"] and np.hypot(b["x"] - x, b["y"] - y) < GRIS_ECART + b["r"]
                   for b in balles):
                continue
            if any(not g["mort"] and np.hypot(g["x"] - x, g["y"] - y) < 5 * R_GRIS
                   for g in gris):
                continue
            return {"x": x, "y": y, "ne": 0.0, "mort": 0}
        return {"x": (ax0 + ax1) / 2, "y": (ay0 + ay1) / 2, "ne": 0.0, "mort": 0}

    for _ in range(GRIS_N):
        g = place_libre()
        g["ne"] = 1.0
        gris.append(g)

    choc_t = np.full((N, N), -9.0)
    images, chocs, morts = [], [], []
    vainqueur, fin = -1, None
    prochain_cliche = 0.0

    def cliche():
        images.append((
            tuple((b["x"], b["y"], b["r"], b["vivant"], b["manges"]) for b in balles),
            tuple((g["x"], g["y"], g["ne"]) for g in gris if not g["mort"]),
            bords(t), t))

    def eclater(b):
        nonlocal vainqueur, fin
        b["vivant"] = 0
        morts.append((t, b["x"], b["y"], b["i"]))
        reste = [m for m in balles if m["vivant"]]
        if len(reste) == 1:
            vainqueur = reste[0]["i"]
            fin = t

    while fin is None and t < 200.0:
        t += DT
        ax0, ax1, ay0, ay1 = bords(t)

        for b in balles:
            if not b["vivant"]:
                continue
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            mur = 0
            if b["x"] < ax0 + b["r"]:
                b["x"], b["vx"], mur = ax0 + b["r"], abs(b["vx"]), 1
            if b["x"] > ax1 - b["r"]:
                b["x"], b["vx"], mur = ax1 - b["r"], -abs(b["vx"]), 1
            if b["y"] < ay0 + b["r"]:
                b["y"], b["vy"], mur = ay0 + b["r"], abs(b["vy"]), 1
            if b["y"] > ay1 - b["r"]:
                b["y"], b["vy"], mur = ay1 - b["r"], -abs(b["vy"]), 1
            if mur:
                #  Une petite déviation à chaque mur, sinon une balle lancée à
                #  45° dans un rectangle reprend éternellement le même circuit
                #  fermé et ne rencontre jamais personne.
                a = rng.uniform(-0.12, 0.12)
                ca, sa = np.cos(a), np.sin(a)
                vx = b["vx"] * ca - b["vy"] * sa
                vy = b["vx"] * sa + b["vy"] * ca
                s = np.sqrt(vx * vx + vy * vy) or 1.0
                b["vx"], b["vy"] = vx * V0 / s, vy * V0 / s
                #  La note dépend de la taille : les grosses parlent grave. On
                #  entend donc la hiérarchie se faire.
                demi = round(24 * (1 - (b["r"] - R_MORT) / (R_MAX - R_MORT)))
                chocs.append((t, "mur", demi, (b["x"] - W / 2) / (W / 2)))

        # --- les pastilles grises -----------------------------------------
        for g in gris:
            if g["mort"]:
                continue
            if not (ax0 < g["x"] < ax1 and ay0 < g["y"] < ay1):
                g["mort"] = 1
                continue
            if g["ne"] < 1:
                g["ne"] = min(1.0, g["ne"] + DT * 3.5)
            for b in balles:
                if not b["vivant"]:
                    continue
                if np.hypot(b["x"] - g["x"], b["y"] - g["y"]) > b["r"] + R_GRIS * g["ne"]:
                    continue
                gain = GRIS_GAIN * max(0.0, 1 - (b["r"] - R_MORT) / (R_MAX - R_MORT))
                b["r"] = min(R_MAX, b["r"] + gain)
                b["manges"] += 1
                chocs.append((t, "pastille", 24, (g["x"] - W / 2) / (W / 2)))
                #  Remplacée ailleurs tant que le terrain ravitaille ; passé
                #  l'heure, elle disparaît pour de bon.
                if t < GRIS_FIN:
                    g.update(place_libre())
                else:
                    g["mort"] = 1
                break

        # --- les rencontres -----------------------------------------------
        part = min(TRANSFERT_MAX, TRANSFERT0 + TRANSFERT_ACCEL * t)
        for i in range(N):
            a = balles[i]
            if not a["vivant"]:
                continue
            for j in range(i + 1, N):
                b = balles[j]
                if not b["vivant"]:
                    continue
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                dd = np.sqrt(dx * dx + dy * dy)
                mini = a["r"] + b["r"]
                if dd >= mini or dd < 1e-9:
                    continue
                nx, ny = dx / dd, dy / dd
                corr = (mini - dd) / 2
                a["x"] -= nx * corr; a["y"] -= ny * corr
                b["x"] += nx * corr; b["y"] += ny * corr
                vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
                if vn > 0:
                    continue
                a["vx"] += vn * nx; a["vy"] += vn * ny
                b["vx"] -= vn * nx; b["vy"] -= vn * ny
                for m in (a, b):
                    s = np.sqrt(m["vx"] ** 2 + m["vy"] ** 2)
                    if s > 1e-9:
                        m["vx"] *= V0 / s
                        m["vy"] *= V0 / s
                if t - choc_t[i, j] < CHOC_REPOS:
                    continue
                choc_t[i, j] = t
                if a["r"] > b["r"] or (a["r"] == b["r"] and rng.random() < 0.5):
                    gros, petit = a, b
                else:
                    gros, petit = b, a
                pris = petit["r"] * part
                petit["r"] -= pris
                gros["r"] = min(R_MAX, gros["r"] + pris * GARDE)
                chocs.append((t, "choc", 19, 0.0))
                if petit["r"] < R_MORT:
                    eclater(petit)
                    if fin is not None:
                        break
            if fin is not None:
                break

        if t >= prochain_cliche:
            cliche()
            prochain_cliche += 1 / FPS_ECH

    fin = fin or t
    while prochain_cliche < fin + APRES + 0.5:
        cliche()
        prochain_cliche += 1 / FPS_ECH
    return images, chocs, morts, fin, vainqueur


IMAGES, CHOCS, MORTS, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = LANCEMENT + FIN + APRES


def instantane(t):
    #  Le temps du film moins le rideau : avant le GO, on montre la première
    #  image, partie figée sur la ligne de départ.
    return IMAGES[min(int(max(0.0, t - LANCEMENT) * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class LesGloutons(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        #  set_opacity écrase l'opacité de chaque partie sans distinction : un
        #  halo fait de deux voiles à 15 % et 7 % deviendrait un disque plein et
        #  la balle disparaîtrait dedans. On retient les opacités d'origine pour
        #  ne faire que les moduler.
        def memoriser(m):
            m.base_op = [(x, x.get_fill_opacity(), x.get_stroke_opacity())
                         for x in m.family_members_with_points()]
            return m

        def poser(m, k):
            for x, fo, so in m.base_op:
                x.set_fill(opacity=fo * k)
                x.set_stroke(opacity=so * k)

        # --- l'arène ----------------------------------------------------------
        arene = RoundedRectangle(width=(X1 - X0) * ECHELLE,
                                 height=(Y1 - Y0) * ECHELLE,
                                 corner_radius=34 * ECHELLE,
                                 stroke_color="#8CAABE", stroke_opacity=0.24,
                                 stroke_width=5, fill_opacity=0)
        arene.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))

        def maj_arene(m):
            _, _, (ax0, ax1, ay0, ay1), _ = instantane(t.get_value())
            m.stretch_to_fit_width((ax1 - ax0) * ECHELLE)
            m.stretch_to_fit_height((ay1 - ay0) * ECHELLE)
            m.move_to(vers_scene((ax0 + ax1) / 2, (ay0 + ay1) / 2))
            #  Le cadre rougit et s'épaissit à mesure que l'étau se referme.
            serre = (X1 - X0 - (ax1 - ax0)) / (2 * ETAU_MAX)
            m.set_stroke(color=teinte(16, 0.52 + 0.10 * serre, 0.80) if serre > 0
                         else "#8CAABE",
                         width=5 + 4 * serre,
                         opacity=0.24 + 0.56 * serre)

        arene.add_updater(maj_arene)

        # --- les pastilles grises ---------------------------------------------
        pastilles = VGroup(*[
            VGroup(Circle(radius=R_GRIS * 2.1 * ECHELLE, stroke_width=0,
                          fill_color="#C9D6E0", fill_opacity=0.16),
                   Circle(radius=R_GRIS * ECHELLE, stroke_width=0,
                          fill_color="#B9C6D2", fill_opacity=1))
            for _ in range(GRIS_N)])
        for m in pastilles:
            memoriser(m)

        def maj_pastilles(g):
            _, gr, _, _ = instantane(t.get_value())
            for k, m in enumerate(g):
                if k >= len(gr):
                    poser(m, 0)
                    continue
                x, y, ne = gr[k]
                poser(m, 1)
                m.set(width=2 * R_GRIS * 2.1 * max(ne, 1e-3) * ECHELLE)
                m.move_to(vers_scene(x, y))

        pastilles.add_updater(maj_pastilles)

        # --- les balles -------------------------------------------------------
        balles = VGroup(*[balle_mobject(TEINTES[i], R_DEPART) for i in range(N)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_DEPART, ((1.7, 0.15), (2.5, 0.07)))
                         for i in range(N)])
        for m in list(balles) + list(halos):
            memoriser(m)

        def maj_balles(_):
            etats, _, _, _ = instantane(t.get_value())
            for i, (x, y, r, vivant, _m) in enumerate(etats):
                c = vers_scene(x, y)
                balles[i].set(width=2 * max(r, 1e-3) * ECHELLE).move_to(c)
                halos[i].set(width=2 * max(r, 1e-3) * 2.5 * ECHELLE).move_to(c)
                poser(balles[i], 1 if vivant else 0)
                poser(halos[i], 1 if vivant else 0)

        balles.add_updater(maj_balles)

        # --- le tableau : les quatre balles à leur taille réelle ---------------
        #  Quatre jauges diraient la même chose que les balles elles-mêmes. La
        #  hiérarchie se lit d'un coup, et les éteintes restent en place pour
        #  qu'on voie qui est tombé.
        YT = 214
        vignettes, noms_m, croix = VGroup(), VGroup(), VGroup()
        for i in range(N):
            x = W / 2 + (i - (N - 1) / 2) * 200
            vignettes.add(Circle(radius=R_DEPART * 0.78 * ECHELLE, stroke_width=2.5,
                                 fill_opacity=1).move_to(vers_scene(x, YT)))
            n = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.66))
            n.scale_to_fit_height(0.185).move_to(vers_scene(x, YT + 98))
            noms_m.add(n)
            c = VGroup(Line(vers_scene(x - 16, YT - 16), vers_scene(x + 16, YT + 16)),
                       Line(vers_scene(x + 16, YT - 16), vers_scene(x - 16, YT + 16)))
            c.set_stroke(color="#FFFFFF", width=3.5, opacity=0.16)
            croix.add(c)

        def maj_vignettes(_):
            etats, _, _, _ = instantane(t.get_value())
            for i, (_x, _y, r, vivant, _m) in enumerate(etats):
                x = W / 2 + (i - (N - 1) / 2) * 200
                if vivant:
                    vignettes[i].set(width=2 * max(6.0, r * 0.78) * ECHELLE)
                    vignettes[i].move_to(vers_scene(x, YT))
                    vignettes[i].set_fill(teinte(TEINTES[i], 0.60), opacity=1)
                    vignettes[i].set_stroke(teinte(TEINTES[i], 0.82), width=2.5,
                                            opacity=0.7)
                    croix[i].set_stroke(opacity=0)
                    noms_m[i].set_opacity(1)
                else:
                    vignettes[i].set(width=2 * 11 * ECHELLE)
                    vignettes[i].move_to(vers_scene(x, YT))
                    vignettes[i].set_fill("#FFFFFF", opacity=0.07)
                    vignettes[i].set_stroke(width=0)
                    croix[i].set_stroke(opacity=0.16)
                    noms_m[i].set_opacity(0)

        vignettes.add_updater(maj_vignettes)

        #  Les deux compteurs sur une ligne, mesurés puis centrés ensemble : à
        #  positions fixes, « plus rien ne repousse » vient recouvrir l'autre.
        #  Toutes les variantes de cette ligne doivent avoir le même corps :
        #  scale_to_fit_height le fait dépendre des jambages et des majuscules
        #  du texte, si bien que « plus de repousse » s'affichait deux fois plus
        #  petit que « 15 pastilles ». On mesure donc un gabarit une fois, et on
        #  applique le même facteur à tout le monde.
        #  Toutes les variantes de cette ligne doivent avoir le même corps :
        #  scale_to_fit_height le fait dépendre des jambages et des majuscules
        #  du texte. On mesure donc un gabarit une fois, et on applique le même
        #  facteur à tout le monde. Et la ligne est composée de morceaux
        #  séparés, non d'une seule chaîne : au-delà d'une trentaine de
        #  caractères, Pango replie le texte sur deux lignes et le compteur
        #  devient illisible.
        gabarit = Text("Agp", color="#A0B4BE")
        ECH_TXT = 0.21 / gabarit.height

        #  Trois morceaux fixes, mis à jour par become et replacés à la mesure.
        #  Remplacer les sous-objets d'un groupe depuis un updater ne suffit
        #  pas — les anciens continuent d'être dessinés, et les générations
        #  s'empilent les unes sur les autres.
        def bout(txt, coul):
            return Text(txt, color=coul).scale(ECH_TXT)

        c_g = bout("4 en lice", "#A0B4BE")
        c_p = bout("·", "#6E7C86")
        c_d = bout("15 pastilles", "#A0B4BE")
        c_f = bout("·  plus de repousse", "#FF9696")
        compteurs = VGroup(c_g, c_p, c_d, c_f)
        compteurs.vu = None
        YC = vers_scene(W / 2, 350)[1]

        def maj_compteurs(_):
            etats, gr, _, tt = instantane(t.get_value())
            vivantes = sum(1 for e in etats if e[3])
            npast, tarie = len(gr), tt >= GRIS_FIN
            if compteurs.vu != (vivantes, npast, tarie):
                c_g.become(bout("%d en lice" % vivantes, "#A0B4BE"))
                c_d.become(bout("%d pastille%s" % (npast, "s" if npast > 1 else ""),
                                "#FF9696" if tarie else "#A0B4BE"))
                compteurs.vu = (vivantes, npast, tarie)
            c_f.set_opacity(1 if tarie else 0)
            parts = [c_g, c_p, c_d] + ([c_f] if tarie else [])
            total = sum(p.width for p in parts) + 0.22 * (len(parts) - 1)
            x = -total / 2
            for p in parts:
                p.move_to(np.array([x + p.width / 2, YC, 0.0]))
                x += p.width + 0.22

        compteurs.add_updater(maj_compteurs)

        # --- le lever de rideau -----------------------------------------------
        rideau = RoundedRectangle(width=(X1 - X0) * ECHELLE,
                                  height=(Y1 - Y0) * ECHELLE,
                                  corner_radius=34 * ECHELLE, stroke_width=0,
                                  fill_color="#04060A", fill_opacity=0)
        rideau.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))

        PAS_P, YP = 232, (Y0 + Y1) / 2 - 40
        choix = VGroup()
        for i in range(N):
            x = W / 2 - PAS_P * (N - 1) / 2 + i * PAS_P
            d = VGroup(halo_mobject(TEINTES[i], 56, ((1.8, 0.22),)),
                       balle_mobject(TEINTES[i], 56))
            d.move_to(vers_scene(x, YP))
            n = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.66))
            n.scale_to_fit_height(0.22).move_to(vers_scene(x, YP + 112))
            choix.add(memoriser(VGroup(d, n)))
        choix.larg = [m.width for m in choix]

        chiffre = Text("3", weight=BOLD, color="#F6FBFE").scale_to_fit_height(1.6)
        chiffre.move_to(vers_scene(W / 2, (Y0 + Y1) / 2))
        chiffre.set_opacity(0)
        chiffre.vu = None
        chiffre.base = chiffre.height

        def maj_rideau(_):
            tt = t.get_value()
            if tt >= LANCEMENT:
                rideau.set_fill(opacity=0)
                for m in choix:
                    poser(m, 0)
                chiffre.set_opacity(0)
                return
            rideau.set_fill(opacity=0.76)
            if tt < PRE_CHOIX:
                chiffre.set_opacity(0)
                for i, m in enumerate(choix):
                    v = float(np.clip((tt - 0.25 - i * 0.16) / 0.32, 0, 1))
                    poser(m, v)
                    #  Un léger dépassement à l'arrivée : la pastille rebondit
                    #  au lieu de simplement apparaître.
                    e = v * (1 + 0.35 * np.sin(np.pi * v) * (1 - v))
                    m.set(width=choix.larg[i] * max(e, 1e-3))
                return
            for m in choix:
                poser(m, 0)
            #  3, 2, 1, puis GO, un temps chacun.
            temps = PRE_COMPTE / 4
            n = min(3, int((tt - PRE_CHOIX) / temps))
            f = (tt - PRE_CHOIX - n * temps) / temps
            if chiffre.vu != n:
                m = Text("GO !" if n == 3 else str(3 - n), weight=BOLD,
                         color="#4BFFA0" if n == 3 else "#F6FBFE")
                m.scale_to_fit_height(1.6 if n < 3 else 1.2)
                chiffre.become(m)
                chiffre.vu = n
                chiffre.base = m.height
            e = 1 + 0.6 * (1 - min(1.0, f / 0.3)) ** 2
            chiffre.scale_to_fit_height(chiffre.base * e)
            chiffre.move_to(vers_scene(W / 2, (Y0 + Y1) / 2))
            chiffre.set_opacity(1 - 0.5 * max(0.0, (f - 0.72) / 0.28))

        rideau.add_updater(maj_rideau)

        # --- bandeau de fin ---------------------------------------------------
        avale = IMAGES[-1][0][VAINQUEUR][4]
        voile, bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "%d pastilles avalées" % avale, t, LANCEMENT + FIN)

        self.add(accroche("choisis ta couleur"), vignettes, noms_m, croix,
                 compteurs, arene, pastilles, halos, balles,
                 rideau, choix, chiffre, voile, bloc)

        if AVEC_SON:
            ev = []
            for k, (instant, genre, hauteur, pan) in enumerate(CHOCS):
                if genre == "mur":
                    if k % 2:
                        continue
                    ev.append((instant + LANCEMENT, "cloche", hauteur, pan, 0.12))
                elif genre == "pastille":
                    ev.append((instant + LANCEMENT, "cloche", 24, pan, 0.11))
                else:
                    ev.append((instant + LANCEMENT, "cloche", 19, pan, 0.10))
            ev += [(m[0] + LANCEMENT, "souffle", 700, (m[1] - W / 2) / (W / 2), 0.44)
                   for m in MORTS]
            #  Trois notes pour le décompte, une quatrième pour le départ.
            for j in range(3):
                ev.append((PRE_CHOIX + j * PRE_COMPTE / 4, "cloche", 7, 0.0, 0.30))
            ev.append((LANCEMENT - PRE_COMPTE / 4, "cloche", 19, 0.0, 0.40))
            ev += accord_victoire(LANCEMENT + FIN + 0.15)
            self.add_sound(bande_son(ev, DUREE, "gloutons.wav"))

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
        LesGloutons().render()
