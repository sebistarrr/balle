"""
Les deux épreuves — reproduction Manim du duel, format vertical.

Cinq balles, six mille pixels de descente, et deux obstacles qui
rassemblent le peloton au lieu de l'étaler. La herse barre toute la largeur :
une seule fenêtre, qui va et vient, et des battants en pente qui vous y font
glisser. Le sas attend le peloton — il ne s'ouvre que lorsque quatre balles
patientent dessus, ou au bout de neuf secondes — puis lâche tout le monde
ensemble dans la ligne droite finale.

Deux réglages viennent de la mesure, pas de l'intuition. Le sas s'ouvre sur
quorum et non sur horloge : à cycle fixe il découpait le temps en tranches et
relançait les balles à une tranche entière d'écart. Et les battants de la herse
sont en pente : sur une barre horizontale une balle se pose et n'en repart
jamais.

Rendu :
    manim -r 1080,1920 --fps 60 deux_epreuves.py DeuxEpreuves

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python deux_epreuves.py --graines` en essaie une série et affiche, pour chacune, la
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
X0, X1 = 70, 1010
DEPART = 120
ARRIVEE = 6250              # longueur du parcours, en px de monde
R_BALLE = 24
G0 = 900.0
G_MONTE = 16.0
REBOND = 0.50
REBOND_PALE = 0.72
V_MAX = 1400.0
FROTTE_X = 0.9993
DT = 1 / 480

CAM_ANCRE = 0.38
CAM_SUIVI = 6.0
#  Le monde est masqué au-dessus de cette hauteur : au-dessus il n'y a que la
#  question posée au spectateur. Plus de classement ni de chiffre d'écart — le
#  pari est de désigner une couleur avant le départ, et un tableau qui donne
#  l'ordre à chaque instant y répondrait à sa place.
VUE_HAUT = 215

NOMS = ("ROUGE", "JAUNE", "VERT", "BLEU", "VIOLET")
TEINTES = (354.0, 38.0, 104.0, 190.0, 280.0)
N = len(NOMS)

#  Graine 6, choisie sur vingt-six : 34,6 s, dont 9,6 s dans la dernière ligne
#  droite au ralenti, et JAUNE franchit la ligne 81 px devant ROUGE — moins de
#  deux balles d'écart. Deux graines finissaient plus serré encore, mais sur un
#  film plus court : c'est le temps passé au ralenti qui fait le suspens.
GRAINE = 6

# --------------------------------------------------------------------------
#  Les deux épreuves
#
#  Un parcours ordinaire étale le peloton : chaque obstacle ajoute du hasard,
#  et les écarts ne font que grandir. Pour une course serrée il faut l'inverse
#  — des obstacles qui *rassemblent*, en faisant attendre les premiers arrivés.
# --------------------------------------------------------------------------

#  1. La herse : deux battants qui barrent toute la largeur, séparés par une
#     fenêtre qui va et vient.
#
#     Les battants descendent vers la fenêtre. C'est nécessaire, pas
#     décoratif : sur une barre horizontale une balle se pose et n'en repart
#     plus — rien ne la déséquilibre. Avec la pente, une balle posée roule
#     toujours vers l'ouverture et finit par tomber.
HERSE_Y = 1620              # hauteur de la fenêtre (le point bas)
HERSE_PENTE = 120           # dénivelé des battants, de la paroi à la fenêtre
HERSE_LARG = 150            # largeur de la fenêtre
HERSE_PER = 3.2             # s pour un aller-retour
HERSE_EP = 13


def herse_x(t):
    return ((X0 + X1) / 2
            + (X1 - X0 - HERSE_LARG - 120) / 2 * np.sin(TAU * t / HERSE_PER))


def battants(t):
    """Les deux battants à l'instant t, du bord vers la fenêtre."""
    g = herse_x(t) - HERSE_LARG / 2
    d = herse_x(t) + HERSE_LARG / 2
    return ((X0, HERSE_Y - HERSE_PENTE, g, HERSE_Y),
            (d, HERSE_Y, X1, HERSE_Y - HERSE_PENTE))


