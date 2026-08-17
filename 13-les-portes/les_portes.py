"""
Les portes — reproduction Manim du duel, format vertical.

Deux puits côte à côte, une balle dans chacun. Le décor défile et les
portes montent à leur rencontre : chacune donne ou retire une vie, et c'est la
dérive horizontale de la balle qui décide par laquelle elle passera. La première
à zéro a perdu.

La part de portes perdantes monte avec le temps : au début on se refait, à la
fin on ne fait que perdre.

Rendu :
    manim -r 1080,1920 --fps 60 les_portes.py LesPortes

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python les_portes.py --graines` en essaie une série et affiche, pour chacune, la
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
Y0, Y1 = 470, 1760          # hauteur visible du puits
Y_BALLE = 1520              # les balles restent à cette hauteur : c'est le
                            # décor qui défile, pas elles
R_BALLE = 26
VIES = 6
ESPACE = 300                # écart vertical entre deux portes
OUVERTURES = 3
LARG_OUV = 96
V_DEFILE0 = 175.0
V_DEFILE_ACCEL = 13.0
V_LAT = 210.0
DT = 1 / 480

MARGE, CLOISON = 60, 26
LARG = (W - 2 * MARGE - CLOISON) / 2

NOMS = ("SAFRAN", "INDIGO")
TEINTES = (44.0, 250.0)

#  Graine 3 : 21,6 s, INDIGO tient jusqu'au bout.
GRAINE = 3


def couloir(i):
    g = MARGE + i * (LARG + CLOISON)
    return g, g + LARG


def defile(t):
    return V_DEFILE0 + V_DEFILE_ACCEL * t


def part_malus(t):
    """La part de portes qui coûtent une vie monte avec le temps : au début on
    se refait, à la fin on ne fait que perdre. C'est ce qui garantit une fin."""
    return min(0.85, 0.45 + 0.025 * t)


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)

    def nouvelle_porte(i, y, t):
        g, d = couloir(i)
        pas = (d - g) / OUVERTURES
        ouvs = []
        for k in range(OUVERTURES):
            cx = (g + (k + 0.5) * pas
                  + rng.uniform(-0.5, 0.5) * (pas - LARG_OUV) * 0.8)
            ouvs.append([cx, 1 if rng.random() > part_malus(t) else -1])
        #  Au moins une bonne porte par rangée : une rangée entièrement
        #  perdante n'est plus un choix, c'est une punition.
        if not any(o[1] > 0 for o in ouvs):
            ouvs[rng.integers(OUVERTURES)][1] = 1
        return {"i": i, "y": y, "ouvs": ouvs}

    balles = []
    for i in range(2):
        g, d = couloir(i)
        balles.append({"i": i, "vivant": 1, "vies": VIES,
                       "x": (g + d) / 2 + rng.uniform(-0.25, 0.25) * LARG,
                       "vx": (-1 if rng.random() < 0.5 else 1) * V_LAT})

    portes = []
    for k in range(8):
        for i in range(2):
            portes.append(nouvelle_porte(i, Y_BALLE - 200 - k * ESPACE, 0.0))
    prochain_rang = Y_BALLE - 200 - 8 * ESPACE

    t = 0.0
    images, passages = [], []
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["vies"], b["vivant"]) for b in balles),
                tuple((p["i"], p["y"], tuple((o[0], o[1]) for o in p["ouvs"]))
                      for p in portes))

    while vainqueur < 0 and t < 120.0:
        t += DT
        dy = defile(t) * DT

        for p in portes:
            avant = p["y"]
            p["y"] += dy
            if avant <= Y_BALLE < p["y"]:
                b = balles[p["i"]]
                if not b["vivant"]:
                    continue
                #  La balle passe par l'ouverture dont elle est la plus proche :
                #  c'est sa dérive horizontale, et elle seule, qui décide.
                choix = min(p["ouvs"], key=lambda o: abs(o[0] - b["x"]))
                b["x"] = choix[0]
                b["vx"] = ((-1 if rng.random() < 0.5 else 1) * V_LAT
                           * rng.uniform(0.6, 1.4))
                b["vies"] = min(VIES + 3, b["vies"] + choix[1])
                passages.append((t, b["x"], choix[1], b["i"]))
                if b["vies"] <= 0:
                    b["vivant"] = 0
                    vainqueur = 1 - b["i"]
                    break
        if vainqueur >= 0:
            break

        portes = [p for p in portes if p["y"] < Y1 + 120]
        prochain_rang += dy
        while prochain_rang > Y0 - ESPACE:
            prochain_rang -= ESPACE
            for i in range(2):
                portes.append(nouvelle_porte(i, prochain_rang, t))

        for b in balles:
            if not b["vivant"]:
                continue
            g, d = couloir(b["i"])
            b["x"] += b["vx"] * DT
            if b["x"] < g + R_BALLE:
                b["x"] = g + R_BALLE
                b["vx"] = abs(b["vx"])
            if b["x"] > d - R_BALLE:
                b["x"] = d - R_BALLE
                b["vx"] = -abs(b["vx"])

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, passages, fin, vainqueur


