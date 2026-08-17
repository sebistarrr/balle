"""
Le grand plongeon — reproduction Manim du duel, format vertical.

Deux balles lâchées à la même hauteur dans un champ de clous en quinconce.
La première qui touche le fond gagne. La gravité augmente de seconde en seconde :
la descente s'accélère, et la fin arrive vite.

Chaque ligne de clous est symétrique par rapport à l'axe du puits, sans quoi le
terrain favoriserait un côté.

Rendu :
    manim -r 1080,1920 --fps 60 grand_plongeon.py GrandPlongeon

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python grand_plongeon.py --graines` en essaie une série et affiche, pour chacune, la
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
X0, X1, DEPART, ARRIVEE = 70, 1010, 520, 1690
R_BALLE = 21
R_CLOU = 11
LIGNES, PAR_LIGNE = 16, 9
#  Gravité faible et clous très élastiques : la balle ne tombe pas, elle
#  ricoche. C'est ce qui fait durer la descente.
G0 = 520.0
G_MONTE = 68.0              # px/s² gagnés par seconde : la fin s'emballe
REBOND = 0.78
V_MAX = 1000.0
DT = 1 / 480

NOMS = ("LIME", "ROSE")
TEINTES = (96.0, 330.0)

#  Graine 4 : 13,8 s, la descente la plus longue des neuf essayées — celle
#  qui laisse le plus de temps pour parier.
GRAINE = 4

#  Le champ de clous est en quinconce, et chaque ligne est symétrique par
#  rapport à l'axe du puits : neuf clous sur les lignes paires, huit sur les
#  impaires. Décaler d'un demi-pas en gardant neuf clous fait sortir le dernier
#  du cadre, la ligne penche à gauche, et le puits favorise un côté.
CLOUS = []
for _l in range(LIGNES):
    _y = DEPART + 130 + _l * (ARRIVEE - DEPART - 210) / (LIGNES - 1)
    _pas = (X1 - X0) / PAR_LIGNE
    if _l % 2 == 0:
        CLOUS += [(X0 + (k + 0.5) * _pas, _y) for k in range(PAR_LIGNE)]
    else:
        CLOUS += [(X0 + k * _pas, _y) for k in range(1, PAR_LIGNE)]


def gravite(t):
    return G0 + G_MONTE * t


def avancement(y):
    return float(np.clip((y - DEPART) / (ARRIVEE - DEPART), 0, 1))


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    #  Les deux tombent de la même hauteur, symétriques par rapport à l'axe :
    #  aucune n'est plus près de l'arrivée.
    ecart = rng.uniform(90, 240)
    balles = [{"i": i, "x": W / 2 + (ecart if i else -ecart), "y": DEPART + 30,
               "vx": rng.uniform(-30, 30), "vy": 0.0} for i in range(2)]

    t = 0.0
    images, chocs = [], []
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["y"], avancement(b["y"])) for b in balles),)

    while vainqueur < 0 and t < 90.0:
        t += DT
        g = gravite(t)
        for b in balles:
            b["vy"] += g * DT
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

            for cx, cy in CLOUS:
                dx, dy = b["x"] - cx, b["y"] - cy
                dd = np.sqrt(dx * dx + dy * dy)
                mini = R_BALLE + R_CLOU
                if dd >= mini or dd < 1e-9:
                    continue
                nx, ny = dx / dd, dy / dd
                b["x"] = cx + nx * mini
                b["y"] = cy + ny * mini
                vn = b["vx"] * nx + b["vy"] * ny
                if vn < 0:
                    b["vx"] -= (1 + REBOND) * vn * nx
                    b["vy"] -= (1 + REBOND) * vn * ny
                    chocs.append((t, cx, cy, b["i"]))

            if b["y"] >= ARRIVEE:
                vainqueur = b["i"]
                break

        a, b = balles
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
    return images, chocs, fin, vainqueur


IMAGES, CHOCS, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class GrandPlongeon(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        parois = VGroup()
        for x in (X0, X1):
            m = Line(vers_scene(x, DEPART), vers_scene(x, ARRIVEE),
                     stroke_color="#6E8CA5", stroke_width=6, stroke_opacity=0.26)
            parois.add(m)

        #  La ligne d'arrivée pulse : c'est le but, elle doit tirer l'œil vers
        #  le bas.
        ligne = DashedLine(vers_scene(X0, ARRIVEE), vers_scene(X1, ARRIVEE),
                           dash_length=0.22, dashed_ratio=0.6,
                           stroke_color="#33FF99", stroke_width=7)

        def maj_ligne(m):
            puls = 0.5 + 0.5 * np.sin(t.get_value() * 5)
            m.set_stroke(opacity=0.5 + 0.4 * puls)

        ligne.add_updater(maj_ligne)

        clous = VGroup(*[
            Dot(vers_scene(cx, cy), radius=R_CLOU * ECHELLE, color="#4A5A6A")
            for cx, cy in CLOUS])

        def maj_clous(g):
            u = t.get_value()
            #  Un clou frappé s'éclaire un instant : on voit le chemin qu'a pris
            #  chaque balle, même quand elle va vite.
            recents = [(cx, cy) for instant, cx, cy, _ in CHOCS
                       if 0 <= u - instant < 0.30]
            for m, (cx, cy) in zip(g, CLOUS):
                vif = any(abs(cx - ax) < 1 and abs(cy - ay) < 1
                          for ax, ay in recents)
                m.set_color("#D7E6F2" if vif else "#4A5A6A")

        clous.add_updater(maj_clous)

        # --- jauges -----------------------------------------------------------
        jauges, remplis = VGroup(), []
        for i in range(2):
            y = 186 + i * 92
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.64))
            nom.scale_to_fit_height(0.30).move_to(vers_scene(92, y),
                                                  aligned_edge=LEFT)
            fond_j = RoundedRectangle(width=520 * ECHELLE, height=26 * ECHELLE,
                                      corner_radius=13 * ECHELLE, stroke_width=0,
                                      fill_color="#FFFFFF", fill_opacity=0.08)
            fond_j.move_to(vers_scene(360 + 260, y - 5))
            plein = RoundedRectangle(width=26 * ECHELLE, height=26 * ECHELLE,
                                     corner_radius=13 * ECHELLE, stroke_width=0,
                                     fill_color=teinte(TEINTES[i], 0.58),
                                     fill_opacity=1)
            jauges.add(nom, fond_j, plein)
            remplis.append(plein)

        def maj_jauges(_):
            (etats,) = instantane(t.get_value())
            for i, plein in enumerate(remplis):
                larg = max(26, 520 * etats[i][2])
                plein.become(RoundedRectangle(
                    width=larg * ECHELLE, height=26 * ECHELLE,
                    corner_radius=13 * ECHELLE, stroke_width=0,
                    fill_color=teinte(TEINTES[i], 0.58), fill_opacity=1))
                plein.move_to(vers_scene(360 + larg / 2, 186 + i * 92 - 5))

        jauges.add_updater(maj_jauges)

        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_BALLE) for i in range(2)])

        def maj_balles(_):
            (etats,) = instantane(t.get_value())
            for i, b in enumerate(balles):
                c = vers_scene(etats[i][0], etats[i][1])
                b.move_to(c)
                for anne in halos[i]:
                    anne.move_to(c)

        balles.add_updater(maj_balles)

        ecart = abs(IMAGES[-1][0][0][2] - IMAGES[-1][0][1][2])
        voile, bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "sur le fil" if ecart <= 0.02 else "%d %% d'avance" % round(ecart * 100),
            t, FIN)

        self.add(accroche("qui touchera le fond en premier ?"), jauges,
                 parois, ligne, clous, halos, balles, voile, bloc)

        if AVEC_SON:
            gamme = (0, 3, 7, 10)
            ev = [(instant, "cloche", gamme[int(cy) % 4] + (12 if i else 0),
                   (cx - W / 2) / (W / 2), 0.15)
                  for instant, cx, cy, i in CHOCS]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "plongeon.wav"))

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
        GrandPlongeon().render()
