"""
La balle et les pointes — reproduction Manim, 30 secondes.

Une balle rebondit dans un cercle ; chaque contact avec le bord joue la note
suivante d'une mélodie, donc le rythme de la musique est celui de la physique.
Trois pointes tournent sur le bord : les toucher fait éclater la balle en une
cinquantaine de billes, qui retombent et s'agitent sans fin au fond.

Rendu (format vertical, YouTube Shorts / TikTok) :
    manim -r 1080,1920 --fps 60 balle_et_pointes.py BalleEtPointes

Les réglages viennent de mesures faites sur une vidéo de référence, ramenées
d'un cadre de 576 x 1024 à celui-ci : trois pointes espacées de 120° tournant à
−52 °/s, teinte du bord égale à l'angle, rebonds élastiques à vitesse à peu près
constante, une bille de 16 px pour un rayon de 274.

La mélodie est écrite pour ce film — celle de la vidéo de référence est un
morceau du commerce, qu'on ne peut ni extraire ni rediffuser.
"""

from manim import *
import colorsys
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#      manim -r 1080,1920 --fps 60 balle_et_pointes.py BalleEtPointes
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#000000"

# --------------------------------------------------------------------------
#  Réglages, dans le repère pixel de la page voisine (1080 x 1920)
# --------------------------------------------------------------------------
W, H = 1080, 1920
CX, CY, R = 540, 976, 514
R_BALLE = 30
G = 1350.0                  # gravité, px/s²
V0 = 1120.0                 # vitesse de la balle, px/s
DT = 1 / 480                # pas de simulation, fixe
DUREE = 30.0
FPS_ECH = 60                # un instantané par image de la vidéo

N_POINTES = 3
DEMI_POINTE = 4.6 * DEGREES
HAUT_POINTE = 46
ROTATION = -52 * DEGREES    # rad/s

#  Bien moins de billes que sur la page : Manim dessine du vectoriel, et il faut
#  que le rendu reste faisable. Le tas se lit tout aussi bien.
N_ECLATS = 55
MAX_ECLATS = 460
SEAUX = 6                   # les billes sont groupées par teinte

#  Les billes ne s'endorment jamais : mesuré sur la vidéo de référence, la
#  moitié des pixels du tas change d'une image à la suivante. Il faut donc de
#  vraies collisions entre elles. Elles avancent à pas plus grossier que la
#  balle principale, qui a besoin d'un pas fin pour que l'instant du rebond —
#  donc la note — tombe juste.
DT_BILLES = 1 / 240
REBOND_BORD = 0.74
REBOND_BILLE = 0.70
FROTTEMENT = 0.9997
CASE = 44

MELODIE = [0, 3, 5, 7, 10, 7, 5, 3,
           0, 3, 5, 10, 12, 10, 7, 5,
           0, -2, 3, 5, 7, 12, 10, 7,
           5, 3, 0, 3, 7, 10, 12, 15]
LA = 220.0

AVEC_SON = True

ECHELLE = 9.0 / W           # un pixel vaut cela en unités de scène
K_ARC = 4 / 3 * np.tan(np.pi / 8)    # bras de commande d'un quart de cercle


def vers_scene(x, y):
    return np.array([(x - W / 2) * ECHELLE, (H / 2 - y) * ECHELLE, 0.0])


def teinte(h, l=0.60, s=1.0):
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))


