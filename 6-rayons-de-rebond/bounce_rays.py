"""
Rayons de rebond — reproduction Manim.

Même mécanique que l'animation 5 (récipient en U, balle qui gagne un cran de
rayon chaque fois qu'elle retombe sur le fond), mais le tracé est différent et
c'est lui le sujet : ce n'est pas la trajectoire qui est dessinée. Chaque choc
laisse un point fixe sur la paroi, et à chaque image on relie le centre de la
balle à tous ces points. L'éventail balaie donc l'espace à mesure qu'elle se
déplace, et les traits sont rigoureusement droits.

Rendu :
    manim -r 720,1244 --fps 60 bounce_rays.py BounceRays

Les constantes reprennent celles de la page `index.html` voisine, dans le même
repère pixel (720 x 1244) ; un pixel vaut 0,01 unité de scène.

Un billard sous gravité est chaotique : le pas de temps est fixe, sans quoi
deux rendus de résolution différente ne donneraient pas la même partie.
"""

from manim import *
import colorsys
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#  La résolution vient de la ligne de commande : garder le rapport 720:1244.
#      manim -r 720,1244 --fps 60 bounce_rays.py BounceRays
# --------------------------------------------------------------------------
config.frame_width = 7.20
config.frame_height = 12.44
config.background_color = "#000000"

# --------------------------------------------------------------------------
#  Réglages, en pixels du repère d'origine
# --------------------------------------------------------------------------
W, H = 720, 1244
CX, RC = 360, 275          # axe et demi-largeur du récipient
HAUT = 340                 # sommet des parois
ARC_CY = 615               # centre du demi-cercle du fond
R0 = 13                    # rayon de départ
G = 6500                   # gravité, px/s²
SOMMET = 500               # le centre de la balle ne monte jamais au-dessus
PAS_RAYON = 1.3            # ce que gagne le rayon à chaque fond touché
GAIN = 1.004               # et ce que gagne sa vitesse, jusqu'au plafond
DT = 1 / 480               # pas de la simulation
ECH = 60                   # points de trajectoire enregistrés par seconde
ATTENTE = 1.5              # pause une fois le récipient rempli

TEINTE_DEPART = 268
TEINTE_PAR_S = 36          # la couleur tourne avec le temps...
TEINTE_PAR_CHOC = 4        # ...et d'un cran à chaque choc

AVEC_SON = True

#  Conversion du repère pixel (origine en haut à gauche, y vers le bas) vers
#  celui de la scène (origine au centre, y vers le haut).
ECHELLE = 0.01


def vers_scene(x, y):
    return np.array([(x - CX) * ECHELLE, (H / 2 - y) * ECHELLE, 0.0])


def teinte_en_couleur(h):
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, 0.55, 1.0)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))


