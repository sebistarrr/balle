"""
Billard en boucle — reproduction Manim.

Douze balles dans un carré, sans frottement. Sur chaque axe le mouvement est
une onde triangulaire ; en imposant un nombre *entier* d'allers-retours par axe
et par cycle, la trajectoire se referme — une figure de Lissajous polygonale.
Les balles se traversent : c'est la condition pour que la boucle reste exacte.

Rendu :
    manim -r 1080,1080 --fps 60 billiard_loop.py BilliardLoop

Les constantes sont celles de la page `index.html` voisine, converties du
repère pixel (1000x1000) au repère de scène (8x8) : un pixel vaut 0,008 unité.
"""

from manim import *
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#      manim -r 1080,1080 --fps 60 billiard_loop.py BilliardLoop
# --------------------------------------------------------------------------
config.frame_width = 8.0
config.frame_height = 8.0
config.background_color = "#020306"

# --------------------------------------------------------------------------
#  Réglages
# --------------------------------------------------------------------------
COTE = 6.848            # côté du carré (856 px sur 1000)
RAYON = 0.12            # rayon d'une balle (15 px)
CYCLE = 12.0            # s — au bout de ce temps tout se resynchronise
DUREE = 24.0            # s à rendre : deux cycles

#  [allers-retours horizontaux, verticaux] par cycle. Des entiers, donc des
#  trajectoires fermées ; premiers entre eux ou non, la figure change.
PAIRES = [(3, 4), (4, 3), (3, 5), (5, 3), (4, 5), (5, 4),
          (5, 6), (6, 5), (3, 7), (7, 3), (5, 7), (7, 5)]
N_BALLES = len(PAIRES)
PHASES = [(k * 0.083, k * 0.137) for k in range(N_BALLES)]

AMPLITUDE = COTE - 2 * RAYON        # course du centre d'une balle
MEMOIRE = 1.1                       # longueur de la traînée, en secondes
VIE_ONDE = 0.59                     # durée d'une onde de choc

MONTRER_TRAJETS = False             # tracer les courbes fermées en fond

PALETTE = ["#F56E51", "#F9B060", "#49C4B9", "#1F99D0"]
COULEURS = color_gradient(PALETTE, N_BALLES)

AVEC_SON = True


# --------------------------------------------------------------------------
#  Cinématique
# --------------------------------------------------------------------------
def triangle(u):
    """Onde triangulaire de période 1 : vaut 1 aux entiers, 0 aux demi-entiers."""
    return 2 * abs(u - np.floor(u) - 0.5)


def position(k, t):
    nx, ny = PAIRES[k]
    px, py = PHASES[k]
    demi = COTE / 2
    return np.array([
        -demi + RAYON + AMPLITUDE * triangle(nx * t / CYCLE + px),
        -demi + RAYON + AMPLITUDE * triangle(ny * t / CYCLE + py),
        0.0,
    ])