#  2. Le sas : un entonnoir qui rassemble, fermé par une trappe. C'est lui qui
#     remet la course à zéro — mais seulement si sa règle d'ouverture est la
#     bonne. Une trappe à cycle fixe ne rassemble rien : elle découpe le temps
#     en tranches, et deux balles séparées d'une seconde repartent souvent à
#     une tranche entière d'écart. Mesuré sur la page, l'écart au sas valait
#     3,5 s, soit exactement la période. La trappe attend donc le peloton au
#     lieu de compter : elle s'ouvre dès que SAS_QUORUM balles patientent
#     dessus, ou au bout de SAS_DELAI si elles ne viennent pas.
SAS_Y = 4560
SAS_G, SAS_D = 400, 680     # largeur de la trappe
SAS_QUORUM = 4              # balles qui déclenchent l'ouverture
SAS_DELAI = 9.0             # s d'attente maximale
SAS_OUVERT = 1.3            # s d'ouverture

#  3. Le ralenti. Sous le sas, la pesanteur tombe à un peu moins de la moitié
#     et la vitesse est plafonnée plus bas : la dernière ligne droite se joue
#     donc au ralenti. C'est là que tout se décide, et il faut avoir le temps
#     de le voir — à pleine pesanteur, les mille sept cents derniers pixels
#     passaient en cinq secondes ; ils en prennent maintenant dix.
RALENTI = 0.42              # part de pesanteur conservée sous le sas
RALENTI_V = 0.55            # part de vitesse maximale conservée

# --------------------------------------------------------------------------
#  Le parcours. Tout obstacle est une capsule — un segment doté d'une
#  épaisseur — ou un disque : une seule primitive de contact suffit donc pour
#  les clous, les parois inclinées, l'entonnoir, la herse et les moulins.
# --------------------------------------------------------------------------
CLOUS, SEGMENTS, ROTORS = [], [], []


def _clou(x, y, r=13):
    CLOUS.append((x, y, r))


def _segment(x1, y1, x2, y2, ep=11):
    SEGMENTS.append((x1, y1, x2, y2, ep))


def _rotor(x, y, longueur, pales, omega, ep=13):
    ROTORS.append({"x": x, "y": y, "longueur": longueur, "pales": pales,
                   "omega": omega, "ep": ep})


#  Une rangée de clous. Deux règles, apprises en mesurant : toute fente plus
#  étroite qu'une balle est un piège — la balle s'y coince, à l'arrêt, et la
#  course ne finit jamais. On garde donc partout un jeu d'au moins trois
#  rayons, et l'on plante les clous des rangées paires *sur* les parois, pour
#  qu'il ne subsiste aucune fente le long des bords. Les rangées impaires,
#  décalées d'un demi-pas, s'arrêtent une place avant le bord.
JEU = 3 * R_BALLE


def _rangee(l, y, pas, r):
    if pas - 2 * r < JEU:
        raise ValueError("rangée trop serrée : %s" % y)
    if l % 2 == 0:
        x = float(X0)
        while x < X1 + 1:
            _clou(x, y, r)
            x += pas
    else:
        x = X0 + 1.5 * pas
        while x < X1 - 1.5 * pas + 1:
            _clou(x, y, r)
            x += pas


#  A. le champ de clous : de quoi disperser le peloton d'entrée
for _l in range(5):
    _rangee(_l, 430 + _l * 200, (X1 - X0) / 9, 13)

#  C. la chicane, puis deux moulins
for _l in range(4):
    _y = 2100 + _l * 320
    if _l % 2 == 0:
        _segment(X0, _y, X0 + 680, _y + 160)
    else:
        _segment(X1, _y, X1 - 680, _y + 160)
_rotor(340, 3700, 220, 4, 2.5)
_rotor(740, 3700, 220, 4, -2.5)

#  D. l'entonnoir qui amène au sas
_segment(X0, 4180, SAS_G, SAS_Y)
_segment(X1, 4180, SAS_D, SAS_Y)

#  E. la ligne droite finale : mille sept cents pixels, clous serrés
for _l in range(8):
    _rangee(_l, 4820 + _l * 150, (X1 - X0) / 10, 11)
#  Le goulet final. Il ne fait que cent quarante pixels — deux balles et demie
#  de large — parce que c'est le dernier endroit où la course peut encore
#  changer de mains : quatre balles y arrivent groupées, et il n'en passe
#  qu'une à la fois.
GOULET_G, GOULET_D = 470, 610
_segment(X0, 6000, GOULET_G, 6160)
_segment(X1, 6000, GOULET_D, 6160)


