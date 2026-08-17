"""
Le sol qui s'effrite — reproduction Manim du duel, format vertical.

Deux balles rebondissent sur un sol de seize dalles. Chaque rebond fissure
la dalle touchée, et au troisième coup elle cède. Celle qui passe au travers a
perdu. Elles partagent le sol : en cassant les dalles sous leurs propres pieds,
elles creusent aussi le terrain de l'autre.

Le rebond sur une dalle est parfaitement élastique : la balle remonte toujours à
la même hauteur, donc la cadence des coups reste régulière et le duel ne
s'éteint pas de lui-même. Ce qui le termine, c'est le sol.

Rendu :
    manim -r 1080,1920 --fps 60 sol_effrite.py SolEffrite

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python sol_effrite.py --graines` en essaie une série et affiche, pour chacune, la
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
X0, X1, PLAFOND, SOL = 80, 1000, 560, 1440
N_DALLES = 16
LARG_DALLE = (X1 - X0) / N_DALLES
HAUT_DALLE = 46
PV0 = 3                     # coups qu'encaisse une dalle
PALIER = 12.0               # s au bout desquelles elles n'en encaissent que deux
R_BALLE = 26
G = 2200.0
V_LAT = 240.0
MORT = 1760
DT = 1 / 480

NOMS = ("ROUGE", "CYAN")
TEINTES = (352.0, 186.0)

#  Graine 3 : 19,7 s, CYAN survit. Ni trop court ni interminable.
GRAINE = 3


def pv_max(t):
    return PV0 if t < PALIER else PV0 - 1


def colonne_de(x):
    return int(min(N_DALLES - 1, max(0, (x - X0) // LARG_DALLE)))


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    dalles = [PV0] * N_DALLES
    balles = [{"i": i, "vivant": 1,
               "x": X0 + (0.22 + 0.5 * i + rng.uniform(0, 0.12)) * (X1 - X0),
               "y": PLAFOND + 120 + rng.uniform(0, 90),
               "vx": (-1 if rng.random() < 0.5 else 1) * (V_LAT + rng.uniform(0, 120)),
               "vy": 0.0} for i in range(2)]

    t = 0.0
    images, chocs, ruines = [], [], []
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["y"], b["vivant"]) for b in balles),
                tuple(dalles))

    while vainqueur < 0 and t < 90.0:
        t += DT
        for b in balles:
            if not b["vivant"]:
                continue
            b["vy"] += G * DT
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            if b["x"] < X0 + R_BALLE:
                b["x"] = X0 + R_BALLE
                b["vx"] = abs(b["vx"])
            if b["x"] > X1 - R_BALLE:
                b["x"] = X1 - R_BALLE
                b["vx"] = -abs(b["vx"])
            if b["y"] < PLAFOND + R_BALLE:
                b["y"] = PLAFOND + R_BALLE
                b["vy"] = abs(b["vy"])

            #  Contact avec le sol : seulement si la dalle sous la balle tient
            #  encore. Sinon elle passe au travers — c'est tout le jeu.
            if b["vy"] > 0 and b["y"] + R_BALLE >= SOL and b["y"] < SOL + HAUT_DALLE:
                col = colonne_de(b["x"])
                if dalles[col] > 0:
                    b["y"] = SOL - R_BALLE
                    b["vy"] = -b["vy"]       # rebond parfait : l'altitude tient
                    dalles[col] -= 1
                    cx = X0 + (col + 0.5) * LARG_DALLE
                    chocs.append((t, dalles[col] * 3 + (12 if b["i"] else 0),
                                  (cx - W / 2) / (W / 2)))
                    if dalles[col] <= 0:
                        ruines.append((t, (cx - W / 2) / (W / 2)))
            if b["y"] > MORT:
                b["vivant"] = 0
                vainqueur = 1 - b["i"]
                break

        #  Choc entre les deux : de quoi se pousser au-dessus d'un trou.
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

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, chocs, ruines, fin, vainqueur


IMAGES, CHOCS, RUINES, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class SolEffrite(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        cadre = VMobject(stroke_color="#6E8CA5", stroke_width=6,
                         stroke_opacity=0.28)
        cadre.set_points_as_corners([
            vers_scene(X0, SOL + HAUT_DALLE), vers_scene(X0, PLAFOND),
            vers_scene(X1, PLAFOND), vers_scene(X1, SOL + HAUT_DALLE)])

        # --- le sol -----------------------------------------------------------
        sol = VGroup()
        for i in range(N_DALLES):
            d = RoundedRectangle(width=(LARG_DALLE - 6) * ECHELLE,
                                 height=HAUT_DALLE * ECHELLE,
                                 corner_radius=5 * ECHELLE,
                                 stroke_width=2.5, fill_opacity=1)
            d.move_to(vers_scene(X0 + (i + 0.5) * LARG_DALLE, SOL + HAUT_DALLE / 2))
            sol.add(d)

        def maj_sol(g):
            u = t.get_value()
            _, dalles = instantane(u)
            pv = pv_max(min(u, FIN))
            for i, m in enumerate(g):
                v = dalles[i]
                if v <= 0:
                    m.set_opacity(0)
                    continue
                #  La dalle s'assombrit et rougit à mesure qu'elle encaisse :
                #  l'état du sol se lit sans compter.
                part = v / pv
                h = 150 - 145 * (1 - part)
                m.set_fill(teinte(h, 0.22 + 0.20 * part, 0.55), opacity=1)
                m.set_stroke(teinte(h, 0.48, 0.70), width=2.5, opacity=0.85)

        sol.add_updater(maj_sol)

        # --- tableau de bord --------------------------------------------------
        #  Ce qui fait peur, ce n'est pas le nombre de dalles restantes, c'est
        #  l'état de celle qu'on a sous les pieds. C'est donc celle-là qu'on
        #  affiche, joueur par joueur.
        tableau, cases = VGroup(), []
        for i in range(2):
            y = 190 + i * 92
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.62))
            nom.scale_to_fit_height(0.32).move_to(vers_scene(92, y - 14),
                                                  aligned_edge=LEFT)
            lib = Text("sous ses pieds", color="#96AAB4").scale_to_fit_height(0.21)
            lib.move_to(vers_scene(440, y - 14), aligned_edge=LEFT)
            tableau.add(nom, lib)
            rang = []
            for k in range(PV0):
                c = RoundedRectangle(width=44 * ECHELLE, height=34 * ECHELLE,
                                     corner_radius=7 * ECHELLE, stroke_width=0,
                                     fill_opacity=1)
                c.move_to(vers_scene(790 + k * 62 + 22, y - 17))
                tableau.add(c)
                rang.append(c)
            cases.append(rang)

        def maj_tableau(_):
            etats, dalles = instantane(t.get_value())
            for i, rang in enumerate(cases):
                x, _, vivant = etats[i]
                v = dalles[colonne_de(x)] if vivant else 0
                for k, c in enumerate(rang):
                    if k < v:
                        c.set_fill(teinte(8 if v <= 1 else 150, 0.56, 0.9),
                                   opacity=1)
                    else:
                        c.set_fill("#FFFFFF", opacity=0.09)

        tableau.add_updater(maj_tableau)

        # --- les balles -------------------------------------------------------
        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_BALLE) for i in range(2)])

        def maj_balles(_):
            etats, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                x, y, vivant = etats[i]
                c = vers_scene(x, y)
                b.move_to(c).set_opacity(1 if vivant else 0)
                for k, anne in enumerate(halos[i]):
                    anne.move_to(c)
                    anne.set_fill(opacity=(0.14, 0.07)[k] if vivant else 0)

        balles.add_updater(maj_balles)

        restantes = sum(1 for v in IMAGES[-1][1] if v > 0)
        voile, bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "%d dalle%s sous ses pieds" % (restantes, "s" if restantes > 1 else ""),
            t, FIN)

        self.add(accroche("qui passera au travers ?"), tableau, cadre, sol,
                 halos, balles, voile, bloc)

        if AVEC_SON:
            ev = [(instant, "cloche", demi, pan, 0.22)
                  for instant, demi, pan in CHOCS]
            ev += [(instant, "souffle", 260, pan, 0.34) for instant, pan in RUINES]
            ev += [(FIN, "souffle", 140, 0.0, 0.5)]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "sol.wav"))

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
        SolEffrite().render()
