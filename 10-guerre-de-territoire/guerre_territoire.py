"""
Guerre de territoire — reproduction Manim du duel, format vertical.

Le terrain est coupé en deux, et chaque balle est lâchée dans le camp
adverse. Toute case qu'elle touche change de camp et la renvoie ailleurs. Le
premier camp effacé a perdu.

Passé douze secondes, la marée monte : le camp en retard perd du terrain tout
seul, de plus en plus vite. Sans elle la partie ne se décide jamais — les deux
camps s'équilibrent autour de 50 % et y restent.

Rendu :
    manim -r 1080,1920 --fps 60 guerre_territoire.py GuerreTerritoire

La partie est jouée d'avance avec un tirage ensemencé, puis relue image par
image : deux rendus donnent exactement le même film. GRAINE choisit le duel —
`python guerre_territoire.py --graines` en essaie une série et affiche, pour chacune, la
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
COLS, RANGS = 20, 24
LC, LR = (X1 - X0) / COLS, (Y1 - Y0) / RANGS
R_BALLE = 22
V0 = 560.0
V_MONTE = 26.0
V_PLAFOND = 1500.0
#  Déviation tirée au sort à chaque case prise et à chaque mur. Sans elle, la
#  balle ne fait que changer le signe de ses composantes : sa direction reste
#  coincée sur quatre valeurs, elle parcourt un damier fixe, et les dernières
#  cases d'un coin ne sont jamais atteintes.
DEVIATION = 0.16
#  La marée. Passé ce délai, le camp en retard perd du terrain tout seul, de
#  plus en plus vite. Sans elle la partie ne se décide jamais : les deux camps
#  s'équilibrent autour de 50 % et y restent.
MAREE = 12.0
MAREE_TAUX = 40.0
DT = 1 / 480

NOMS = ("OCÉAN", "ORANGE")
TEINTES = (202.0, 26.0)

#  Graine 4 : 17,9 s, OCÉAN l'emporte. La plus longue des huit essayées.
GRAINE = 4

SONDES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def vitesse_de(comptes, i, t):
    """Celle qui mène frappe plus vite, donc creuse l'écart."""
    return min(V_PLAFOND,
               V0 * (0.55 + 1.3 * comptes[i] / (COLS * RANGS)) + V_MONTE * t)