# --------------------------------------------------------------------------
#  Simulation : on joue toute la partie d'avance, puis on relit.
# --------------------------------------------------------------------------
def simuler():
    """Renvoie (temps, chemin, rayons, teintes, chocs, duree).

    temps, chemin, rayons, teintes : échantillons de la trajectoire, à la
    cadence ECH plus un point exact à chaque choc.
    chocs : (instant, x, y, remplissage) — pour la bande son.
    """
    x, y = CX + 40, float(SOMMET)
    vx, vy = 650.0, 0.0
    r = float(R0)
    teinte = float(TEINTE_DEPART)
    t = 0.0

    temps, chemin, rayons, teintes, chocs = [0.0], [(x, y)], [r], [teinte], []
    impacts = []                     # (instant, point touché sur la paroi)
    prochain = 1 / ECH

    while r < RC - 1e-9 and t < 300:
        vy += G * DT
        x += vx * DT
        y += vy * DT
        t += DT
        teinte -= TEINTE_PAR_S * DT

        touche, nx, ny, fond = False, 0.0, 0.0, False
        if y >= ARC_CY:                                  # fond arrondi
            # sqrt(dx*dx+dy*dy) et non hypot : hypot n'a pas d'arrondi
            # spécifié, il diffère d'un langage à l'autre, et sur un
            # système chaotique cela suffit à faire diverger ce script
            # de la page web.
            dx, dy = x - CX, y - ARC_CY
            d = np.sqrt(dx * dx + dy * dy)
            if d > RC - r:
                nx, ny = dx / d, dy / d
                x, y = CX + nx * (RC - r), ARC_CY + ny * (RC - r)
                touche = fond = True
        elif x < CX - RC + r:                            # paroi gauche
            x, nx, touche = CX - RC + r, -1.0, True
        elif x > CX + RC - r:                            # paroi droite
            x, nx, touche = CX + RC - r, 1.0, True

        if touche:
            #  Le point touché. Le centre est à RC - r du centre du fond, donc
            #  le contact tombe à RC pile : il est sur le tracé du récipient.
            impacts.append((t, CX + nx * RC,
                            ARC_CY + ny * RC if fond else y))
            p = 2 * (vx * nx + vy * ny)
            vx -= p * nx
            vy -= p * ny                                 # rebond élastique
            teinte -= TEINTE_PAR_CHOC
            if fond:
                r = min(RC, r + PAS_RAYON)
                vx *= GAIN
                vy *= GAIN
            # On repose la balle sur la paroi APRÈS l'avoir fait grossir. Sans
            # cela elle la chevauche encore d'un cran, le choc se redéclenche au
            # pas suivant, et ce doublon aléatoire rend la partie imprévisible.
            x = CX + nx * (RC - r)
            if fond:
                y = ARC_CY + ny * (RC - r)
            # l'énergie est bornée : sans cela la balle sortirait par le haut
            vmax = np.sqrt(max(0.0, 2 * G * (y - SOMMET)))
            s = np.sqrt(vx * vx + vy * vy)
            if s > vmax > 0:
                vx *= vmax / s
                vy *= vmax / s
            chocs.append((t, (r - R0) / (RC - R0)))
            temps.append(t); chemin.append((x, y)); rayons.append(r); teintes.append(teinte)

        if t >= prochain:
            temps.append(t); chemin.append((x, y)); rayons.append(r); teintes.append(teinte)
            prochain += 1 / ECH

    # le récipient est plein : la balle se cale au fond et marque un temps
    for u in (t + 1e-3, t + ATTENTE):
        temps.append(u); chemin.append((CX, ARC_CY)); rayons.append(float(RC))
        teintes.append(teinte - TEINTE_PAR_S * (u - t))

    return (np.array(temps), np.array(chemin), np.array(rayons),
            np.array(teintes), chocs, np.array(impacts), temps[-1])


TEMPS, CHEMIN, RAYONS, TEINTES, CHOCS, IMPACTS, DUREE = simuler()
#  Trajectoire déjà convertie dans le repère de la scène : on ne la recalcule
#  pas à chaque image, la trace peut compter plusieurs milliers de points.
CHEMIN_SCENE = np.stack([
    (CHEMIN[:, 0] - CX) * ECHELLE,
    (H / 2 - CHEMIN[:, 1]) * ECHELLE,
    np.zeros(len(CHEMIN)),
], axis=1)


IMPACTS_T = IMPACTS[:, 0]
IMPACTS_SCENE = np.stack([
    (IMPACTS[:, 1] - CX) * ECHELLE,
    (H / 2 - IMPACTS[:, 2]) * ECHELLE,
    np.zeros(len(IMPACTS)),
], axis=1)


