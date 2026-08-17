"""
Cinq vies — reproduction Manim du duel, format vertical.

Deux balles dans une arène hérissée de pointes tournantes. Toucher une pointe
coûte une vie ; la balle réapparaît au centre, brièvement invulnérable. Cinq
vies chacune, la dernière debout gagne.

Rendu :
    manim -r 1080,1920 --fps 60 cinq_vies.py CinqVies

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python cinq_vies.py --graines` en essaie une série et affiche, pour chacune, la
durée et l'écart final, de quoi choisir un duel serré.
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

# --------------------------------------------------------------------------
#  Réglages, dans le repère pixel de la page voisine (1080 x 1920)
# --------------------------------------------------------------------------
W, H = 1080, 1920
CX, CY, R = 540, 1010, 452
R_BALLE = 27
V0 = 760.0                  # px/s, constante : pas de gravité
DT = 1 / 480
VIES = 5
INVULN = 0.8                # s d'invulnérabilité après une perte
FPS_ECH = 60
APRES = 3.0                 # s de bandeau « vainqueur » après le duel

#  Six pointes : trois dans un sens, trois dans l'autre. Deux sens de rotation
#  valent bien mieux qu'un — les intervalles sûrs se ferment et se rouvrent au
#  lieu de défiler régulièrement, et l'œil n'arrive pas à anticiper.
POINTES = ((3, -42 * DEGREES, 0.0), (3, +29 * DEGREES, PI / 3))
DEMI_POINTE0 = 4.2 * DEGREES
ELARGIT = 1.6 * DEGREES     # gagné par palier
PALIER = 6.0                # s entre deux élargissements
HAUT_POINTE = 52

NOMS = ("ROUGE", "CYAN")
TEINTES = (352.0, 186.0)

#  Graine 19 : 21,0 s, ROUGE l'emporte avec une seule vie — le duel le plus
#  serré des quarante essayés.
GRAINE = 19
AVEC_SON = True

ECHELLE = 9.0 / W
GAMME = (0, 3, 7, 10, 12)


def vers_scene(x, y):
    return np.array([(x - W / 2) * ECHELLE, (H / 2 - y) * ECHELLE, 0.0])


def teinte(h, l=0.60, s=1.0):
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))


def demi_pointe(t):
    return DEMI_POINTE0 + ELARGIT * int(t / PALIER)


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    """Renvoie (images, rebonds, pertes, fin, vainqueur).

    images : un instantané par image de vidéo — (t, [(x, y, invuln, vies)] , ...)
    rebonds : (instant, x, joueur, rang) — sert à la bande son
    pertes  : (instant, x, y, joueur)
    """
    rng = np.random.default_rng(graine)

    def lancer(b, ou, cap):
        b["x"] = CX + np.cos(ou) * 150
        b["y"] = CY + np.sin(ou) * 150
        b["vx"] = np.cos(cap) * V0
        b["vy"] = np.sin(cap) * V0
        b["invuln"] = INVULN

    balles = [{"i": i, "vies": VIES, "x": 0.0, "y": 0.0,
               "vx": 0.0, "vy": 0.0, "invuln": 0.0} for i in range(2)]
    #  Départ tiré au sort, les deux directions indépendantes. Avec un départ
    #  fixe, tout ce qui précède la première perte de vie est déterminé
    #  d'avance : c'est toujours la même balle qui encaisse en premier, et elle
    #  court après son retard tout le reste du duel.
    a0 = rng.uniform(0, TAU)
    lancer(balles[0], a0, rng.uniform(0, TAU))
    lancer(balles[1], a0 + PI, rng.uniform(0, TAU))

    t = 0.0
    images, rebonds, pertes = [], [], []
    prochaine = 0.0
    rang = 0
    vainqueur = -1

    def sur_pointe(angle):
        dp = demi_pointe(t)
        for n, vit, phase in POINTES:
            for i in range(n):
                a = phase + vit * t + i * TAU / n
                d = (angle - a) % TAU
                if d > PI:
                    d -= TAU
                if abs(d) < dp:
                    return True
        return False

    def instantane():
        return (t,
                tuple((b["x"], b["y"], b["invuln"], b["vies"]) for b in balles),
                demi_pointe(t))

    while vainqueur < 0 and t < 90.0:
        t += DT
        for b in balles:
            if b["vies"] <= 0:
                continue
            if b["invuln"] > 0:
                b["invuln"] -= DT
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            dx, dy = b["x"] - CX, b["y"] - CY
            d = np.sqrt(dx * dx + dy * dy)
            if d > R - R_BALLE:
                nx, ny = dx / d, dy / d
                angle = np.arctan2(-ny, nx)
                if b["invuln"] <= 0 and sur_pointe(angle):
                    b["vies"] -= 1
                    pertes.append((t, b["x"], b["y"], b["i"]))
                    if b["vies"] <= 0:
                        vainqueur = 1 - b["i"]
                        break
                    lancer(b, rng.uniform(0, TAU), rng.uniform(0, TAU))
                    continue
                b["x"], b["y"] = CX + nx * (R - R_BALLE), CY + ny * (R - R_BALLE)
                p = 2 * (b["vx"] * nx + b["vy"] * ny)
                b["vx"] -= p * nx
                b["vy"] -= p * ny
                s = np.sqrt(b["vx"] * b["vx"] + b["vy"] * b["vy"])
                b["vx"] *= V0 / s
                b["vy"] *= V0 / s
                rebonds.append((t, b["x"], b["i"], rang))
                rang += 1

        #  Choc entre les deux balles : elles se repoussent, ce qui les envoie
        #  vers le bord — donc vers les pointes. C'est le seul moment où l'une
        #  agit sur le sort de l'autre.
        a, b = balles
        if a["vies"] > 0 and b["vies"] > 0:
            dx, dy = b["x"] - a["x"], b["y"] - a["y"]
            dd = np.sqrt(dx * dx + dy * dy)
            if 1e-9 < dd < 2 * R_BALLE:
                nx, ny = dx / dd, dy / dd
                corr = (2 * R_BALLE - dd) / 2
                a["x"] -= nx * corr; a["y"] -= ny * corr
                b["x"] += nx * corr; b["y"] += ny * corr
                vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
                if vn < 0:
                    a["vx"] += vn * nx; a["vy"] += vn * ny
                    b["vx"] -= vn * nx; b["vy"] -= vn * ny
                    for m in balles:
                        s = np.sqrt(m["vx"] ** 2 + m["vy"] ** 2)
                        if s > 1e-9:
                            m["vx"] *= V0 / s
                            m["vy"] *= V0 / s
                    rebonds.append((t, (a["x"] + b["x"]) / 2, 0, rang))
                    rang += 1

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    #  On prolonge l'image finale pendant le bandeau : les updaters continuent
    #  de lire un instantané, il faut qu'il en existe un.
    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, rebonds, pertes, fin, vainqueur


IMAGES, REBONDS, PERTES, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class CinqVies(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        titre = Text("qui survivra ?", weight=SEMIBOLD, color="#EBF4F8")
        titre.scale_to_fit_height(0.30).move_to(vers_scene(CX, 96))

        # --- tableau de bord : noms et pastilles de vie ----------------------
        #  C'est la seule chose qu'on doit pouvoir lire d'un coup d'œil : en
        #  haut, grande, et à la même place du début à la fin.
        tableau = VGroup()
        pastilles = []
        for i in range(2):
            y = 190 + i * 96
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.62))
            nom.scale_to_fit_height(0.32)
            nom.move_to(vers_scene(96, y - 15), aligned_edge=LEFT)
            tableau.add(nom)
            rangee = []
            for k in range(VIES):
                c = Circle(radius=21 * ECHELLE, stroke_width=2, fill_opacity=1)
                c.move_to(vers_scene(700 + k * 62, y - 15))
                tableau.add(c)
                rangee.append(c)
            pastilles.append(rangee)

        def maj_tableau(_):
            _, etats, _ = instantane(t.get_value())
            for i, rangee in enumerate(pastilles):
                vies = etats[i][3]
                for k, c in enumerate(rangee):
                    if k < vies:
                        c.set_fill(teinte(TEINTES[i], 0.60), opacity=1)
                        c.set_stroke(teinte(TEINTES[i], 0.82), width=2, opacity=0.8)
                    else:
                        c.set_fill("#FFFFFF", opacity=0.10)
                        c.set_stroke(width=0)

        tableau.add_updater(maj_tableau)

        # --- l'arène ---------------------------------------------------------
        arene = Circle(radius=R * ECHELLE, stroke_color="#7896AA",
                       stroke_width=6, stroke_opacity=0.35, fill_opacity=0)
        arene.move_to(vers_scene(CX, CY))

        total = sum(n for n, _, _ in POINTES)
        pointes = VGroup(*[Polygon(ORIGIN, ORIGIN, ORIGIN, fill_color=WHITE,
                                   fill_opacity=1, stroke_width=0)
                           for _ in range(total)])

        def maj_pointes(g):
            u = t.get_value()
            _, _, dp = instantane(u)
            k = 0
            for n, vit, phase in POINTES:
                for i in range(n):
                    a = phase + vit * min(u, FIN) + i * TAU / n

                    def p(ang, ray):
                        return vers_scene(CX + ray * np.cos(ang),
                                          CY - ray * np.sin(ang))

                    g[k].set_points_as_corners([
                        p(a - dp, R + 4), p(a + dp, R + 4),
                        p(a, R - HAUT_POINTE), p(a - dp, R + 4)])
                    k += 1

        pointes.add_updater(maj_pointes)

        # --- les balles ------------------------------------------------------
        balles, halos = VGroup(), VGroup()
        for i in range(2):
            b = Circle(radius=R_BALLE * ECHELLE, stroke_color="#FFFFFF",
                       stroke_width=2.5, stroke_opacity=0.5,
                       fill_color=teinte(TEINTES[i], 0.62), fill_opacity=1)
            balles.add(b)
            halos.add(VGroup(*[
                Circle(radius=R_BALLE * f * ECHELLE, stroke_width=0,
                       fill_color=teinte(TEINTES[i], 0.58), fill_opacity=o)
                for f, o in ((1.7, 0.14), (2.6, 0.07))]))

        def maj_balles(_):
            _, etats, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                x, y, invuln, vies = etats[i]
                c = vers_scene(x, y)
                #  Une balle invulnérable clignote : sans cela on croit à un
                #  défaut quand elle traverse une pointe juste après une perte.
                visible = vies > 0 and not (invuln > 0 and int(invuln * 12) % 2)
                b.move_to(c).set_opacity(1 if visible else 0)
                for k, anne in enumerate(halos[i]):
                    anne.move_to(c)
                    anne.set_fill(opacity=(0.14, 0.07)[k] if visible else 0)

        balles.add_updater(maj_balles)

        # --- éclair rouge à chaque vie perdue --------------------------------
        eclair = Rectangle(width=config.frame_width, height=config.frame_height,
                           stroke_width=0, fill_color="#FF7878", fill_opacity=0)

        def maj_eclair(m):
            u = t.get_value()
            v = 0.0
            for instant, *_ in PERTES:
                age = u - instant
                if 0 <= age < 0.20:
                    v = max(v, (1 - age / 0.20) ** 2)
            m.set_fill(opacity=0.34 * v)

        eclair.add_updater(maj_eclair)

        # --- bandeau de fin ---------------------------------------------------
        gagnant = VAINQUEUR
        restantes = IMAGES[-1][1][gagnant][3]
        voile = Rectangle(width=config.frame_width, height=config.frame_height,
                          stroke_width=0, fill_color="#04060A", fill_opacity=0)
        bandeau = VGroup(
            Text("vainqueur", color="#C8D7DC").scale_to_fit_height(0.30),
            Text(NOMS[gagnant], weight=BOLD,
                 color=teinte(TEINTES[gagnant], 0.64)).scale_to_fit_height(0.85),
            Text("%d vie%s restante%s" % (restantes, "s" if restantes > 1 else "",
                                          "s" if restantes > 1 else ""),
                 color="#A0B4BE").scale_to_fit_height(0.27),
        ).arrange(DOWN, buff=0.30)
        bandeau.move_to(vers_scene(CX, CY))
        bandeau.set_opacity(0)

        def maj_fin(_):
            v = np.clip((t.get_value() - FIN) / 0.4, 0, 1)
            voile.set_fill(opacity=0.62 * v)
            for m in bandeau:
                m.set_opacity(v)

        voile.add_updater(maj_fin)

        self.add(titre, tableau, arene, halos, balles, pointes, eclair,
                 voile, bandeau)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par rebond — grave pour l'un, aigu pour l'autre, on
#  reconnaît qui joue sans regarder — un fracas par vie perdue, un accord à la
#  fin. Écrite ici, rien d'emprunté.
# --------------------------------------------------------------------------
def generer_bande_son(chemin="duel.wav", sr=44100):
    import wave

    n = int((DUREE + 2.5) * sr)
    gauche, droite = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(3)

    def poser(debut, onde, pan=0.0):
        i0 = max(0, int(debut * sr))
        fin = min(i0 + len(onde), n)
        if fin > i0:
            g = np.clip(0.5 * (1 - pan), 0, 1)
            gauche[i0:fin] += g * onde[: fin - i0]
            droite[i0:fin] += (1 - g) * onde[: fin - i0]

    def secondes(duree):
        return np.arange(int(duree * sr)) / sr

    def cloche(demi, duree=1.0, force=0.20, base=196.0):
        f = base * 2 ** (demi / 12)
        tt = secondes(duree)
        s = np.zeros_like(tt)
        #  Les harmoniques hautes s'éteignent plus vite que la fondamentale :
        #  c'est ce qui fait entendre un métal frappé plutôt qu'un orgue.
        for mult, amp, chute in ((1, 1.0, 3.0), (2, 0.32, 5.2), (3, 0.12, 7.6)):
            s += amp * np.exp(-tt * chute) * np.sin(TAU * f * mult * tt)
        return force * (1 - np.exp(-tt / 0.002)) * s

    for instant, x, joueur, rang in REBONDS:
        demi = GAMME[rang % len(GAMME)] + (12 if joueur else 0)
        poser(instant, cloche(demi), pan=(x - CX) / R)

    for instant, x, _, _ in PERTES:
        tt = secondes(0.45)
        souffle = rng.normal(0, 1, len(tt)) * (1 - tt / tt[-1]) ** 2.2 * 0.40
        poser(instant, souffle, pan=(x - CX) / R)
        poser(instant, cloche(-12, 1.4, 0.30), pan=(x - CX) / R)

    for i, demi in enumerate((0, 4, 7, 12)):
        poser(FIN + 0.15 + i * 0.11,
              cloche(demi + (12 if VAINQUEUR else 0), 1.8, 0.26))

    #  Réverbération : la même note sèche sonne comme un jouet, et dans une
    #  salle comme un instrument. Un canal par oreille, pour la largeur.
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


# --------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if "--graines" in sys.argv:
        #  De quoi choisir un duel serré : ni trop court, ni gagné d'avance.
        print("graine  durée  vainqueur  vies restantes")
        for g in range(40):
            _, _, pertes, fin, gagnant = simuler(g)
            vies = VIES - sum(1 for p in pertes if p[3] == gagnant)
            print("%5d %7.1f %10s %8d" % (g, fin, NOMS[gagnant], vies))
    else:
        config.pixel_width, config.pixel_height = 1080, 1920
        config.frame_rate = 60
        CinqVies().render()