def projete(px, py, x1, y1, x2, y2):
    """Point du segment le plus proche d'un point donné."""
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy or 1.0
    t = min(1.0, max(0.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return x1 + t * dx, y1 + t * dy


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    #  L'ordre des couloirs est tiré au sort : sur un parcours fixe, la
    #  position de départ compte, et il ne faut pas qu'elle avantage toujours
    #  la même.
    rangs = rng.permutation(N)
    balles = [{"i": i, "arrive": 0, "rang": 0,
               "x": X0 + (rangs[i] + 0.5) * (X1 - X0) / N,
               "y": float(DEPART), "vx": rng.uniform(-20, 20), "vy": 0.0,
               "yjalon": float(DEPART), "tjalon": 0.0}
              for i in range(N)]
    phases = [rng.uniform(0, TAU) for _ in ROTORS]

    t = 0.0
    camera = 0.0
    images, chocs = [], []
    classement = []
    prochaine = 0.0
    fin = None
    sas_file, sas_depuis, sas_jusqua = 0, -1.0, -1.0

    def heurter(b, qx, qy, ep, rebond, vsx, vsy):
        dx, dy = b["x"] - qx, b["y"] - qy
        dd = np.sqrt(dx * dx + dy * dy)
        mini = R_BALLE + ep
        if dd >= mini:
            return False
        nx, ny = (dx / dd, dy / dd) if dd > 1e-9 else (0.0, -1.0)
        b["x"], b["y"] = qx + nx * mini, qy + ny * mini
        rvx, rvy = b["vx"] - vsx, b["vy"] - vsy
        vn = rvx * nx + rvy * ny
        if vn >= 0:
            return False
        b["vx"] = vsx + rvx - (1 + rebond) * vn * nx
        b["vy"] = vsy + rvy - (1 + rebond) * vn * ny
        return True

    def instantane():
        #  L'état du sas est enregistré avec le reste : « prête » vaut 1 quand
        #  l'ouverture est acquise, et c'est ce que le rendu affiche.
        prete = 0.0 if sas_depuis < 0 else (t - sas_depuis) / SAS_DELAI
        prete = min(1.0, max(prete, sas_file / SAS_QUORUM))
        return (tuple((b["x"], b["y"], b["arrive"], b["rang"]) for b in balles),
                camera, tuple(phases), t <= sas_jusqua, prete, t)

    while fin is None and t < 150.0:
        t += DT
        g = G0 + G_MONTE * t
        for k, r in enumerate(ROTORS):
            phases[k] += r["omega"] * DT
        batt = battants(t)

        sas_file = sum(1 for b in balles if not b["arrive"]
                       and SAS_Y - 300 < b["y"] < SAS_Y + 40)
        if t > sas_jusqua:
            if sas_file == 0:
                sas_depuis = -1.0
            else:
                if sas_depuis < 0:
                    sas_depuis = t
                if sas_file >= SAS_QUORUM or t - sas_depuis > SAS_DELAI:
                    sas_jusqua = t + SAS_OUVERT
                    sas_depuis = -1.0
                    chocs.append((t, (SAS_G + SAS_D) / 2, 0, 2))
        trappe = t > sas_jusqua

        for b in balles:
            if b["arrive"]:
                continue
            lent = b["y"] > SAS_Y
            b["vy"] += g * (RALENTI if lent else 1.0) * DT
            b["vx"] *= FROTTE_X
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            vmax = V_MAX * RALENTI_V if lent else V_MAX
            s = np.sqrt(b["vx"] ** 2 + b["vy"] ** 2)
            if s > vmax:
                b["vx"] *= vmax / s
                b["vy"] *= vmax / s
            if b["x"] < X0 + R_BALLE:
                b["x"] = X0 + R_BALLE
                b["vx"] = abs(b["vx"]) * REBOND
            if b["x"] > X1 - R_BALLE:
                b["x"] = X1 - R_BALLE
                b["vx"] = -abs(b["vx"]) * REBOND

            #  On ne teste que ce qui est dans la bande utile : le parcours
            #  fait six mille pixels de long.
            for cx, cy, cr in CLOUS:
                if abs(cy - b["y"]) > 90:
                    continue
                if heurter(b, cx, cy, cr, REBOND, 0.0, 0.0):
                    chocs.append((t, cx, b["i"], 0))
            for x1, y1, x2, y2, ep in SEGMENTS:
                if b["y"] < min(y1, y2) - 120 or b["y"] > max(y1, y2) + 120:
                    continue
                qx, qy = projete(b["x"], b["y"], x1, y1, x2, y2)
                heurter(b, qx, qy, ep, REBOND, 0.0, 0.0)

            #  La herse. Les battants glissent : au choc, leur vitesse propre
            #  pousse la balle sur le côté.
            if HERSE_Y - HERSE_PENTE - 160 < b["y"] < HERSE_Y + 160:
                vgliss = (herse_x(t + 0.01) - herse_x(t)) / 0.01
                for x1, y1, x2, y2 in batt:
                    if x2 <= x1:
                        continue
                    qx, qy = projete(b["x"], b["y"], x1, y1, x2, y2)
                    if heurter(b, qx, qy, HERSE_EP, REBOND, vgliss * 0.35, 0.0):
                        chocs.append((t, qx, b["i"], 1))

            #  Le sas : la trappe n'existe qu'entre deux ouvertures.
            if trappe and b["y"] < SAS_Y and abs(b["y"] - SAS_Y) < 140:
                qx, qy = projete(b["x"], b["y"], SAS_G, SAS_Y, SAS_D, SAS_Y)
                heurter(b, qx, qy, 14, 0.28, 0.0, 0.0)

            for k, r in enumerate(ROTORS):
                if abs(r["y"] - b["y"]) > r["longueur"] + 120:
                    continue
                for p in range(r["pales"]):
                    a = phases[k] + p * TAU / r["pales"]
                    ex = r["x"] + np.cos(a) * r["longueur"]
                    ey = r["y"] + np.sin(a) * r["longueur"]
                    qx, qy = projete(b["x"], b["y"], r["x"], r["y"], ex, ey)
                    #  Vitesse du point de contact : ω ∧ r. C'est elle qui
                    #  propulse ; sans elle une pale balaie la balle sans effet.
                    rx, ry = qx - r["x"], qy - r["y"]
                    if heurter(b, qx, qy, r["ep"], REBOND_PALE,
                               -r["omega"] * ry, r["omega"] * rx):
                        chocs.append((t, qx, b["i"], 1))

            #  Garde-fou. Les pièges connus sont bouchés, mais il suffit d'une
            #  balle immobilisée quelque part pour qu'une course ne se termine
            #  jamais : on secoue celle qui n'a pas gagné vingt-cinq pixels
            #  depuis un moment. On est plus patient devant la herse et devant
            #  le sas, où l'attente fait partie du jeu — sans quoi le garde-fou
            #  éjecterait de la file une balle qui attend simplement son tour.
            attente = (HERSE_Y - HERSE_PENTE - 200 < b["y"] < HERSE_Y
                       or SAS_Y - 300 < b["y"] < SAS_Y)
            if b["y"] > b["yjalon"] + 25:
                b["yjalon"], b["tjalon"] = b["y"], t
            elif t - b["tjalon"] > (8.0 if attente else 3.5):
                b["vx"] += rng.choice((-1.0, 1.0)) * rng.uniform(160, 300)
                b["vy"] -= 130
                b["yjalon"], b["tjalon"] = b["y"], t

            if b["y"] >= ARRIVEE:
                b["arrive"] = 1
                classement.append(b["i"])
                b["rang"] = len(classement)
                #  On s'arrête au podium : la course est jouée, et regarder les
                #  deux dernières finir n'apprend plus rien.
                if len(classement) >= 3:
                    fin = t

        for i in range(N):
            a = balles[i]
            if a["arrive"]:
                continue
            for j in range(i + 1, N):
                b = balles[j]
                if b["arrive"]:
                    continue
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                dd = np.sqrt(dx * dx + dy * dy)
                if dd >= 2 * R_BALLE or dd < 1e-9:
                    continue
                nx, ny = dx / dd, dy / dd
                corr = (2 * R_BALLE - dd) / 2
                a["x"] -= nx * corr; a["y"] -= ny * corr
                b["x"] += nx * corr; b["y"] += ny * corr
                vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
                if vn < 0:
                    p = 0.9 * vn
                    a["vx"] += p * nx; a["vy"] += p * ny
                    b["vx"] -= p * nx; b["vy"] -= p * ny

        #  La caméra suit la tête de course et la rattrape doucement : un suivi
        #  rigide ferait sauter tout le décor à chaque rebond.
        tete = max(b["y"] for b in balles)
        vise = max(0.0, min(ARRIVEE + 200 - H, tete - H * CAM_ANCRE))
        camera += (vise - camera) * min(1.0, CAM_SUIVI * DT)

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = fin or t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, chocs, tuple(classement), fin, (classement[0] if classement
                                                   else 0)


IMAGES, CHOCS, CLASSEMENT, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


def monde(x, y, camera):
    """Un point du parcours, ramené dans le repère de la scène."""
    return vers_scene(x, y - camera)


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class DeuxEpreuves(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- le décor fixe, dessiné une fois et translaté ---------------------
        #  Cent cinquante clous et une quinzaine de parois : on les construit
        #  dans un seul groupe, et la caméra n'est qu'un décalage de ce groupe.
        #  Les replacer un par un à chaque image coûterait cent fois plus.
        statique = VGroup()
        for x1, y1, x2, y2, ep in SEGMENTS:
            statique.add(Line(monde(x1, y1, 0), monde(x2, y2, 0),
                              stroke_color="#8FA8BA",
                              stroke_width=2 * ep * ECHELLE * 130))
        for cx, cy, cr in CLOUS:
            statique.add(Dot(monde(cx, cy, 0), radius=cr * ECHELLE,
                             color="#546678"))
        for x in (X0, X1):
            statique.add(Line(monde(x, -200, 0), monde(x, ARRIVEE + 400, 0),
                              stroke_color="#6E8CA5", stroke_width=5,
                              stroke_opacity=0.26))
        statique.add(DashedLine(monde(X0, ARRIVEE, 0), monde(X1, ARRIVEE, 0),
                                dash_length=0.24, dashed_ratio=0.6,
                                stroke_color="#33FF99", stroke_width=8))
        statique.camera_posee = 0.0

        def maj_statique(g):
            _, camera, _, _, _, _ = instantane(t.get_value())
            g.shift(UP * (camera - g.camera_posee) * ECHELLE)
            g.camera_posee = camera

        statique.add_updater(maj_statique)

        # --- la herse ---------------------------------------------------------
        #  Deux battants et deux repères verts qui bornent la fenêtre : c'est le
        #  seul passage, il doit sauter aux yeux au milieu d'une barre qui
        #  occupe toute la largeur.
        herse_corps = VGroup(*[Line(ORIGIN, RIGHT, stroke_color="#B98CE0",
                                    stroke_width=26) for _ in range(2)])
        herse_bord = VGroup(*[Line(ORIGIN, RIGHT, stroke_color="#33FF99",
                                   stroke_width=6) for _ in range(2)])
        herse = VGroup(herse_corps, herse_bord)

        def maj_herse(_):
            _, camera, _, _, _, tt = instantane(t.get_value())
            for k, (x1, y1, x2, y2) in enumerate(battants(tt)):
                if x2 <= x1:
                    herse_corps[k].set_opacity(0)
                    continue
                herse_corps[k].set_opacity(1)
                herse_corps[k].put_start_and_end_on(monde(x1, y1, camera),
                                                    monde(x2, y2, camera))
            for k, dx in enumerate((-HERSE_LARG / 2, HERSE_LARG / 2)):
                x = herse_x(tt) + dx
                herse_bord[k].put_start_and_end_on(
                    monde(x, HERSE_Y - 30, camera),
                    monde(x, HERSE_Y + 38, camera))

        herse.add_updater(maj_herse)

        # --- le sas -----------------------------------------------------------
        #  La trappe passe du rouge au vert à mesure que l'ouverture s'acquiert.
        #  Sans ce signal, l'ouverture paraîtrait arbitraire.
        trappe = Line(ORIGIN, RIGHT, stroke_width=26)

        def maj_sas(_):
            _, camera, _, ouvert, prete, _ = instantane(t.get_value())
            trappe.put_start_and_end_on(monde(SAS_G, SAS_Y, camera),
                                        monde(SAS_D, SAS_Y, camera))
            if ouvert:
                trappe.set_stroke(color="#33FF99", width=8, opacity=0.85)
            else:
                trappe.set_stroke(
                    color=teinte(8 + 130 * prete ** 3, 0.44 + 0.18 * prete, 0.90),
                    width=26, opacity=1)

        trappe.add_updater(maj_sas)

        # --- les moulins ------------------------------------------------------
        pales = VGroup()
        for r in ROTORS:
            for _ in range(r["pales"]):
                pales.add(Line(ORIGIN, RIGHT, stroke_color="#F0B25E",
                               stroke_width=15))
        moyeux = VGroup(*[Dot(ORIGIN, radius=20 * ECHELLE, color="#2B3644")
                          for _ in ROTORS])

        def maj_rotors(_):
            _, camera, phases, _, _, _ = instantane(t.get_value())
            k = 0
            for m, (r, ph) in enumerate(zip(ROTORS, phases)):
                c = monde(r["x"], r["y"], camera)
                moyeux[m].move_to(c)
                for p in range(r["pales"]):
                    a = ph + p * TAU / r["pales"]
                    bout = monde(r["x"] + np.cos(a) * r["longueur"],
                                 r["y"] + np.sin(a) * r["longueur"], camera)
                    pales[k].put_start_and_end_on(c, bout)
                    k += 1

        pales.add_updater(maj_rotors)

        # --- les balles -------------------------------------------------------
        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(N)])

        def maj_balles(_):
            etats, camera, _, _, _, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                x, y, arrive, _r = etats[i]
                b.move_to(monde(x, y, camera))
                b.set_opacity(0 if arrive else 1)

        balles.add_updater(maj_balles)

        # --- le masque du haut ------------------------------------------------
        #  Manim n'a pas de découpage : on pose un bandeau opaque sur la zone du
        #  tableau de bord, entre le monde et lui.
        masque = Rectangle(width=config.frame_width, height=6,
                           stroke_width=0, fill_color="#04060A", fill_opacity=1)
        masque.move_to(vers_scene(W / 2, VUE_HAUT) + UP * 3)
        liseré = Line(vers_scene(0, VUE_HAUT), vers_scene(W, VUE_HAUT),
                      stroke_color="#7896AF", stroke_width=3, stroke_opacity=0.22)

        # --- l'en-tête ---------------------------------------------------------
        #  Une question, en grand, et rien d'autre. Ce que l'en-tête perd en
        #  information, le parcours le gagne en hauteur.
        #  Les deux lignes forment un seul Text : mises à l'échelle séparément
        #  elles n'auraient pas le même corps, « qui finira première » ayant des
        #  jambages et pas « choisis la couleur » — à hauteur égale, ses
        #  majuscules seraient plus petites.
        entete = Text("choisis la couleur" "\n" "qui finira première",
                      weight=BOLD, color="#EBF4F8", line_spacing=0.75)
        entete.scale_to_fit_width(6.6).move_to(vers_scene(W / 2, 128))

        # --- bandeau de fin ---------------------------------------------------
        voile = Rectangle(width=config.frame_width, height=config.frame_height,
                          stroke_width=0, fill_color="#04060A", fill_opacity=0)
        podium = VGroup(
            Text("vainqueur", color="#C8D7DC").scale_to_fit_height(0.28),
            Text(NOMS[VAINQUEUR], weight=BOLD,
                 color=teinte(TEINTES[VAINQUEUR], 0.64)).scale_to_fit_height(0.78),
            *[Text("%s   %s" % (("1er", "2e", "3e")[k], NOMS[i]),
                   weight=SEMIBOLD, color=teinte(TEINTES[i], 0.62)
                   ).scale_to_fit_height(0.30)
              for k, i in enumerate(CLASSEMENT[:3])],
        ).arrange(DOWN, buff=0.34).move_to(vers_scene(W / 2, H / 2))
        podium.set_opacity(0)

        def maj_fin(_):
            v = float(np.clip((t.get_value() - FIN) / 0.4, 0, 1))
            voile.set_fill(opacity=0.72 * v)
            for m in podium:
                m.set_opacity(v)

        voile.add_updater(maj_fin)

        self.add(statique, herse, trappe, pales, moyeux, balles, masque, liseré,
                 entete, voile, podium)

        if AVEC_SON:
            gamme = (0, 3, 7, 10, 12)
            ev = []
            for k, (instant, x, i, genre) in enumerate(CHOCS):
                pan = (x - W / 2) / (W / 2)
                if genre == 2:                      # l'ouverture du sas
                    ev.append((instant, "souffle", 260, 0.0, 0.5))
                elif genre == 1:                    # pale ou battant
                    ev.append((instant, "cloche", 19 + (5 if i % 2 else 0),
                               pan, 0.19))
                elif k % 3 == 0:                    # un clou sur trois
                    ev.append((instant, "cloche",
                               gamme[int(x) % 5] + (12 if i % 2 else 0),
                               pan, 0.12))
            ev += accord_victoire(FIN + 0.15, VAINQUEUR % 2 == 1)
            self.add_sound(bande_son(ev, DUREE, "deux_epreuves.wav"))

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
        DeuxEpreuves().render()