def rebonds(jusqu_a):
    """Tous les (instant, k, verticale) où une balle touche une paroi.

    Sur un axe, l'onde triangulaire atteint un extrême à chaque demi-période :
    u entier (paroi haute) ou demi-entier (paroi basse).
    """
    out = []
    for k in range(N_BALLES):
        for axe in (0, 1):
            n, ph = PAIRES[k][axe], PHASES[k][axe]
            m = int(np.floor(ph * 2)) + 1
            while True:
                instant = (m / 2 - ph) * CYCLE / n
                if instant > jusqu_a:
                    break
                if instant >= 0:
                    out.append((instant, k, axe == 0))
                m += 1
    return sorted(out)


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class BilliardLoop(Scene):
    def construct(self):
        t = ValueTracker(0.0)
        demi = COTE / 2

        # --- le carré, qui pulse à chaque bouclage ---------------------------
        cadre = Square(side_length=COTE, stroke_color="#49C4B9", stroke_width=4)

        def pulser(m):
            depuis = t.get_value() % CYCLE          # temps depuis le bouclage
            f = np.clip(1 - depuis / 0.7, 0, 1)
            m.set_stroke(width=4 + 7 * f, opacity=0.35 + 0.6 * f)

        cadre.add_updater(pulser)

        # --- trajectoires complètes (facultatif) -----------------------------
        trajets = VGroup()
        if MONTRER_TRAJETS:
            for k in range(N_BALLES):
                pts = [position(k, i / 1400 * CYCLE) for i in range(1401)]
                trajets.add(VMobject(stroke_color=COULEURS[k], stroke_width=2,
                                     stroke_opacity=0.22).set_points_as_corners(pts))

        # --- balles et halos --------------------------------------------------
        balles, halos = VGroup(), VGroup()
        for k in range(N_BALLES):
            p0 = position(k, 0.0)
            balles.add(Circle(radius=RAYON, fill_color=COULEURS[k],
                              fill_opacity=0.95, stroke_width=0).move_to(p0))
            halos.add(VGroup(*[
                Circle(radius=RAYON * f, fill_color=COULEURS[k],
                       fill_opacity=o, stroke_width=0).move_to(p0)
                for f, o in ((1.6, 0.12), (2.3, 0.06))]))

        def replacer(_):
            u = t.get_value()
            for k in range(N_BALLES):
                p = position(k, u)
                balles[k].move_to(p)
                halos[k].move_to(p)

        groupe = VGroup(halos, balles)
        groupe.add_updater(replacer)

        # --- traînées ---------------------------------------------------------
        #  On lit la position par une fonction dédiée plutôt que par
        #  balles[k].get_center : selon l'ordre des updaters, la traînée
        #  accuserait sinon une image de retard.
        trainees = VGroup()
        for k in range(N_BALLES):
            trainees.add(TracedPath(
                (lambda kk=k: position(kk, t.get_value())),
                dissipating_time=MEMOIRE,
                stroke_color=COULEURS[k], stroke_width=6))

        # --- ondes de choc : une par rebond, créées d'avance ------------------
        ondes = VGroup()
        for instant, k, _ in rebonds(DUREE):
            centre = position(k, instant)
            onde = Circle(radius=1.0, stroke_width=6, stroke_color=COULEURS[k])
            onde.move_to(centre)

            def souffle(m, t0=instant, c=centre):
                age = t.get_value() - t0
                if age < 0 or age > VIE_ONDE:
                    m.set_stroke(opacity=0)
                    return
                vie = 1 - age / VIE_ONDE
                m.width = 2 * (RAYON + 2.4 * age)
                m.move_to(c)
                m.set_stroke(opacity=0.5 * vie, width=2 + 6 * vie)

            onde.add_updater(souffle)
            ondes.add(onde)

        # --- avancement dans le cycle ----------------------------------------
        rail = Line(LEFT * demi, RIGHT * demi, stroke_width=3,
                    stroke_color=WHITE, stroke_opacity=0.12)
        rail.shift(DOWN * (demi + 0.28))
        jauge = Line(LEFT * demi, LEFT * demi, stroke_width=3,
                     stroke_color="#49C4B9")
        jauge.shift(DOWN * (demi + 0.28))

        def remplir(m):
            p = (t.get_value() % CYCLE) / CYCLE
            depart = LEFT * demi + DOWN * (demi + 0.28)
            m.put_start_and_end_on(depart, depart + RIGHT * max(1e-3, COTE * p))

        jauge.add_updater(remplir)

        self.add(cadre, trajets, rail, jauge, ondes, trainees, groupe)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par rebond (facultatif)
# --------------------------------------------------------------------------
def generer_bande_son(chemin="billard.wav", sr=44100):
    """Note à chaque rebond ; grave pour les balles lentes."""
    import wave

    n = int((DUREE + 2.0) * sr)
    buf = np.zeros(n)

    demi_tons = [0, 3, 5, 7, 10]
    notes = [196.0 * 2 ** ((demi_tons[i % 5] + 12 * (i // 5)) / 12)
             for i in range(N_BALLES)]

    for instant, k, verticale in rebonds(DUREE):
        f = notes[k]
        i0 = int(instant * sr)
        env_len = int(1.4 * sr)
        tt = np.arange(env_len) / sr
        env = np.exp(-3.6 * tt) * (1 - np.exp(-tt / 0.004))
        # les parois verticales sonnent un peu plus clair que les horizontales
        onde = (np.sin(TAU * f * tt)
                + (0.30 if verticale else 0.16) * np.sin(TAU * 2 * f * tt)
                + (0.10 if verticale else 0.04) * np.sin(TAU * 3 * f * tt))
        fin = min(i0 + env_len, n)
        buf[i0:fin] += 0.16 * (onde * env)[: fin - i0]

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
    # Lancement direct : python billiard_loop.py
    config.pixel_width, config.pixel_height = 1080, 1080
    config.frame_rate = 60
    BilliardLoop().render()
