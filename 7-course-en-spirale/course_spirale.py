"""
Course en spirale — reproduction Manim du duel, format vertical.

Deux balles, deux couloirs en spirale entrelacés. La gravité est dirigée
vers le centre — c'est l'entonnoir des troncs à pièces — et leur couloir les
guide vers le trou. Première arrivée, première gagnante.

Les deux pistes sont la même à un demi-tour près, donc rigoureusement de même
longueur : aucune des deux n'est avantagée.

Rendu :
    manim -r 1080,1920 --fps 60 course_spirale.py CourseSpirale

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python course_spirale.py --graines` en essaie une série et affiche, pour chacune, la
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
CX, CY = 540, 1010
R_EXT = 470                 # rayon de la paroi extérieure au départ
#  Deux couloirs entrelacés, comme les deux départs d'une vis à double filet.
#  Chacune a le sien : dans un couloir partagé assez étroit, on ne double pas,
#  et celle qui part devant gagne à tous les coups. Les deux pistes sont ici la
#  même à un demi-tour près, donc rigoureusement de même longueur.
PAS = 140                   # ce que la spirale gagne par tour
LARGEUR = 56                # largeur d'un couloir
R_TROU = 100                # en deçà, c'est gagné
R_BALLE = 16
THETA_MAX = (R_EXT - LARGEUR / 2 - R_TROU) / PAS * TAU
G = 280.0                   # gravité, dirigée vers le centre
V_MAX = 900.0
AMORTI = 0.999985
REBOND = 0.15               # contact mou : la balle glisse, ne ricoche pas
DT = 1 / 480

NOMS = ("AMBRE", "VIOLET")
TEINTES = (38.0, 282.0)

#  Graine 6 : 11,0 s, VIOLET l'emporte de 1,2 % — la fin la plus serrée des
#  vingt essayées.
GRAINE = 6


def paroi_ext(th, lane):
    return R_EXT - PAS * (th - lane * PI) / TAU


def paroi_int(th, lane):
    return paroi_ext(th, lane) - LARGEUR


def normale_paroi(th, r):
    """Normale à la paroi, dirigée vers l'extérieur.

    Elle n'est pas radiale : la spirale descend de PAS par tour, sa tangente est
    donc inclinée d'environ 5° sur le cercle. Prendre la direction radiale à la
    place annule à chaque pas la composante par laquelle la balle glisse vers
    l'intérieur — c'est-à-dire exactement le travail moteur de la gravité, et la
    course s'arrête au bout de quelques secondes.
    """
    rp = -PAS / TAU
    c, s = np.cos(th), np.sin(th)
    nx, ny = r * c + rp * s, r * s - rp * c
    n = np.sqrt(nx * nx + ny * ny) or 1.0
    return nx / n, ny / n


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    jeu = rng.uniform(0, TAU * 0.15)
    balles = []
    for i in range(2):
        th = i * PI + 0.12 + jeu
        r = paroi_ext(th, i) - LARGEUR / 2
        v = rng.uniform(210, 270)
        balles.append({"i": i, "th": th, "deroule": th, "depart": th,
                       "x": CX + np.cos(th) * r, "y": CY + np.sin(th) * r,
                       "vx": -np.sin(th) * v, "vy": np.cos(th) * v})

    t = 0.0
    images, chocs = [], []
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["y"], min(1.0, (b["deroule"] - b["depart"])
                                           / THETA_MAX)) for b in balles),)

    while vainqueur < 0 and t < 90.0:
        t += DT
        for b in balles:
            dx, dy = b["x"] - CX, b["y"] - CY
            d = np.sqrt(dx * dx + dy * dy) or 1e-9
            b["vx"] -= G * DT * dx / d
            b["vy"] -= G * DT * dy / d
            b["vx"] *= AMORTI
            b["vy"] *= AMORTI
            s = np.sqrt(b["vx"] ** 2 + b["vy"] ** 2)
            if s > V_MAX:
                b["vx"] *= V_MAX / s
                b["vy"] *= V_MAX / s
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT

            #  Angle déroulé : l'angle brut saute de 2π, il faut suivre le
            #  nombre de tours pour savoir sur quelle spire on se trouve.
            brut = np.arctan2(b["y"] - CY, b["x"] - CX)
            ecart = brut - b["th"]
            while ecart > PI:
                ecart -= TAU
            while ecart < -PI:
                ecart += TAU
            b["th"] = brut
            b["deroule"] += ecart

            rr = np.sqrt((b["x"] - CX) ** 2 + (b["y"] - CY) ** 2)
            if rr < R_TROU:
                vainqueur = b["i"]
                break

            ext = paroi_ext(b["deroule"], b["i"]) - R_BALLE
            inte = paroi_int(b["deroule"], b["i"]) + R_BALLE
            choc, nx, ny = 0.0, 0.0, 0.0
            if rr > ext:
                choc = rr - ext
                nx, ny = normale_paroi(b["deroule"], paroi_ext(b["deroule"], b["i"]))
            elif rr < inte:
                choc = rr - inte
                nx, ny = normale_paroi(b["deroule"], paroi_int(b["deroule"], b["i"]))
            if choc != 0.0:
                b["x"] -= nx * choc
                b["y"] -= ny * choc
                vn = b["vx"] * nx + b["vy"] * ny
                b["vx"] -= (1 + REBOND) * vn * nx
                b["vy"] -= (1 + REBOND) * vn * ny
                if abs(vn) > 90:
                    avance = min(1.0, (b["deroule"] - b["depart"]) / THETA_MAX)
                    chocs.append((t, b["i"], avance, (b["x"] - CX) / R_EXT,
                                  min(1.0, abs(vn) / 700)))

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
class CourseSpirale(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- les deux pistes -------------------------------------------------
        pistes = VGroup()
        for i in range(2):
            for rayon in (paroi_ext, paroi_int):
                pts = []
                th = i * PI
                while th <= i * PI + THETA_MAX + 0.3:
                    r = rayon(th, i)
                    pts.append(vers_scene(CX + np.cos(th) * r,
                                          CY + np.sin(th) * r))
                    th += 0.04
                courbe = VMobject(stroke_color=teinte(TEINTES[i], 0.42, 0.6),
                                  stroke_width=6, stroke_opacity=0.55)
                courbe.set_points_as_corners(pts)
                pistes.add(courbe)

        #  Le trou d'arrivée, qui pulse : c'est le but, il doit attirer l'œil.
        trou = VGroup(*[
            Circle(radius=R_TROU * k * ECHELLE, stroke_width=0,
                   fill_color="#33FF99", fill_opacity=o)
            for k, o in ((1, 0.30), (1.32, 0.13), (1.7, 0.06))])
        trou.move_to(vers_scene(CX, CY))

        def maj_trou(g):
            puls = 0.5 + 0.5 * np.sin(t.get_value() * 4)
            for m, o in zip(g, (0.30, 0.13, 0.06)):
                m.set_fill(opacity=o * (0.6 + 0.4 * puls))

        trou.add_updater(maj_trou)

        # --- jauges d'avancement ---------------------------------------------
        jauges, remplis, pourcents = VGroup(), [], []
        for i in range(2):
            y = 176 + i * 92
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.64))
            nom.scale_to_fit_height(0.30)
            nom.move_to(vers_scene(92, y), aligned_edge=LEFT)
            fond_j = RoundedRectangle(width=560 * ECHELLE, height=26 * ECHELLE,
                                      corner_radius=13 * ECHELLE,
                                      stroke_width=0, fill_color="#FFFFFF",
                                      fill_opacity=0.08)
            fond_j.move_to(vers_scene(400 + 280, y - 5))
            plein = RoundedRectangle(width=26 * ECHELLE, height=26 * ECHELLE,
                                     corner_radius=13 * ECHELLE, stroke_width=0,
                                     fill_color=teinte(TEINTES[i], 0.58),
                                     fill_opacity=1)
            pct = Text("0 %", color="#DCE8EE").scale_to_fit_height(0.22)
            pct.move_to(vers_scene(1000, y), aligned_edge=RIGHT)
            pct.rang = -1
            jauges.add(nom, fond_j, plein, pct)
            remplis.append(plein)
            pourcents.append(pct)

        def maj_jauges(_):
            (etats,) = instantane(t.get_value())
            for i, plein in enumerate(remplis):
                a = etats[i][2]
                larg = max(26, 560 * a)
                plein.become(RoundedRectangle(
                    width=larg * ECHELLE, height=26 * ECHELLE,
                    corner_radius=13 * ECHELLE, stroke_width=0,
                    fill_color=teinte(TEINTES[i], 0.58), fill_opacity=1))
                plein.move_to(vers_scene(400 + larg / 2, 176 + i * 92 - 5))
                #  Le texte n'est reconstruit qu'au changement de valeur :
                #  refaire un Text à chaque image coûte cher pour rien.
                rang = int(round(a * 100))
                if rang != pourcents[i].rang:
                    m = Text("%d %%" % rang, color="#DCE8EE")
                    m.scale_to_fit_height(0.22)
                    m.move_to(vers_scene(1000, 176 + i * 92), aligned_edge=RIGHT)
                    pourcents[i].become(m)
                    pourcents[i].rang = rang

        jauges.add_updater(maj_jauges)

        # --- les balles ------------------------------------------------------
        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_BALLE,
                                      ((2.2, 0.16), (3.4, 0.07)))
                         for i in range(2)])

        def maj_balles(_):
            (etats,) = instantane(t.get_value())
            for i, b in enumerate(balles):
                c = vers_scene(etats[i][0], etats[i][1])
                b.move_to(c)
                for anne in halos[i]:
                    anne.move_to(c)

        balles.add_updater(maj_balles)

        ecart = abs(IMAGES[-1][0][0][2] - IMAGES[-1][0][1][2])
        voile, bloc = bandeau_fin(NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
                                  "%d %% d'avance" % round(ecart * 100), t, FIN)

        self.add(accroche("qui touchera le centre en premier ?"), jauges,
                 trou, pistes, halos, balles, voile, bloc)

        if AVEC_SON:
            ev = [(instant, "cloche", round(av * 24) + (7 if i else 0),
                   pan, 0.10 + 0.12 * force)
                  for instant, i, av, pan, force in CHOCS]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "course.wav"))

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
        CourseSpirale().render()