def indice(t):
    return int(np.searchsorted(TEMPS, t, side="right"))


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class BounceRays(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        def teinte_courante():
            i = min(indice(t.get_value()), len(TEINTES) - 1)
            return teinte_en_couleur(TEINTES[i])

        # --- légende ---------------------------------------------------------
        legende = VGroup(
            Text("plus grosse à chaque rebond,", font_size=25, color=WHITE),
            Text("sous gravité", font_size=25, color=WHITE),
        ).arrange(DOWN, buff=0.14)
        legende.move_to(vers_scene(CX, 228))

        # --- le récipient ------------------------------------------------------
        #  Une seule courbe : paroi gauche, demi-cercle du fond, paroi droite.
        pts = [vers_scene(CX - RC, HAUT), vers_scene(CX - RC, ARC_CY)]
        for k in range(181):
            a = np.pi - np.pi * k / 180          # de la gauche vers la droite
            pts.append(vers_scene(CX + RC * np.cos(a), ARC_CY + RC * np.sin(a)))
        pts += [vers_scene(CX + RC, ARC_CY), vers_scene(CX + RC, HAUT)]
        recipient = VMobject(stroke_width=3).set_points_as_corners(pts)
        recipient.add_updater(lambda m: m.set_stroke(color=teinte_courante()))

        # --- les rayons : du centre de la balle vers chaque impact -------------
        #  Une seule courbe en zigzag centre -> impact -> centre -> impact...
        #  Chaque rayon est donc parcouru deux fois, ce qui ne se voit pas, et
        #  cela évite d'avoir à gérer des centaines de tracés séparés.
        rayons = VMobject(stroke_width=1.4)

        def maj_rayons(m):
            tv = t.get_value()
            n = int(np.searchsorted(IMPACTS_T, tv, side="right"))
            if n == 0:
                m.set_stroke(opacity=0)
                return
            centre = CHEMIN_SCENE[min(indice(tv), len(CHEMIN_SCENE) - 1)]
            zigzag = np.empty((2 * n, 3))
            zigzag[0::2] = centre
            zigzag[1::2] = IMPACTS_SCENE[:n]
            m.set_points_as_corners(zigzag)
            m.set_stroke(color=teinte_courante(), width=1.4, opacity=1)

        rayons.add_updater(maj_rayons)

        # --- la balle, par-dessus ----------------------------------------------
        balle = Circle(radius=1.0, stroke_width=0, fill_opacity=1)

        def maj_balle(m):
            i = min(indice(t.get_value()), len(RAYONS) - 1)
            m.width = 2 * RAYONS[i] * ECHELLE
            m.move_to(CHEMIN_SCENE[i])
            m.set_fill(teinte_courante())

        balle.add_updater(maj_balle)

        # --- avancement ---------------------------------------------------------
        gauche = vers_scene(CX - RC, H - 150)
        rail = Line(gauche, vers_scene(CX + RC, H - 150),
                    stroke_width=3, stroke_color=WHITE, stroke_opacity=0.12)
        jauge = Line(gauche, gauche, stroke_width=3)

        def maj_jauge(m):
            i = min(indice(t.get_value()), len(RAYONS) - 1)
            p = (RAYONS[i] - R0) / (RC - R0)
            m.put_start_and_end_on(gauche, gauche + RIGHT * max(1e-3, 2 * RC * ECHELLE * p))
            m.set_stroke(color=teinte_courante())

        jauge.add_updater(maj_jauge)

        self.add(legende, recipient, rail, jauge, rayons, balle)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par choc (facultatif)
# --------------------------------------------------------------------------
def generer_bande_son(chemin="rayons.wav", sr=44100):
    """Note à chaque choc, d'autant plus grave que la balle est grosse.

    Vers la fin les chocs se comptent par dizaines par seconde : on n'en garde
    que quelques-uns par tranche, sinon le mélange sature en bruit.
    """
    import wave

    n = int((DUREE + 2.0) * sr)
    buf = np.zeros(n)

    demi_tons = [0, 3, 5, 7, 10]
    notes = [165.0 * 2 ** ((demi_tons[i % 5] + 12 * (i // 5)) / 12)
             for i in range(16)][::-1]

    dernier, garde = -1.0, []
    for instant, p in CHOCS:
        if instant - dernier < 0.06:      # au plus ~16 notes par seconde
            continue
        dernier = instant
        garde.append((instant, p))

    for instant, p in garde:
        f = notes[min(len(notes) - 1, int(p * len(notes)))]
        i0 = int(instant * sr)
        env_len = int(1.0 * sr)
        tt = np.arange(env_len) / sr
        env = np.exp(-4.5 * tt) * (1 - np.exp(-tt / 0.004))
        onde = np.sin(TAU * f * tt) + 0.25 * np.sin(TAU * 2 * f * tt)
        fin = min(i0 + env_len, n)
        buf[i0:fin] += 0.20 * (onde * env)[: fin - i0]

    buf = np.tanh(buf * 1.2)
    pcm = (buf / max(1e-9, np.abs(buf).max()) * 0.9 * 32767).astype("<i2")

    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Lancement direct : python growing_bounce.py
    config.pixel_width, config.pixel_height = 720, 1244
    config.frame_rate = 60
    BounceRays().render()
