"""
Le mur qui pousse — reproduction Manim du duel, format vertical.

Deux chambres, un mur mobile au milieu, une balle de chaque côté. Chaque
coup porté au mur le pousse d'autant vers l'adversaire — un tir à la corde où
l'on gagne du terrain sans jamais voir l'autre. Quand une chambre devient trop
étroite, sa balle est écrasée.

La poussée dépend du cube de la largeur de la chambre d'où part le coup, sans
quoi les deux camps se compensent exactement et le mur ne bouge plus.

Rendu :
    manim -r 1080,1920 --fps 60 mur_qui_pousse.py MurQuiPousse

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python mur_qui_pousse.py --graines` en essaie une série et affiche, pour chacune, la
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
X0, X1, Y0, Y1 = 70, 1010, 540, 1700
R_BALLE = 28
V0 = 700.0
EP_MUR = 18                 # demi-épaisseur du mur
POUSSE0 = 15.0              # px gagnés par coup, au départ
POUSSE_ACCEL = 1.1
ECRASE = 2 * R_BALLE + 14   # largeur en deçà de laquelle on est écrasé
#  Passé ce délai, les murs extérieurs se referment eux aussi. L'avantage creusé
#  par la poussée décide presque toujours, mais pas toujours.
SERRAGE = 16.0
SERRE_V = 15.0
DT = 1 / 480

NOMS = ("JADE", "RUBIS")
TEINTES = (156.0, 344.0)

#  Graine 3 : 20,9 s, JADE écrase RUBIS.
GRAINE = 3


def serrage(t):
    return max(0.0, (t - SERRAGE) * SERRE_V)


def bornes(i, mur, t):
    g, d = X0 + serrage(t), X1 - serrage(t)
    return (g, mur - EP_MUR) if i == 0 else (mur + EP_MUR, d)


def part_de(i, mur, t):
    g, d = bornes(i, mur, t)
    total = (X1 - serrage(t)) - (X0 + serrage(t)) - 2 * EP_MUR
    return max(0.0, (d - g) / total) if total > 0 else 0.0


def poussee_par_coup(i, mur, t):
    """La poussée dépend du cube de la largeur de la chambre d'où part le coup.

    Sans lien du tout, le duel ne finit jamais : la balle enfermée dans la
    chambre étroite revient plus souvent au mur, puisqu'elle a moins de chemin à
    faire, et rend exactement les coups qu'elle prend. Une poussée simplement
    proportionnelle à la largeur ne change rien non plus, la fréquence des coups
    variant comme l'inverse de la largeur : le produit est constant. Il faut un
    exposant supérieur à un pour que l'avantage se creuse tout seul.
    """
    return (POUSSE0 + POUSSE_ACCEL * t) * (0.12 + 3.0 * part_de(i, mur, t) ** 3)


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    mur = (X0 + X1) / 2
    balles = []
    for i in range(2):
        g, d = bornes(i, mur, 0.0)
        a = rng.uniform(0, TAU)
        balles.append({"i": i, "vivant": 1, "x": (g + d) / 2,
                       "y": (Y0 + Y1) / 2 + (-1 if i else 1) * 200,
                       "vx": np.cos(a) * V0, "vy": np.sin(a) * V0})

    t = 0.0
    images, coups_son = [], []
    coups = [0, 0]
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["y"], b["vivant"]) for b in balles), mur,
                serrage(t),
                tuple(part_de(i, mur, t) for i in range(2)))

    def ecraser():
        nonlocal vainqueur
        l0 = bornes(0, mur, t)
        l1 = bornes(1, mur, t)
        perdant = 0 if (l0[1] - l0[0]) < (l1[1] - l1[0]) else 1
        g, d = bornes(perdant, mur, t)
        if d - g < ECRASE:
            balles[perdant]["vivant"] = 0
            vainqueur = 1 - perdant

    while vainqueur < 0 and t < 120.0:
        t += DT
        if t > SERRAGE:
            ecraser()
            if vainqueur >= 0:
                break

        for b in balles:
            if not b["vivant"]:
                continue
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            if b["y"] < Y0 + R_BALLE:
                b["y"] = Y0 + R_BALLE
                b["vy"] = abs(b["vy"])
            if b["y"] > Y1 - R_BALLE:
                b["y"] = Y1 - R_BALLE
                b["vy"] = -abs(b["vy"])

            g, d = bornes(b["i"], mur, t)
            frappe = False
            if b["i"] == 0:
                if b["x"] < g + R_BALLE:
                    b["x"] = g + R_BALLE
                    b["vx"] = abs(b["vx"])
                if b["x"] > d - R_BALLE:
                    b["x"] = d - R_BALLE
                    b["vx"] = -abs(b["vx"])
                    frappe = True
            else:
                if b["x"] > d - R_BALLE:
                    b["x"] = d - R_BALLE
                    b["vx"] = -abs(b["vx"])
                if b["x"] < g + R_BALLE:
                    b["x"] = g + R_BALLE
                    b["vx"] = abs(b["vx"])
                    frappe = True

            if frappe:
                #  Le mur part du côté de l'adversaire : frapper, c'est gagner
                #  du terrain.
                mur += (1 if b["i"] == 0 else -1) * poussee_par_coup(b["i"], mur, t)
                coups[b["i"]] += 1
                coups_son.append((t, b["i"], coups[b["i"]], b["y"]))
                ecraser()
                if vainqueur >= 0:
                    break

            #  L'étau peut avoir dépassé la balle : on la ramène dedans, sinon
            #  elle reste bloquée dehors et ne frappe plus jamais.
            g2, d2 = bornes(b["i"], mur, t)
            b["x"] = min(max(b["x"], g2 + R_BALLE), d2 - R_BALLE)
            s = np.sqrt(b["vx"] ** 2 + b["vy"] ** 2)
            if s > 1e-9:
                b["vx"] *= V0 / s
                b["vy"] *= V0 / s

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, coups_son, coups, fin, vainqueur


IMAGES, COUPS_SON, COUPS, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class MurQuiPousse(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        chambres = VGroup(*[
            Rectangle(width=1, height=(Y1 - Y0) * ECHELLE, stroke_width=0,
                      fill_color=teinte(TEINTES[i], 0.12, 0.6), fill_opacity=1)
            for i in range(2)])
        mur_m = Rectangle(width=2 * EP_MUR * ECHELLE,
                          height=(Y1 - Y0) * ECHELLE, stroke_width=0,
                          fill_color="#EEF5FA", fill_opacity=1)
        cadre = Rectangle(width=1, height=(Y1 - Y0) * ECHELLE,
                          stroke_color="#96B4C8", stroke_width=6,
                          stroke_opacity=0.30, fill_opacity=0)

        def maj_decor(_):
            etats, mur, ser, _ = instantane(t.get_value())
            for i, m in enumerate(chambres):
                g, d = ((X0 + ser, mur - EP_MUR) if i == 0
                        else (mur + EP_MUR, X1 - ser))
                larg = max(1e-3, d - g)
                #  stretch_to_fit_width, et non width= : le setter de width
                #  passe par scale_to_fit_width, qui conserve le rapport et
                #  étire donc aussi la hauteur. Les chambres débordaient du
                #  cadre et recouvraient le tableau de bord.
                m.stretch_to_fit_width(larg * ECHELLE)
                m.move_to(vers_scene((g + d) / 2, (Y0 + Y1) / 2))
            mur_m.move_to(vers_scene(mur, (Y0 + Y1) / 2))
            cadre.stretch_to_fit_width(
                max(1e-3, (X1 - ser) - (X0 + ser)) * ECHELLE)
            cadre.move_to(vers_scene(W / 2, (Y0 + Y1) / 2))

        chambres.add_updater(maj_decor)

        # --- jauges : la position du mur est le score ---------------------------
        jauges, remplis, pourcents = VGroup(), [], []
        for i in range(2):
            y = 186 + i * 92
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.62))
            nom.scale_to_fit_height(0.32).move_to(vers_scene(92, y),
                                                  aligned_edge=LEFT)
            fond_j = RoundedRectangle(width=500 * ECHELLE, height=26 * ECHELLE,
                                      corner_radius=13 * ECHELLE, stroke_width=0,
                                      fill_color="#FFFFFF", fill_opacity=0.08)
            fond_j.move_to(vers_scene(400 + 250, y - 5))
            plein = RoundedRectangle(width=250 * ECHELLE, height=26 * ECHELLE,
                                     corner_radius=13 * ECHELLE, stroke_width=0,
                                     fill_color=teinte(TEINTES[i], 0.58),
                                     fill_opacity=1)
            pct = Text("50 %", color="#DCE8EE").scale_to_fit_height(0.22)
            pct.move_to(vers_scene(1005, y), aligned_edge=RIGHT)
            pct.rang = -1
            jauges.add(nom, fond_j, plein, pct)
            remplis.append(plein)
            pourcents.append(pct)

        def maj_jauges(_):
            _, _, _, parts = instantane(t.get_value())
            for i, plein in enumerate(remplis):
                larg = max(8, 500 * parts[i])
                col = teinte(8 if parts[i] < 0.2 else TEINTES[i], 0.58)
                plein.become(RoundedRectangle(
                    width=larg * ECHELLE, height=26 * ECHELLE,
                    corner_radius=13 * ECHELLE, stroke_width=0,
                    fill_color=col, fill_opacity=1))
                plein.move_to(vers_scene(400 + larg / 2, 186 + i * 92 - 5))
                rang = int(round(parts[i] * 100))
                if rang != pourcents[i].rang:
                    m = Text("%d %%" % rang, color="#DCE8EE")
                    m.scale_to_fit_height(0.22)
                    m.move_to(vers_scene(1005, 186 + i * 92), aligned_edge=RIGHT)
                    pourcents[i].become(m)
                    pourcents[i].rang = rang

        jauges.add_updater(maj_jauges)

        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_BALLE,
                                      ((1.8, 0.14), (2.7, 0.07)))
                         for i in range(2)])

        def maj_balles(_):
            etats, _, _, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                c = vers_scene(etats[i][0], etats[i][1])
                b.move_to(c).set_opacity(1 if etats[i][2] else 0)
                for k, anne in enumerate(halos[i]):
                    anne.move_to(c)
                    anne.set_fill(opacity=(0.14, 0.07)[k] if etats[i][2] else 0)

        balles.add_updater(maj_balles)

        etau = Text("L'ÉTAU SE REFERME", weight=BOLD, color="#FF6E6E")
        etau.scale_to_fit_height(0.26).move_to(vers_scene(W / 2, H - 100))

        def maj_etau(m):
            u = t.get_value()
            m.set_opacity(1.0 if SERRAGE < u < FIN else 0.0)

        etau.add_updater(maj_etau)

        voile, bloc = bandeau_fin(NOMS[VAINQUEUR],
                                  teinte(TEINTES[VAINQUEUR], 0.64),
                                  "%d coups au mur" % COUPS[VAINQUEUR], t, FIN)

        #  Le décor d'abord, le tableau de bord par-dessus : rien ne doit
        #  pouvoir recouvrir les jauges.
        self.add(chambres, mur_m, cadre, halos, balles,
                 accroche("qui va se faire écraser ?"), jauges, etau,
                 voile, bloc)

        if AVEC_SON:
            gamme = (0, 5, 7, 12)
            ev = [(instant, "cloche", gamme[n % 4] + (12 if i else 0),
                   0.5 * (1 if i else -1), 0.22)
                  for instant, i, n, _ in COUPS_SON]
            ev += [(FIN, "souffle", 170, 0.0, 0.55)]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "mur.wav"))

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
        MurQuiPousse().render()
