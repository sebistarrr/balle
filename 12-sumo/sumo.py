"""
Sumo — reproduction Manim du duel, format vertical.

Une plateforme ronde, et pas le moindre mur. Les deux balles glissent dans
une cuvette qui les ramène toujours vers le centre : elles se croisent, se
percutent, et un seul choc bien placé suffit à en envoyer une dans le vide. La
première sortie a perdu.

Elles sont lancées en sens de rotation contraires : dans le même sens, la
symétrie centrale les maintiendrait éternellement aux antipodes l'une de
l'autre, et aucun choc n'aurait jamais lieu.

Rendu :
    manim -r 1080,1920 --fps 60 sumo.py Sumo

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python sumo.py --graines` en essaie une série et affiche, pour chacune, la
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
CX, CY = 540, 1040
R0 = 440                    # rayon de l'anneau au départ
R_MIN = 130
RETRECIT = 4.0              # px/s : l'anneau n'est là qu'en dernier recours
R_BALLE = 30
#  Cuvette harmonique : l'accélération vers le centre est proportionnelle à la
#  distance. Les balles oscillent donc à travers le centre et se rencontrent
#  souvent — c'est là tout le sel. Une gravité constante les collerait au fond.
RAIDEUR = 2.6               # s⁻¹ : a = -RAIDEUR² · r
V0 = 520.0
#  Restitution supérieure à 1 : chaque contact ajoute de l'élan, comme deux
#  lutteurs qui se poussent. À restitution 1 l'énergie ne bouge pas, les orbites
#  restent sages, et c'est l'anneau qui finit par trancher à heure fixe.
POUSSEE = 1.03
DT = 1 / 480

NOMS = ("ACIER", "BRAISE")
TEINTES = (205.0, 18.0)

#  Graine 0 : 17,6 s, BRAISE éjectée en dernier — le plus long des six essais.
GRAINE = 0


def anneau(t):
    return max(R_MIN, R0 - RETRECIT * t)


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    a0 = rng.uniform(0, TAU)
    balles = []
    for i in range(2):
        ou = a0 + i * PI
        #  Diamétralement opposées, mais lancées en sens de rotation
        #  contraires : elles se croisent alors deux fois par tour. Dans le même
        #  sens, la symétrie centrale les maintient éternellement aux antipodes
        #  et elles ne se touchent jamais.
        sens = -1 if i else 1
        k = rng.uniform(0.85, 1.15)
        balles.append({"i": i, "vivant": 1,
                       "x": CX + np.cos(ou) * R0 * 0.45,
                       "y": CY + np.sin(ou) * R0 * 0.45,
                       "vx": -np.sin(ou) * V0 * k * sens,
                       "vy": np.cos(ou) * V0 * k * sens})

    t = 0.0
    images, chocs = [], []
    prochaine = 0.0
    vainqueur = -1

    def dist(b):
        return np.sqrt((b["x"] - CX) ** 2 + (b["y"] - CY) ** 2)

    def instantane():
        bord = anneau(t)
        return (tuple((b["x"], b["y"], b["vivant"],
                       min(1.0, dist(b) / bord)) for b in balles), bord)

    while vainqueur < 0 and t < 90.0:
        t += DT
        bord = anneau(t)
        for b in balles:
            if not b["vivant"]:
                continue
            #  Rappel vers le centre, proportionnel à l'écart : c'est la pente
            #  de la cuvette. Rien ne retient la balle au bord — pas de mur.
            b["vx"] -= RAIDEUR * RAIDEUR * (b["x"] - CX) * DT
            b["vy"] -= RAIDEUR * RAIDEUR * (b["y"] - CY) * DT
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            if dist(b) > bord:
                b["vivant"] = 0
                vainqueur = 1 - b["i"]
                break

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
                    j = -(1 + POUSSEE) * vn / 2
                    a["vx"] -= j * nx; a["vy"] -= j * ny
                    b["vx"] += j * nx; b["vy"] += j * ny
                    force = min(1.0, abs(vn) / 1200)
                    chocs.append((t, (a["x"] + b["x"]) / 2,
                                  (a["y"] + b["y"]) / 2, force))

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
class Sumo(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        #  La plateforme : un disque plein avec un liseré clair, et des cercles
        #  concentriques qui donnent la pente de la cuvette. Ce qui est dehors
        #  est le vide, et doit se lire comme tel.
        plateau = VGroup(
            Circle(radius=R0 * ECHELLE, stroke_color="#BED7E6", stroke_width=8,
                   stroke_opacity=0.55, fill_color="#141C24", fill_opacity=1),
            *[Circle(radius=R0 * k / 5 * ECHELLE, stroke_color="#BED7E6",
                     stroke_width=2, stroke_opacity=0.10, fill_opacity=0)
              for k in range(1, 5)])
        plateau.move_to(vers_scene(CX, CY))

        def maj_plateau(g):
            _, bord = instantane(t.get_value())
            for k, m in enumerate(g):
                r = bord if k == 0 else bord * k / 5
                m.set(width=2 * r * ECHELLE)
                m.move_to(vers_scene(CX, CY))

        plateau.add_updater(maj_plateau)

        # --- jauges de danger --------------------------------------------------
        #  La jauge n'est pas une vie mais une position : à quelle distance du
        #  vide se trouve chaque balle. Elle bouge en permanence.
        jauges, remplis = VGroup(), []
        for i in range(2):
            y = 186 + i * 92
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.62))
            nom.scale_to_fit_height(0.32).move_to(vers_scene(92, y),
                                                  aligned_edge=LEFT)
            fond_j = RoundedRectangle(width=480 * ECHELLE, height=26 * ECHELLE,
                                      corner_radius=13 * ECHELLE, stroke_width=0,
                                      fill_color="#FFFFFF", fill_opacity=0.08)
            fond_j.move_to(vers_scene(420 + 240, y - 5))
            plein = RoundedRectangle(width=10 * ECHELLE, height=26 * ECHELLE,
                                     corner_radius=13 * ECHELLE, stroke_width=0,
                                     fill_color=teinte(TEINTES[i], 0.58),
                                     fill_opacity=1)
            jauges.add(nom, fond_j, plein)
            remplis.append(plein)

        def maj_jauges(_):
            etats, _ = instantane(t.get_value())
            for i, plein in enumerate(remplis):
                part = etats[i][3] if etats[i][2] else 1.0
                larg = max(10, 480 * part)
                #  Au-delà de 80 % du rayon, la jauge passe au rouge : c'est le
                #  moment où un choc devient fatal.
                col = teinte(8 if part > 0.8 else TEINTES[i], 0.58)
                plein.become(RoundedRectangle(
                    width=larg * ECHELLE, height=26 * ECHELLE,
                    corner_radius=13 * ECHELLE, stroke_width=0,
                    fill_color=col, fill_opacity=1))
                plein.move_to(vers_scene(420 + larg / 2, 186 + i * 92 - 5))

        jauges.add_updater(maj_jauges)

        balles = VGroup(*[balle_mobject(TEINTES[i], R_BALLE) for i in range(2)])

        def maj_balles(_):
            etats, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                b.move_to(vers_scene(etats[i][0], etats[i][1]))
                b.set_opacity(1 if etats[i][2] else 0)

        balles.add_updater(maj_balles)

        voile, bloc = bandeau_fin(NOMS[VAINQUEUR],
                                  teinte(TEINTES[VAINQUEUR], 0.64),
                                  "l'autre est passée par-dessus bord", t, FIN)

        self.add(accroche("qui sortira de l'anneau ?"), jauges, plateau,
                 balles, voile, bloc)

        if AVEC_SON:
            ev = [(instant, "grave", round(force * 12), (x - CX) / R0,
                   0.14 + 0.26 * force)
                  for instant, x, y, force in CHOCS]
            ev += [(FIN, "souffle", 150, 0.0, 0.5)]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "sumo.wav"))

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
        Sumo().render()
