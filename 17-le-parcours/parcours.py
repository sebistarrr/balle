"""
Le parcours — reproduction Manim du duel, format vertical.

Cinq balles, un parcours de sept mille pixels — huit fois la hauteur de
l'écran. Champ de clous, barres tournantes, entonnoir, chicane, moulins, ligne
droite finale. La première en bas gagne, et la caméra suit la tête de course.

Tout obstacle est une capsule — un segment doté d'une épaisseur — ou un disque :
une seule primitive de contact suffit pour tout le parcours. Les pales des
moulins ont en plus une vitesse propre au point de contact, et c'est elle qui
propulse — ou qui renvoie en arrière.

Rendu :
    manim -r 1080,1920 --fps 60 parcours.py LeParcours

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python parcours.py --graines` en essaie une série et affiche, pour chacune, la
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
ARRIVEE = 7600              # longueur du parcours, en px de monde
R_BALLE = 24
G0 = 900.0
G_MONTE = 22.0
REBOND = 0.52
REBOND_PALE = 0.75
V_MAX = 1450.0
FROTTE_X = 0.9993
DT = 1 / 480

CAM_ANCRE = 0.38
CAM_SUIVI = 6.0
#  Le monde est masqué au-dessus de cette hauteur : au-dessus il n'y a que le
#  titre et le classement. Sans ce masque, une pale de moulin ou une balle
#  distancée vient se dessiner par-dessus le tableau de bord.
VUE_HAUT = 450

NOMS = ("ROUGE", "AMBRE", "LIME", "CYAN", "VIOLET")
TEINTES = (354.0, 38.0, 104.0, 190.0, 280.0)
N = len(NOMS)

#  Graine 4 : 34,4 s, VIOLET franchit la ligne 1,2 % devant ROUGE — l'arrivée
#  la plus serrée des onze essayées.
GRAINE = 4

# --------------------------------------------------------------------------
#  Le parcours. Tout obstacle est une capsule — un segment doté d'une
#  épaisseur — ou un disque : une seule primitive de contact suffit donc pour
#  les clous, les parois inclinées, l'entonnoir, les barres et les moulins.
# --------------------------------------------------------------------------
CLOUS, SEGMENTS, ROTORS = [], [], []


def _clou(x, y, r=13):
    CLOUS.append((x, y, r))


def _segment(x1, y1, x2, y2, ep=11):
    SEGMENTS.append((x1, y1, x2, y2, ep))


def _rotor(x, y, longueur, pales, omega, ep=13):
    ROTORS.append({"x": x, "y": y, "longueur": longueur, "pales": pales,
                   "omega": omega, "ep": ep})


#  A. le champ de clous, pour disperser le peloton d'entrée
for _l in range(6):
    _y = 420 + _l * 190
    _p = (X1 - X0) / 9
    if _l % 2 == 0:
        for _k in range(9):
            _clou(X0 + (_k + 0.5) * _p, _y)
    else:
        for _k in range(1, 9):
            _clou(X0 + _k * _p, _y)

#  B. trois barres tournantes
_rotor(540, 1780, 300, 2, 1.7)
_rotor(540, 2200, 300, 2, -2.1)
_rotor(540, 2620, 300, 2, 1.4)

#  C. l'entonnoir : deux parois qui se referment sur un goulet
_segment(X0, 2980, 430, 3380)
_segment(X1, 2980, 650, 3380)
_segment(430, 3380, 430, 3480)
_segment(650, 3380, 650, 3480)

#  D. la chicane : des plans inclinés en quinconce
for _l in range(5):
    _y = 3760 + _l * 300
    if _l % 2 == 0:
        _segment(X0, _y, X0 + 660, _y + 150)
    else:
        _segment(X1, _y, X1 - 660, _y + 150)

#  E. les moulins, qui renvoient en arrière autant qu'ils propulsent
_rotor(350, 5560, 230, 4, 2.4)
_rotor(730, 5560, 230, 4, -2.4)
_rotor(540, 5980, 250, 3, 1.9)

#  F. la dernière ligne : clous serrés, puis l'arrivée
for _l in range(6):
    _y = 6320 + _l * 165
    _p = (X1 - X0) / 13
    if _l % 2 == 0:
        for _k in range(13):
            _clou(X0 + (_k + 0.5) * _p, _y, 11)
    else:
        for _k in range(1, 13):
            _clou(X0 + _k * _p, _y, 11)
_segment(X0, 7380, 430, 7500)
_segment(X1, 7380, 650, 7500)


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
    #  L'ordre des couloirs est tiré au sort : sur un parcours fixe, la position
    #  de départ compte, et il ne faut pas qu'elle avantage toujours la même.
    rangs = rng.permutation(N)
    balles = [{"i": i, "arrive": 0, "rang": 0,
               "x": X0 + (rangs[i] + 0.5) * (X1 - X0) / N,
               "y": float(DEPART), "vx": rng.uniform(-20, 20), "vy": 0.0}
              for i in range(N)]
    phases = [rng.uniform(0, TAU) for _ in ROTORS]

    t = 0.0
    camera = 0.0
    images, chocs = [], []
    classement = []
    prochaine = 0.0
    fin = None

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
        return (tuple((b["x"], b["y"], b["arrive"], b["rang"]) for b in balles),
                camera, tuple(phases))

    while fin is None and t < 150.0:
        t += DT
        g = G0 + G_MONTE * t
        for k, r in enumerate(ROTORS):
            phases[k] += r["omega"] * DT

        for b in balles:
            if b["arrive"]:
                continue
            b["vy"] += g * DT
            b["vx"] *= FROTTE_X
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            s = np.sqrt(b["vx"] ** 2 + b["vy"] ** 2)
            if s > V_MAX:
                b["vx"] *= V_MAX / s
                b["vy"] *= V_MAX / s
            if b["x"] < X0 + R_BALLE:
                b["x"] = X0 + R_BALLE
                b["vx"] = abs(b["vx"]) * REBOND
            if b["x"] > X1 - R_BALLE:
                b["x"] = X1 - R_BALLE
                b["vx"] = -abs(b["vx"]) * REBOND

            #  On ne teste que ce qui est dans la bande utile : le parcours
            #  fait sept mille pixels de long.
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
    return images, chocs, tuple(classement), fin, (classement[0] if classement else 0)


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
class LeParcours(Scene):
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
        arrivee = DashedLine(monde(X0, ARRIVEE, 0), monde(X1, ARRIVEE, 0),
                             dash_length=0.24, dashed_ratio=0.6,
                             stroke_color="#33FF99", stroke_width=8)
        statique.add(arrivee)
        statique.camera_posee = 0.0

        def maj_statique(g):
            _, camera, _ = instantane(t.get_value())
            g.shift(UP * (camera - g.camera_posee) * ECHELLE)
            g.camera_posee = camera

        statique.add_updater(maj_statique)

        # --- les moulins ------------------------------------------------------
        pales = VGroup()
        for r in ROTORS:
            for _ in range(r["pales"]):
                pales.add(Line(ORIGIN, RIGHT, stroke_color="#F0B25E",
                               stroke_width=15))
        moyeux = VGroup(*[Dot(ORIGIN, radius=20 * ECHELLE, color="#2B3644")
                          for _ in ROTORS])

        def maj_rotors(_):
            _, camera, phases = instantane(t.get_value())
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
            etats, camera, _ = instantane(t.get_value())
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

        # --- le tableau de bord : cinq lignes, dans l'ordre de la course -------
        lignes = []
        for k in range(N):
            y = 150 + k * 62
            rang = Text("1", weight=BOLD, color="#96AAB4").scale_to_fit_height(0.20)
            rang.move_to(vers_scene(76, y), aligned_edge=LEFT)
            nom = Text(NOMS[0], weight=BOLD).scale_to_fit_height(0.20)
            nom.move_to(vers_scene(116, y), aligned_edge=LEFT)
            fond_b = RoundedRectangle(width=560 * ECHELLE, height=22 * ECHELLE,
                                      corner_radius=11 * ECHELLE, stroke_width=0,
                                      fill_color="#FFFFFF", fill_opacity=0.07)
            fond_b.move_to(vers_scene(330 + 280, y))
            plein = RoundedRectangle(width=22 * ECHELLE, height=22 * ECHELLE,
                                     corner_radius=11 * ECHELLE, stroke_width=0,
                                     fill_opacity=1)
            lignes.append({"rang": rang, "nom": nom, "fond": fond_b,
                           "plein": plein, "vu": None})

        tableau = VGroup(*[m for l in lignes
                           for m in (l["fond"], l["plein"], l["rang"], l["nom"])])

        def maj_tableau(_):
            etats, _, _ = instantane(t.get_value())
            #  L'ordre des lignes est déjà le classement : arrivées d'abord,
            #  puis les autres par distance parcourue.
            ordre = sorted(range(N),
                           key=lambda i: -(1e9 - etats[i][3] if etats[i][2]
                                           else etats[i][1]))
            for k, i in enumerate(ordre):
                l = lignes[k]
                y = 150 + k * 62
                part = float(np.clip((etats[i][1] - DEPART)
                                     / (ARRIVEE - DEPART), 0, 1))
                larg = max(22, 560 * part)
                l["plein"].become(RoundedRectangle(
                    width=larg * ECHELLE, height=22 * ECHELLE,
                    corner_radius=11 * ECHELLE, stroke_width=0,
                    fill_color=teinte(TEINTES[i], 0.56), fill_opacity=1))
                l["plein"].move_to(vers_scene(330 + larg / 2, y))
                #  Les textes ne sont refaits qu'au changement de place : en
                #  reconstruire dix à chaque image doublerait le temps de rendu.
                if l["vu"] != (k, i):
                    r = Text(str(k + 1), weight=BOLD,
                             color="#FFD65A" if k == 0 else "#96AAB4")
                    r.scale_to_fit_height(0.20)
                    r.move_to(vers_scene(76, y), aligned_edge=LEFT)
                    l["rang"].become(r)
                    m = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.64))
                    m.scale_to_fit_height(0.20)
                    m.move_to(vers_scene(116, y), aligned_edge=LEFT)
                    l["nom"].become(m)
                    l["vu"] = (k, i)

        tableau.add_updater(maj_tableau)

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

        self.add(statique, pales, moyeux, balles, masque, liseré,
                 accroche("qui franchira la ligne en premier ?"), tableau,
                 voile, podium)

        if AVEC_SON:
            gamme = (0, 3, 7, 10, 12)
            ev = []
            for k, (instant, x, i, pale) in enumerate(CHOCS):
                if not pale and k % 3:
                    continue
                pan = (x - W / 2) / (W / 2)
                if pale:
                    ev.append((instant, "cloche", 19 + (5 if i % 2 else 0),
                               pan, 0.19))
                else:
                    ev.append((instant, "cloche",
                               gamme[int(x) % 5] + (12 if i % 2 else 0),
                               pan, 0.12))
            ev += accord_victoire(FIN + 0.15, VAINQUEUR % 2 == 1)
            self.add_sound(bande_son(ev, DUREE, "parcours.wav"))

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
        LeParcours().render()