# --------------------------------------------------------------------------
#  Simulation
# --------------------------------------------------------------------------
def simuler(graine):
    rng = np.random.default_rng(graine)
    terrain = np.zeros((RANGS, COLS), dtype=np.uint8)
    terrain[:, COLS // 2:] = 1
    comptes = [COLS * RANGS // 2, COLS * RANGS // 2]

    balles = []
    for i in range(2):
        a = PI / 4 + rng.uniform(0, PI / 2)
        #  Lancée vers le camp adverse, pas vers le sien : dans l'autre sens
        #  elle traverse tout de suite son propre terrain et la partie démarre
        #  à vide.
        balles.append({"i": i,
                       "x": X0 + (X1 - X0) * (0.25 if i else 0.75),
                       "y": (Y0 + Y1) / 2 + (-1 if i else 1) * (Y1 - Y0) * 0.18,
                       "vx": (-1 if i else 1) * np.cos(a) * V0,
                       "vy": (-1 if i else 1) * np.sin(a) * V0})

    t = 0.0
    images, prises = [], []
    prochaine = 0.0
    dette = 0.0
    vainqueur = -1

    def devier(b):
        v = vitesse_de(comptes, b["i"], t)
        a = rng.uniform(-DEVIATION, DEVIATION)
        ca, sa = np.cos(a), np.sin(a)
        vx = b["vx"] * ca - b["vy"] * sa
        vy = b["vx"] * sa + b["vy"] * ca
        s = np.sqrt(vx * vx + vy * vy)
        if s > 1e-9:
            b["vx"], b["vy"] = vx * v / s, vy * v / s

    def instantane():
        return (tuple((b["x"], b["y"]) for b in balles),
                terrain.copy(), tuple(comptes))

    def montee():
        #  Une case du camp en retard, prise au hasard, passe à l'autre camp.
        #  Au hasard plutôt qu'au front : le camp ne recule pas, il se délite.
        nonlocal vainqueur
        perdant = 0 if comptes[0] < comptes[1] else 1
        gagnant = 1 - perdant
        if comptes[perdant] <= 0:
            return
        idx = np.argwhere(terrain == perdant)
        r, c = idx[rng.integers(len(idx))]
        terrain[r, c] = gagnant
        comptes[gagnant] += 1
        comptes[perdant] -= 1
        prises.append((t, X0 + (c + 0.5) * LC, gagnant))
        if comptes[perdant] <= 0:
            vainqueur = gagnant

    while vainqueur < 0 and t < 120.0:
        t += DT
        if t > MAREE:
            dette += MAREE_TAUX * (1 + (t - MAREE) * 0.9) * DT
            while dette >= 1 and vainqueur < 0:
                dette -= 1
                montee()
            if vainqueur >= 0:
                break

        for b in balles:
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            mur = False
            if b["x"] < X0 + R_BALLE:
                b["x"] = X0 + R_BALLE; b["vx"] = abs(b["vx"]); mur = True
            if b["x"] > X1 - R_BALLE:
                b["x"] = X1 - R_BALLE; b["vx"] = -abs(b["vx"]); mur = True
            if b["y"] < Y0 + R_BALLE:
                b["y"] = Y0 + R_BALLE; b["vy"] = abs(b["vy"]); mur = True
            if b["y"] > Y1 - R_BALLE:
                b["y"] = Y1 - R_BALLE; b["vy"] = -abs(b["vy"]); mur = True
            if mur:
                devier(b)

            pris = False
            for sx, sy in SONDES:
                px, py = b["x"] + sx * R_BALLE, b["y"] + sy * R_BALLE
                if px < X0 or px >= X1 or py < Y0 or py >= Y1:
                    continue
                c, r = int((px - X0) // LC), int((py - Y0) // LR)
                if terrain[r, c] == b["i"]:
                    continue
                terrain[r, c] = b["i"]
                comptes[b["i"]] += 1
                comptes[1 - b["i"]] -= 1
                pris = True
                if sx:
                    b["vx"] = -sx * abs(b["vx"])
                if sy:
                    b["vy"] = -sy * abs(b["vy"])
                prises.append((t, X0 + (c + 0.5) * LC, b["i"]))
                if comptes[1 - b["i"]] <= 0:
                    vainqueur = b["i"]
                    break
            if vainqueur >= 0:
                break
            if pris:
                devier(b)

        if t >= prochaine:
            images.append(instantane())
            prochaine += 1 / FPS_ECH

    fin = t
    while prochaine < fin + APRES + 0.5:
        images.append(instantane())
        prochaine += 1 / FPS_ECH
    return images, prises, fin, vainqueur


IMAGES, PRISES, FIN, VAINQUEUR = simuler(GRAINE)
DUREE = FIN + APRES


def instantane(t):
    return IMAGES[min(int(t * FPS_ECH), len(IMAGES) - 1)]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class GuerreTerritoire(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        #  Une case = un carré. Quatre cent quatre-vingts objets, mais ils ne
        #  changent que de couleur : Manim s'en accommode.
        cases = VGroup()
        for r in range(RANGS):
            for c in range(COLS):
                m = Square(side_length=(LC - 2) * ECHELLE, stroke_width=0,
                           fill_opacity=1)
                m.stretch_to_fit_height((LR - 2) * ECHELLE)
                m.move_to(vers_scene(X0 + (c + 0.5) * LC, Y0 + (r + 0.5) * LR))
                cases.add(m)

        couleurs = [teinte(TEINTES[i], 0.26, 0.62) for i in range(2)]

        def maj_cases(g):
            _, terrain, _ = instantane(t.get_value())
            plat = terrain.reshape(-1)
            for k, m in enumerate(g):
                m.set_fill(couleurs[plat[k]], opacity=1)

        cases.add_updater(maj_cases)

        cadre = Rectangle(width=(X1 - X0) * ECHELLE, height=(Y1 - Y0) * ECHELLE,
                          stroke_color="#8CAABE", stroke_width=5,
                          stroke_opacity=0.22, fill_opacity=0)
        cadre.move_to(vers_scene((X0 + X1) / 2, (Y0 + Y1) / 2))

        # --- jauges -----------------------------------------------------------
        jauges, remplis, pourcents = VGroup(), [], []
        for i in range(2):
            y = 180 + i * 88
            nom = Text(NOMS[i], weight=BOLD, color=teinte(TEINTES[i], 0.62))
            nom.scale_to_fit_height(0.30).move_to(vers_scene(92, y),
                                                  aligned_edge=LEFT)
            fond_j = RoundedRectangle(width=500 * ECHELLE, height=26 * ECHELLE,
                                      corner_radius=13 * ECHELLE, stroke_width=0,
                                      fill_color="#FFFFFF", fill_opacity=0.08)
            fond_j.move_to(vers_scene(380 + 250, y - 5))
            plein = RoundedRectangle(width=250 * ECHELLE, height=26 * ECHELLE,
                                     corner_radius=13 * ECHELLE, stroke_width=0,
                                     fill_color=teinte(TEINTES[i], 0.56),
                                     fill_opacity=1)
            pct = Text("50 %", color="#DCE8EE").scale_to_fit_height(0.22)
            pct.move_to(vers_scene(1005, y), aligned_edge=RIGHT)
            pct.rang = -1
            jauges.add(nom, fond_j, plein, pct)
            remplis.append(plein)
            pourcents.append(pct)

        def maj_jauges(_):
            _, _, comptes = instantane(t.get_value())
            total = COLS * RANGS
            for i, plein in enumerate(remplis):
                part = comptes[i] / total
                larg = max(6, 500 * part)
                plein.become(RoundedRectangle(
                    width=larg * ECHELLE, height=26 * ECHELLE,
                    corner_radius=13 * ECHELLE, stroke_width=0,
                    fill_color=teinte(TEINTES[i], 0.56), fill_opacity=1))
                plein.move_to(vers_scene(380 + larg / 2, 180 + i * 88 - 5))
                rang = int(round(part * 100))
                if rang != pourcents[i].rang:
                    m = Text("%d %%" % rang, color="#DCE8EE")
                    m.scale_to_fit_height(0.22)
                    m.move_to(vers_scene(1005, 180 + i * 88), aligned_edge=RIGHT)
                    pourcents[i].become(m)
                    pourcents[i].rang = rang

        jauges.add_updater(maj_jauges)

        balles = VGroup(*[
            Circle(radius=R_BALLE * ECHELLE, stroke_color="#FFFFFF",
                   stroke_width=2.5, stroke_opacity=0.65,
                   fill_color=teinte(TEINTES[i], 0.72), fill_opacity=1)
            for i in range(2)])
        halos = VGroup(*[halo_mobject(TEINTES[i], R_BALLE,
                                      ((2.0, 0.16), (3.1, 0.07)))
                         for i in range(2)])

        def maj_balles(_):
            etats, _, _ = instantane(t.get_value())
            for i, b in enumerate(balles):
                c = vers_scene(etats[i][0], etats[i][1])
                b.move_to(c)
                for anne in halos[i]:
                    anne.move_to(c)

        balles.add_updater(maj_balles)

        #  Le bandeau « la marée monte » : c'est le moment où le duel bascule,
        #  il faut le dire.
        maree = Text("LA MARÉE MONTE", weight=BOLD, color="#FF6E6E")
        maree.scale_to_fit_height(0.26).move_to(vers_scene(W / 2, H - 90))

        def maj_maree(m):
            u = t.get_value()
            m.set_opacity(1.0 if MAREE < u < FIN else 0.0)

        maree.add_updater(maj_maree)

        voile, bloc = bandeau_fin(NOMS[VAINQUEUR],
                                  teinte(TEINTES[VAINQUEUR], 0.64),
                                  "terrain conquis en entier", t, FIN)

        self.add(accroche("quel camp va disparaître ?"), jauges, cases, cadre,
                 halos, balles, maree, voile, bloc)

        if AVEC_SON:
            #  Une note toutes les six prises : à quarante cases par seconde
            #  pendant la marée, tout sonner ferait un mur de bruit.
            ev = [(instant, "cloche", (0, 3, 7, 10, 12)[k % 5] + (12 if i else 0),
                   (x - W / 2) / (W / 2), 0.13)
                  for k, (instant, x, i) in enumerate(PRISES) if k % 6 == 0]
            ev += accord_victoire(FIN + 0.15, VAINQUEUR == 1)
            self.add_sound(bande_son(ev, DUREE, "territoire.wav"))

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
        GuerreTerritoire().render()
