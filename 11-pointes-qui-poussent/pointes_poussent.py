"""
Les pointes qui poussent — reproduction Manim du duel, format vertical.

Sept pointes plantées sur le bord, qui s'allongent vers le centre de plus
en plus vite. Deux balles rebondissent dans ce qu'il reste d'espace, avec trois
vies chacune. La première à bout de vies a perdu — et l'espace se referme sur
les deux à la fois.

La couronne tourne pendant qu'elle pousse, ce qui déplace sans cesse les
intervalles sûrs : impossible d'en apprendre le rythme.

Rendu :
    manim -r 1080,1920 --fps 60 pointes_poussent.py PointesPoussent

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python pointes_poussent.py --graines` en essaie une série et affiche, pour chacune, la
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
#  Réglages, dans le repère pixel de la page voisine
# --------------------------------------------------------------------------
CX, CY, R = 540, 1030, 452
R_BALLE = 26
V0 = 720.0
#  Sept pointes de 3,2° : elles couvrent 12 % du bord. Plus larges ou plus
#  nombreuses, la balle meurt au premier ou au deuxième rebond.
N_POINTES = 7
DEMI_POINTE = 3.2 * DEGREES
VIES = 3
INVULN = 0.7
POUSSE0 = 4.0               # px/s de longueur gagnée, au départ
POUSSE_ACCEL = 0.85         # px/s² : les pointes poussent de plus en plus vite
ROTATION = 13 * DEGREES
DT = 1 / 480

NOMS = ("IRIS", "MENTHE")
TEINTES = (268.0, 158.0)

#  Graine 6 : 13,8 s, MENTHE survit.
GRAINE = 6


def longueur(t):
    return POUSSE0 * t + POUSSE_ACCEL * t * t / 2


def libre(t):
    return max(0.0, R - longueur(t))


def sur_pointe(angle, t):
    a = ROTATION * t
    d = (angle - a) % TAU
    pas = TAU / N_POINTES
    d = d % pas
    return min(d, pas - d) < DEMI_POINTE


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    a0 = rng.uniform(0, TAU)
    balles = []
    for i in range(2):
        ou = a0 + i * PI
        cap = rng.uniform(0, TAU)
        balles.append({"i": i, "vivant": 1, "vies": VIES, "invuln": INVULN,
                       "x": CX + np.cos(ou) * 180, "y": CY + np.sin(ou) * 180,
                       "vx": np.cos(cap) * V0, "vy": np.sin(cap) * V0})

    t = 0.0
    images, chocs, touches = [], [], []
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["y"], b["invuln"], b["vies"], b["vivant"])
                      for b in balles), libre(min(t, 1e9)))

    while vainqueur < 0 and t < 90.0:
        t += DT
        lib = libre(t)
        for b in balles:
            if not b["vivant"]:
                continue
            if b["invuln"] > 0:
                b["invuln"] -= DT
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            dx, dy = b["x"] - CX, b["y"] - CY
            d = np.sqrt(dx * dx + dy * dy) or 1e-9
            nx, ny = dx / d, dy / d
            angle = np.arctan2(-ny, nx)

            #  Deux barrières : la pointe, plus près du centre, et le bord
            #  derrière. Toucher la première coûte une vie ; la seconde renvoie.
            if b["invuln"] <= 0 and d > lib - R_BALLE and sur_pointe(angle, t):
                b["vies"] -= 1
                touches.append((t, b["x"], b["y"], b["i"]))
                if b["vies"] <= 0:
                    b["vivant"] = 0
                    vainqueur = 1 - b["i"]
                    break
                #  Renvoyée près du centre, brièvement intouchable : sans ce
                #  répit elle se ferait reprendre à l'image suivante.
                ou, cap = rng.uniform(0, TAU), rng.uniform(0, TAU)
                rentree = min(180.0, max(0.0, lib - R_BALLE - 30))
                b["x"] = CX + np.cos(ou) * rentree
                b["y"] = CY + np.sin(ou) * rentree
                b["vx"] = np.cos(cap) * V0
                b["vy"] = np.sin(cap) * V0
                b["invuln"] = INVULN
                continue

            if d > R - R_BALLE:
                b["x"] = CX + nx * (R - R_BALLE)
                b["y"] = CY + ny * (R - R_BALLE)
                p = 2 * (b["vx"] * nx + b["vy"] * ny)
                b["vx"] -= p * nx
                b["vy"] -= p * ny
                s = np.sqrt(b["vx"] ** 2 + b["vy"] ** 2)
                b["vx"] *= V0 / s
                b["vy"] *= V0 / s
                chocs.append((t, b["x"], b["i"], int(d) % 5))

        a, b = balles
        if a["vivant"] and b["vivant"]:
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

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, chocs, touches, fin, vainqueur


IMAGES, CHOCS, TOUCHES, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class PointesPoussent(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        bord = Circle(radius=R * ECHELLE, stroke_color="#7896AA",
                      stroke_width=6, stroke_opacity=0.30, fill_opacity=0)
        bord.move_to(vers_scene(CX, CY))

        #  Le disque encore libre, en creux : ce qu'il reste d'espace se voit
        #  d'un coup d'œil, et il se referme sous nos yeux.
        disque = Circle(radius=R * ECHELLE, stroke_color="#78C8E6",
                        stroke_width=3, stroke_opacity=0.30,
                        fill_color="#5AAAC8", fill_opacity=0.06)

        def maj_disque(m):
            _, lib = instantane(t.get_value())
            m.become(Circle(radius=max(1e-3, lib) * ECHELLE,
                            stroke_color="#78C8E6", stroke_width=3,
                            stroke_opacity=0.30, fill_color="#5AAAC8",
                            fill_opacity=0.06).move_to(vers_scene(CX, CY)))

        disque.add_updater(maj_disque)

        pointes = VGroup(*[Polygon(ORIGIN, ORIGIN, ORIGIN, stroke_width=0,
                                   fill_opacity=1) for _ in range(N_POINTES)])

        def maj_pointes(g):
            u = min(t.get_value(), FIN)
            lg = min(R - 20, longueur(u))
            for i, tri in enumerate(g):
                a = ROTATION * u + i * TAU / N_POINTES

                def p(ang, ray):
                    return vers_scene(CX + ray * np.cos(ang),
                                      CY - ray * np.sin(ang))

                tri.set_points_as_corners([
                    p(a - DEMI_POINTE, R + 4), p(a + DEMI_POINTE, R + 4),
                    p(a, R - lg), p(a - DEMI_POINTE, R + 4)])
                #  Blanche au bord, rouge à la pointe : le danger est au bout.
                tri.set_fill(color=["#E6F0F8", "#FF5A6E"], opacity=1)

        pointes.add_updater(maj_pointes)

        # --- tableau : nom et pastilles de vie --------------------------------
        tableau, pastilles = VGroup(), []
        for i in range(2):
            y = 186 + i * 90
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.62))
            nom.scale_to_fit_height(0.32).move_to(vers_scene(92, y - 14),
                                                  aligned_edge=LEFT)
            tableau.add(nom)
            rang = []
            for k in range(VIES):
                c = Circle(radius=20 * ECHELLE, stroke_width=0, fill_opacity=1)
                c.move_to(vers_scene(560 + k * 62, y - 14))
                tableau.add(c)
                rang.append(c)
            pastilles.append(rang)

        def maj_tableau(_):
            etats, _ = instantane(t.get_value())
            for i, rang in enumerate(pastilles):
                for k, c in enumerate(rang):
                    if k < etats[i][3]:
                        c.set_fill(teinte(TEINTES[i], 0.60), opacity=1)
                    else:
                        c.set_fill("#FFFFFF", opacity=0.10)

        tableau.add_updater(maj_tableau)

        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_BALLE) for i in range(2)])

        def maj_balles(_):
            etats, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                x, y, invuln, _, vivant = etats[i]
                c = vers_scene(x, y)
                #  Une balle intouchable clignote : sans cela on croit à un
                #  défaut quand elle traverse une pointe juste après une touche.
                visible = vivant and not (invuln > 0 and int(invuln * 12) % 2)
                b.move_to(c).set_opacity(1 if visible else 0)
                for k, anne in enumerate(halos[i]):
                    anne.move_to(c)
                    anne.set_fill(opacity=(0.14, 0.07)[k] if visible else 0)

        balles.add_updater(maj_balles)

        lib_fin = IMAGES[-1][1]
        voile, bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "il restait %d %% d'espace" % round(100 * lib_fin / R), t, FIN)

        self.add(accroche("qui se fera empaler ?"), tableau, disque, halos,
                 balles, pointes, bord, voile, bloc)

        if AVEC_SON:
            gamme = (0, 3, 7, 10, 12)
            ev = [(instant, "cloche", gamme[k] + (12 if i else 0),
                   (x - CX) / R, 0.17)
                  for instant, x, i, k in CHOCS]
            ev += [(instant, "souffle", 240, (x - CX) / R, 0.5)
                   for instant, x, _, _ in TOUCHES]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "pointes.wav"))

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
        PointesPoussent().render()
