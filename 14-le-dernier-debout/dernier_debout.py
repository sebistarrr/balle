"""
Le dernier debout — reproduction Manim du duel, format vertical.

Huit balles de taille identique dans une arène close. À chaque contact, la
plus grosse arrache un morceau de la plus petite. Sous un certain rayon, on
éclate. Il n'en restera qu'une.

À taille égale un choc ne transfère rien : c'est ce qui rend les premières
secondes indécises. Dès qu'un écart se crée il s'amplifie de lui-même.

Rendu :
    manim -r 1080,1920 --fps 60 dernier_debout.py DernierDebout

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python dernier_debout.py --graines` en essaie une série et affiche, pour chacune, la
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
CX, CY, R = 540, 1080, 462
N = 8                       # concurrentes au départ
R_DEPART = 34.0
R_MORT = 13.0               # en deçà, la balle éclate
V0 = 620.0
#  Ce qu'un choc transfère : une part du rayon du plus petit passe au plus gros.
#  La part grandit avec le temps, sinon les dernières survivantes se rendraient
#  coup pour coup indéfiniment.
TRANSFERT0 = 0.07
TRANSFERT_ACCEL = 0.018
DT = 1 / 480

TEINTES = (8.0, 40.0, 96.0, 152.0, 196.0, 236.0, 282.0, 322.0)
NOMS = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")

#  Graine 2 : 21,8 s, la sixième l'emporte.
GRAINE = 2


def transfert(t):
    return TRANSFERT0 + TRANSFERT_ACCEL * t


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    a0 = rng.uniform(0, TAU)
    balles = []
    for i in range(N):
        #  Réparties en cercle à intervalles réguliers, toutes du même rayon :
        #  aucune ne commence avantagée. Seule la direction est tirée au sort.
        ou = a0 + i * TAU / N
        cap = rng.uniform(0, TAU)
        balles.append({"i": i, "vivant": 1, "r": R_DEPART,
                       "x": CX + np.cos(ou) * R * 0.62,
                       "y": CY + np.sin(ou) * R * 0.62,
                       "vx": np.cos(cap) * V0, "vy": np.sin(cap) * V0})

    t = 0.0
    images, chocs, morts = [], [], []
    prochaine = 0.0
    vainqueur = -1

    def instantane():
        return (tuple((b["x"], b["y"], b["r"], b["vivant"]) for b in balles),)

    while vainqueur < 0 and t < 120.0:
        t += DT
        for b in balles:
            if not b["vivant"]:
                continue
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            dx, dy = b["x"] - CX, b["y"] - CY
            d = np.sqrt(dx * dx + dy * dy)
            if d > R - b["r"]:
                nx, ny = dx / d, dy / d
                b["x"] = CX + nx * (R - b["r"])
                b["y"] = CY + ny * (R - b["r"])
                p = 2 * (b["vx"] * nx + b["vy"] * ny)
                b["vx"] -= p * nx
                b["vy"] -= p * ny
                s = np.sqrt(b["vx"] ** 2 + b["vy"] ** 2)
                b["vx"] *= V0 / s
                b["vy"] *= V0 / s
                #  La note dépend de la taille : les grosses parlent grave. On
                #  entend donc la hiérarchie se faire.
                demi = int(round(24 * (1 - (b["r"] - R_MORT) / (60 - R_MORT))))
                chocs.append((t, b["x"], demi))

        part = transfert(t)
        for i in range(N):
            a = balles[i]
            if not a["vivant"]:
                continue
            for j in range(i + 1, N):
                b = balles[j]
                if not b["vivant"]:
                    continue
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                dd = np.sqrt(dx * dx + dy * dy)
                mini = a["r"] + b["r"]
                if dd >= mini or dd < 1e-9:
                    continue
                nx, ny = dx / dd, dy / dd
                corr = (mini - dd) / 2
                a["x"] -= nx * corr; a["y"] -= ny * corr
                b["x"] += nx * corr; b["y"] += ny * corr
                vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
                if vn > 0:
                    continue
                a["vx"] += vn * nx; a["vy"] += vn * ny
                b["vx"] -= vn * nx; b["vy"] -= vn * ny
                for m in (a, b):
                    s = np.sqrt(m["vx"] ** 2 + m["vy"] ** 2)
                    if s > 1e-9:
                        m["vx"] *= V0 / s
                        m["vy"] *= V0 / s
                #  Le gros prend au petit. À taille égale, rien ne bouge : c'est
                #  ce qui rend les premiers instants indécis.
                gros, petit = (a, b) if a["r"] >= b["r"] else (b, a)
                pris = petit["r"] * part
                petit["r"] -= pris
                gros["r"] += pris * 0.75   # une part se perd
                if petit["r"] < R_MORT:
                    petit["vivant"] = 0
                    morts.append((t, petit["x"]))
                    reste = [m for m in balles if m["vivant"]]
                    if len(reste) == 1:
                        vainqueur = reste[0]["i"]
                        break
            if vainqueur >= 0:
                break

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, chocs, morts, fin, vainqueur


IMAGES, CHOCS, MORTS, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class DernierDebout(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        arene = Circle(radius=R * ECHELLE, stroke_color="#7896AA",
                       stroke_width=6, stroke_opacity=0.32, fill_opacity=0)
        arene.move_to(vers_scene(CX, CY))

        # --- tableau : huit pastilles à leur taille réelle ---------------------
        #  Huit jauges ne se lisent pas. Les pastilles, si : la hiérarchie
        #  apparaît d'un coup, et les éteintes restent en place pour qu'on voie
        #  qui est tombé.
        tableau = VGroup()
        for i in range(N):
            c = Circle(radius=R_DEPART * 0.62 * ECHELLE, stroke_width=2,
                       fill_opacity=1)
            c.move_to(vers_scene(140 + i * 114, 210))
            tableau.add(c)

        compte = Text("8 en lice", color="#A0B4BE").scale_to_fit_height(0.23)
        compte.move_to(vers_scene(W / 2, 300))
        compte.valeur = N

        def maj_tableau(_):
            (etats,) = instantane(t.get_value())
            vivantes = 0
            for i, c in enumerate(tableau):
                x, y, r, vivant = etats[i]
                if vivant:
                    vivantes += 1
                    c.set(width=2 * max(5, r * 0.62) * ECHELLE)
                    c.move_to(vers_scene(140 + i * 114, 210))
                    c.set_fill(teinte(TEINTES[i], 0.60), opacity=1)
                    c.set_stroke(teinte(TEINTES[i], 0.80), width=2, opacity=0.7)
                else:
                    c.set(width=2 * 10 * ECHELLE)
                    c.move_to(vers_scene(140 + i * 114, 210))
                    c.set_fill("#FFFFFF", opacity=0.08)
                    c.set_stroke(width=0)
            if vivantes != compte.valeur:
                m = Text("%d en lice" % vivantes, color="#A0B4BE")
                m.scale_to_fit_height(0.23).move_to(vers_scene(W / 2, 300))
                compte.become(m)
                compte.valeur = vivantes

        tableau.add_updater(maj_tableau)

        balles = VGroup(*[
            Circle(radius=R_DEPART * ECHELLE, stroke_color="#FFFFFF",
                   stroke_width=2.5, stroke_opacity=0.5,
                   fill_color=teinte(TEINTES[i], 0.62), fill_opacity=1)
            for i in range(N)])
        halos = VGroup(*[
            Circle(radius=R_DEPART * 1.9 * ECHELLE, stroke_width=0,
                   fill_color=teinte(TEINTES[i], 0.58), fill_opacity=0.13)
            for i in range(N)])

        def maj_balles(_):
            (etats,) = instantane(t.get_value())
            for i, b in enumerate(balles):
                x, y, r, vivant = etats[i]
                c = vers_scene(x, y)
                b.set(width=2 * max(1e-3, r) * ECHELLE).move_to(c)
                b.set_opacity(1 if vivant else 0)
                halos[i].set(width=2 * max(1e-3, r) * 1.9 * ECHELLE).move_to(c)
                halos[i].set_fill(opacity=0.13 if vivant else 0)

        balles.add_updater(maj_balles)

        r_fin = IMAGES[-1][0][VAINQUEUR][2]
        voile, bloc = bandeau_fin(
            NOMS[VAINQUEUR], teinte(TEINTES[VAINQUEUR], 0.64),
            "%d px de rayon, contre %d au départ" % (round(r_fin), R_DEPART),
            t, FIN)

        self.add(accroche("laquelle des huit restera ?"), tableau, compte,
                 arene, halos, balles, voile, bloc)

        if AVEC_SON:
            #  Une note sur deux : à huit balles, tout sonner ferait un tapis.
            ev = [(instant, "cloche", demi, (x - CX) / R, 0.12)
                  for k, (instant, x, demi) in enumerate(CHOCS) if k % 2 == 0]
            ev += [(instant, "souffle", 1400, (x - CX) / R, 0.42)
                   for instant, x in MORTS]
            ev += accord_victoire(FIN + 0.15)
            self.add_sound(bande_son(ev, DUREE, "debout.wav"))

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
        DernierDebout().render()