IMAGES, PASSAGES, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES
#  Combien de portes au plus à l'écran : on prépare autant d'objets une fois
#  pour toutes, et on les replace à chaque image.
MAX_PORTES = max(len(im[1]) for im in IMAGES)


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class LesPortes(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        fonds = VGroup()
        for i in range(2):
            g, d = couloir(i)
            m = Rectangle(width=(d - g) * ECHELLE, height=(Y1 - Y0) * ECHELLE,
                          stroke_width=0, fill_color=teinte(TEINTES[i], 0.08, 0.55),
                          fill_opacity=1)
            m.move_to(vers_scene((g + d) / 2, (Y0 + Y1) / 2))
            fonds.add(m)

        # --- les portes -------------------------------------------------------
        #  Un linteau et trois ouvertures par porte. Les objets sont créés une
        #  fois et déplacés : en recréer à chaque image coûterait bien trop cher.
        portes = VGroup()
        pieces = []
        for _ in range(MAX_PORTES):
            linteau = Rectangle(width=LARG * ECHELLE, height=18 * ECHELLE,
                                stroke_width=0, fill_color="#96AFC3",
                                fill_opacity=0.30)
            ouvs = []
            for _k in range(OUVERTURES):
                trou = Rectangle(width=LARG_OUV * ECHELLE, height=22 * ECHELLE,
                                 stroke_width=0, fill_color="#04060A",
                                 fill_opacity=1)
                barre = Rectangle(width=LARG_OUV * ECHELLE, height=8 * ECHELLE,
                                  stroke_width=0, fill_opacity=0.9)
                ouvs.append((trou, barre))
            portes.add(linteau, *[m for paire in ouvs for m in paire])
            pieces.append((linteau, ouvs))

        def maj_portes(_):
            _, liste = instantane(t.get_value())
            for k, (linteau, ouvs) in enumerate(pieces):
                if k >= len(liste):
                    linteau.set_opacity(0)
                    for trou, barre in ouvs:
                        trou.set_opacity(0)
                        barre.set_opacity(0)
                    continue
                i, y, trous = liste[k]
                g, d = couloir(i)
                linteau.set_opacity(0.30).move_to(vers_scene((g + d) / 2, y))
                for (trou, barre), (cx, bonus) in zip(ouvs, trous):
                    trou.set_opacity(1).move_to(vers_scene(cx, y))
                    barre.set_opacity(0.9).move_to(vers_scene(cx, y + 4))
                    barre.set_fill("#2BE58C" if bonus > 0 else "#FA3B3B")

        portes.add_updater(maj_portes)

        # --- tableau de bord ---------------------------------------------------
        tableau, pastilles = VGroup(), []
        for i in range(2):
            y = 186 + i * 88
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.64))
            nom.scale_to_fit_height(0.30).move_to(vers_scene(92, y),
                                                  aligned_edge=LEFT)
            tableau.add(nom)
            rang = []
            for k in range(VIES + 3):
                c = Circle(radius=20 * ECHELLE, stroke_width=0, fill_opacity=1)
                c.move_to(vers_scene(400 + k * 62, y - 4))
                tableau.add(c)
                rang.append(c)
            pastilles.append(rang)

        def maj_tableau(_):
            etats, _ = instantane(t.get_value())
            for i, rang in enumerate(pastilles):
                for k, c in enumerate(rang):
                    if k < etats[i][1]:
                        c.set_fill(teinte(TEINTES[i], 0.60), opacity=1)
                    else:
                        c.set_fill("#FFFFFF", opacity=0.07)

        tableau.add_updater(maj_tableau)

        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])

        def maj_balles(_):
            etats, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                b.move_to(vers_scene(etats[i][0], Y_BALLE))
                b.set_opacity(1 if etats[i][2] else 0)

        balles.add_updater(maj_balles)

        cloison = Rectangle(width=CLOISON * ECHELLE, height=(Y1 - Y0) * ECHELLE,
                            stroke_width=0, fill_color="#8CA8BE", fill_opacity=0.35)
        cloison.move_to(vers_scene(MARGE + LARG + CLOISON / 2, (Y0 + Y1) / 2))
        cadre = Rectangle(width=(W - 2 * MARGE) * ECHELLE,
                          height=(Y1 - Y0) * ECHELLE, stroke_color="#8CA8BE",
                          stroke_width=6, stroke_opacity=0.35, fill_opacity=0)
        cadre.move_to(vers_scene(W / 2, (Y0 + Y1) / 2))

        restantes = IMAGES[-1][0][VAINQUEUR][1]
        voile, bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "%d vie%s en poche" % (restantes, "s" if restantes > 1 else ""),
            t, FIN)

        self.add(accroche("qui tombera à court de vies ?"), tableau, fonds,
                 portes, balles, cloison, cadre, voile, bloc)

        if AVEC_SON:
            ev = []
            for instant, x, bonus, i in PASSAGES:
                pan = (x - W / 2) / (W / 2)
                if bonus > 0:
                    ev.append((instant, "aigu", 12 + (5 if i else 0), pan, 0.22))
                else:
                    ev.append((instant, "grave", -5 + (5 if i else 0), pan, 0.26))
                    ev.append((instant, "souffle", 300, pan, 0.24))
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "portes.wav"))

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
        LesPortes().render()