# --------------------------------------------------------------------------
#  Simulation : on joue toute la partie d'avance, puis on relit. Un tirage
#  ensemencé, donc deux rendus donnent exactement le même film.
# --------------------------------------------------------------------------
def simuler():
    """Renvoie (images, rebonds, eclatements).

    images : un instantané par image de vidéo —
             (position de la balle, teinte, angle des pointes, billes)
    billes : tableau (n, 4) de x, y, rayon, teinte
    """
    rng = np.random.default_rng(4)
    bx, by = CX, CY - R * 0.45
    vx, vy = np.cos(0.6) * V0, np.sin(0.6) * V0
    h_balle = 150.0
    t = 0.0
    eclats = []                     # dictionnaires : x, y, vx, vy, r, h, dort
    images, rebonds, eclatements = [], [], []
    note = 0
    prochaine = 0.0

    reste_billes = 0.0

    def sur_pointe(angle):
        for i in range(N_POINTES):
            a = ROTATION * t + i * TAU / N_POINTES
            d = (angle - a) % TAU
            if d > np.pi:
                d -= TAU
            if abs(d) < DEMI_POINTE:
                return True
        return False

    while t < DUREE:
        # --- la balle ---------------------------------------------------
        vy += G * DT
        bx += vx * DT
        by += vy * DT
        t += DT

        dx, dy = bx - CX, by - CY
        d = np.sqrt(dx * dx + dy * dy)
        if d > R - R_BALLE:
            nx, ny = dx / d, dy / d
            angle = np.arctan2(-ny, nx)
            if sur_pointe(angle):
                eclatements.append((t, bx, by, h_balle))
                for _ in range(N_ECLATS):
                    a = rng.uniform(0, TAU)
                    v = rng.uniform(250, 1150)
                    eclats.append({"x": bx, "y": by,
                                   "vx": np.cos(a) * v, "vy": np.sin(a) * v,
                                   "r": rng.uniform(5, 12),
                                   "h": (h_balle + rng.uniform(-80, 80)) % 360})
                if len(eclats) > MAX_ECLATS:
                    eclats = eclats[-MAX_ECLATS:]
                h_balle = (h_balle + 47) % 360
                bx, by = CX, CY - R * 0.45
                a = rng.uniform(0, TAU)
                vx, vy = np.cos(a) * V0, np.sin(a) * V0
            else:
                bx, by = CX + nx * (R - R_BALLE), CY + ny * (R - R_BALLE)
                p = 2 * (vx * nx + vy * ny)
                vx -= p * nx
                vy -= p * ny
                #  Vitesse maintenue : sans cela la balle se traîne au fond et
                #  la mélodie s'éteint avec elle.
                s = np.sqrt(vx * vx + vy * vy)
                vx *= V0 / s
                vy *= V0 / s
                rebonds.append((t, bx, by, MELODIE[note % len(MELODIE)],
                                np.degrees(angle) % 360))
                note += 1

        # --- les billes -------------------------------------------------
        reste_billes += DT
        while reste_billes >= DT_BILLES:
            reste_billes -= DT_BILLES
            h = DT_BILLES
            cases = {}
            for i, e in enumerate(eclats):
                e["vy"] += G * h
                e["vx"] *= FROTTEMENT
                e["vy"] *= FROTTEMENT
                e["x"] += e["vx"] * h
                e["y"] += e["vy"] * h
                ex, ey = e["x"] - CX, e["y"] - CY
                de = np.sqrt(ex * ex + ey * ey)
                if de > R - e["r"]:
                    nx, ny = ex / de, ey / de
                    e["x"], e["y"] = CX + nx * (R - e["r"]), CY + ny * (R - e["r"])
                    p = (1 + REBOND_BORD) * (e["vx"] * nx + e["vy"] * ny)
                    e["vx"] -= p * nx
                    e["vy"] -= p * ny
                cases.setdefault((int(e["x"] // CASE), int(e["y"] // CASE)), []).append(i)

            #  Contacts entre billes. Chaque paire n'est examinée qu'une fois :
            #  seules les cases suivantes sont visitées, et dans la case
            #  courante seuls les indices supérieurs.
            for (gx, gy), ici in cases.items():
                for ax, ay in ((0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
                    la = cases.get((gx + ax, gy + ay))
                    if not la:
                        continue
                    meme = ax == 0 and ay == 0
                    for m, ia in enumerate(ici):
                        for ib in (la[m + 1:] if meme else la):
                            a, b = eclats[ia], eclats[ib]
                            dx2, dy2 = b["x"] - a["x"], b["y"] - a["y"]
                            dd = np.sqrt(dx2 * dx2 + dy2 * dy2)
                            mini = a["r"] + b["r"]
                            if dd >= mini or dd < 1e-9:
                                continue
                            nx, ny = dx2 / dd, dy2 / dd
                            corr = (mini - dd) / 2
                            a["x"] -= nx * corr; a["y"] -= ny * corr
                            b["x"] += nx * corr; b["y"] += ny * corr
                            vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
                            if vn > 0:
                                continue
                            j = -(1 + REBOND_BILLE) * vn / 2
                            a["vx"] -= j * nx; a["vy"] -= j * ny
                            b["vx"] += j * nx; b["vy"] += j * ny

            #  Une bille poussée par ses voisines peut passer le bord : on la
            #  ramène dedans en fin de pas, et on annule sa vitesse sortante.
            for e in eclats:
                ex, ey = e["x"] - CX, e["y"] - CY
                de = np.sqrt(ex * ex + ey * ey)
                if de > R - e["r"]:
                    nx, ny = ex / de, ey / de
                    e["x"], e["y"] = CX + nx * (R - e["r"]), CY + ny * (R - e["r"])
                    sortant = e["vx"] * nx + e["vy"] * ny
                    if sortant > 0:
                        e["vx"] -= sortant * nx
                        e["vy"] -= sortant * ny

        # --- instantané -------------------------------------------------
        if t >= prochaine:
            billes = np.array([[e["x"], e["y"], e["r"], e["h"]] for e in eclats],
                              dtype=float).reshape(-1, 4)
            images.append(((bx, by), h_balle, ROTATION * t, billes))
            prochaine += 1 / FPS_ECH

    return images, rebonds, eclatements


IMAGES, REBONDS, ECLATEMENTS = simuler()


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


def disques(billes):
    """Un tableau de points dessinant tous ces disques en un seul objet.

    Chaque cercle tient en quatre cubiques ; deux cercles voisins ne se
    touchant pas, Manim les sépare de lui-même en sous-chemins distincts.
    """
    n = len(billes)
    if n == 0:
        return np.zeros((0, 3))
    pts = np.empty((16 * n, 3))
    for i, (x, y, r, _) in enumerate(billes):
        c = vers_scene(x, y)
        rr = r * ECHELLE
        k = K_ARC * rr
        coins = [(rr, 0.0), (0.0, rr), (-rr, 0.0), (0.0, -rr)]
        tang = [(0.0, k), (-k, 0.0), (0.0, -k), (k, 0.0)]
        for j in range(4):
            p0, p3 = coins[j], coins[(j + 1) % 4]
            t0, t1 = tang[j], tang[(j + 1) % 4]
            b = 16 * i + 4 * j
            pts[b] = c + (p0[0], p0[1], 0)
            pts[b + 1] = c + (p0[0] + t0[0], p0[1] + t0[1], 0)
            pts[b + 2] = c + (p3[0] - t1[0], p3[1] - t1[1], 0)
            pts[b + 3] = c + (p3[0], p3[1], 0)
    return pts


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class BalleEtPointes(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- le bord, en arc-en-ciel : la teinte suit l'angle ---------------
        #  Cent vingt arcs fixes : ils ne changent jamais, donc autant les
        #  construire une fois pour toutes.
        bord = VGroup()
        for i in range(120):
            a0 = i * 3 * DEGREES
            bord.add(Arc(radius=R * ECHELLE, start_angle=a0,
                         angle=3.4 * DEGREES,
                         stroke_color=teinte(i * 3, 0.58),
                         stroke_width=6).shift(vers_scene(CX, CY)))

        # --- les pointes ----------------------------------------------------
        pointes = VGroup(*[
            Polygon(ORIGIN, ORIGIN, ORIGIN, fill_color=WHITE, fill_opacity=1,
                    stroke_width=0) for _ in range(N_POINTES)])

        def maj_pointes(g):
            base = instantane(t.get_value())[2]
            for i, tri in enumerate(g):
                a = base + i * TAU / N_POINTES
                def p(ang, ray):
                    return vers_scene(CX + ray * np.cos(ang), CY - ray * np.sin(ang))
                tri.set_points_as_corners([
                    p(a - DEMI_POINTE, R), p(a + DEMI_POINTE, R),
                    p(a, R - HAUT_POINTE), p(a - DEMI_POINTE, R)])

        pointes.add_updater(maj_pointes)

        # --- les billes, groupées par teinte --------------------------------
        seaux = VGroup(*[VMobject(stroke_width=0, fill_opacity=1)
                         for _ in range(SEAUX)])

        def maj_seaux(g):
            billes = instantane(t.get_value())[3]
            for i, seau in enumerate(g):
                if len(billes):
                    k = (billes[:, 3] // (360 / SEAUX)).astype(int) % SEAUX == i
                    lot = billes[k]
                else:
                    lot = billes
                seau.set_points(disques(lot))
                seau.set_fill(teinte((i + 0.5) * 360 / SEAUX, 0.56), opacity=1)

        seaux.add_updater(maj_seaux)

        # --- ondes de contact ------------------------------------------------
        ondes = VGroup()
        for instant, x, y, _, ang in REBONDS:
            o = Circle(radius=1.0, stroke_width=5, fill_opacity=0)
            o.move_to(vers_scene(x, y))

            def souffle(m, t0=instant, c=vers_scene(x, y), h=ang):
                age = t.get_value() - t0
                if age < 0 or age > 0.45:
                    m.set_stroke(opacity=0)
                    return
                v = 1 - age / 0.45
                m.width = 2 * (R_BALLE + 700 * age) * ECHELLE
                m.move_to(c)
                m.set_stroke(color=teinte(h, 0.66), opacity=0.5 * v,
                             width=2 + 6 * v)

            o.add_updater(souffle)
            ondes.add(o)

        # --- la balle --------------------------------------------------------
        balle = Circle(radius=R_BALLE * ECHELLE, stroke_color="#FFFFFF",
                       stroke_width=2, fill_opacity=1)
        halo = VGroup(*[Circle(radius=R_BALLE * ECHELLE * f, stroke_width=0,
                               fill_opacity=o) for f, o in ((1.7, 0.12), (2.4, 0.06))])

        def maj_balle(_):
            (bx, by), h, _, _ = instantane(t.get_value())
            c = vers_scene(bx, by)
            balle.move_to(c)
            balle.set_fill(teinte(h, 0.62))
            for anneau in halo:
                anneau.move_to(c)
                anneau.set_fill(teinte(h, 0.62))

        balle.add_updater(maj_balle)

        # --- textes -----------------------------------------------------------
        #  Deux lignes posées explicitement : une phrase longue laissée à
        #  scale_to_fit_width se replie toute seule, et mal alignée.
        titre = VGroup(*[
            Text(l, weight=BOLD, color="#F0F8FC").scale_to_fit_height(0.40)
            for l in ("la balle survivra-t-elle", "aux pointes ?")
        ]).arrange(DOWN, buff=0.16)
        titre.move_to(vers_scene(CX, 250))

        def compteurs(n, e):
            m = Text(f"{n} notes   ·   {e} éclatements", color="#BECDD2")
            m.scale_to_fit_height(0.30)
            return m.move_to(vers_scene(CX, H - 200))

        compte = compteurs(0, 0)
        compte.affiche = None

        def maj_compte(m):
            u = t.get_value()
            n = sum(1 for r in REBONDS if r[0] <= u)
            e = sum(1 for x in ECLATEMENTS if x[0] <= u)
            if (n, e) != m.affiche:
                m.become(compteurs(n, e))
                m.affiche = (n, e)

        compte.add_updater(maj_compte)

        self.add(bord, pointes, seaux, ondes, halo, balle, titre, compte)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par rebond, un fracas par pointe touchée. Écrite ici,
#  rien d'emprunté.
# --------------------------------------------------------------------------
def generer_bande_son(chemin="rebonds.wav", sr=44100):
    import wave

    n = int((DUREE + 2.0) * sr)
    gauche, droite = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(9)

    def poser(debut, onde, pan=0.0):
        i0 = max(0, int(debut * sr))
        fin = min(i0 + len(onde), n)
        if fin > i0:
            g = np.clip(0.5 * (1 - pan), 0, 1)
            gauche[i0:fin] += g * onde[: fin - i0]
            droite[i0:fin] += (1 - g) * onde[: fin - i0]

    def cloche(demi, duree=1.1, force=0.34):
        f = LA * 2 ** (demi / 12)
        d = int(duree * sr)
        tt = np.arange(d) / sr
        env = np.exp(-tt * 3.6) * (1 - np.exp(-tt / 0.003))
        return force * env * (np.sin(TAU * f * tt)
                              + 0.32 * np.sin(TAU * 2 * f * 1.002 * tt)
                              + 0.12 * np.sin(TAU * 3 * f * tt))

    for instant, x, _, demi, _ in REBONDS:
        poser(instant, cloche(demi), pan=(x - CX) / R)

    for instant, x, _, _ in ECLATEMENTS:
        pan = (x - CX) / R
        for j, demi in enumerate((12, 15, 19, 22, 24)):
            poser(instant + j * 0.018, cloche(demi, 1.6, 0.16), pan)
        d = int(0.5 * sr)
        tt = np.arange(d) / sr
        souffle = rng.normal(0, 1, d) * (1 - tt / tt[-1]) ** 3 * 0.20
        poser(instant, souffle, pan)

    stereo = np.stack([np.tanh(gauche * 1.1), np.tanh(droite * 1.1)], axis=1)
    pcm = (stereo / max(1e-9, np.abs(stereo).max()) * 0.92 * 32767).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Lancement direct : python balle_et_pointes.py
    config.pixel_width, config.pixel_height = 1080, 1920
    config.frame_rate = 60
    BalleEtPointes().render()
