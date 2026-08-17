"""
La balle qui grossit — reproduction Manim.

Une balle rebondit sans frottement dans un carré. À chaque contact avec une
paroi son rayon gagne un cran ; l'espace laissé à son centre se resserre
d'autant, donc la cadence s'emballe toute seule. Au 45e rebond elle est
inscrite dans le carré.

Rendu :
    manim -r 1080,1080 --fps 60 growing_ball.py GrowingBall

Les constantes sont celles de la page `index.html` voisine, converties du
repère pixel (1000x1000) au repère de scène (8x8) : un pixel vaut 0,008 unité.
"""

from manim import *
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#  La résolution vient de la ligne de commande : garder un carré.
#      manim -r 1080,1080 --fps 60 growing_ball.py GrowingBall
# --------------------------------------------------------------------------
config.frame_width = 8.0
config.frame_height = 8.0
config.background_color = "#020306"

# --------------------------------------------------------------------------
#  Réglages
# --------------------------------------------------------------------------
COTE = 6.848            # côté du carré (856 px sur 1000)
R_MIN = 0.144           # rayon au départ (18 px)
R_MAX = COTE / 2        # rayon d'arrivée : la balle est inscrite dans le carré
REBONDS = 45            # contacts nécessaires pour y arriver
PAS = (R_MAX - R_MIN) / REBONDS
VITESSE = 4.96          # unités par seconde (620 px/s)
CAP = 32.7 * DEGREES    # direction initiale
DEPART = np.array([0.0, -0.12 * COTE, 0.0])
ATTENTE = 1.6           # temps d'arrêt une fois le carré rempli

VIE_ONDE = 0.62         # durée d'une onde de choc, en secondes
MEMOIRE = 0.7           # longueur de la traînée, en secondes

PALETTE = ["#1F99D0", "#49C4B9", "#F9B060", "#F56E51"]   # petite -> pleine
COULEURS = color_gradient(PALETTE, 128)

AVEC_SON = True


def teinte(p):
    """Couleur de la balle selon son remplissage p, entre 0 et 1."""
    return COULEURS[int(np.clip(p, 0, 1) * (len(COULEURS) - 1))]


# --------------------------------------------------------------------------
#  Simulation : on rejoue le trajet une fois pour toutes, puis on relit.
#  Entre deux contacts le mouvement est rectiligne uniforme et le rayon est
#  constant : quelques dizaines de segments suffisent à décrire tout le cycle.
# --------------------------------------------------------------------------
def simuler():
    """Renvoie (segments, contacts, duree).

    segment : (t0, p0, t1, p1, rayon)      — un vol libre entre deux parois
    contact : (t, point, rayon, verticale) — l'instant d'un rebond
    """
    demi = COTE / 2
    p = DEPART.copy()
    v = np.array([np.cos(CAP), np.sin(CAP), 0.0]) * VITESSE
    r = R_MIN
    t = 0.0
    segments, contacts = [], []

    for _ in range(REBONDS):
        lim = demi - r
        # temps restant avant de toucher, sur chaque axe
        durees = []
        for axe in (0, 1):
            if abs(v[axe]) < 1e-12:
                durees.append(np.inf)
            else:
                cible = lim if v[axe] > 0 else -lim
                durees.append((cible - p[axe]) / v[axe])
        dt = min(durees)
        verticale = durees[0] <= durees[1]

        suivant = p + v * dt
        segments.append((t, p.copy(), t + dt, suivant.copy(), r))
        t += dt
        p = suivant
        contacts.append((t, p.copy(), r, verticale))

        v[0 if verticale else 1] *= -1
        r = min(R_MAX, r + PAS)

        # la croissance peut faire déborder le centre : on le ramène dedans
        lim = demi - r
        if lim <= 1e-9:
            break
        p[:2] = np.clip(p[:2], -lim, lim)

    # le carré est rempli : la balle se cale au centre et marque un temps
    segments.append((t, ORIGIN.copy(), t + ATTENTE, ORIGIN.copy(), R_MAX))
    return segments, contacts, t + ATTENTE


SEGMENTS, CONTACTS, DUREE = simuler()


def etat(t):
    """Centre et rayon de la balle à l'instant t."""
    for t0, p0, t1, p1, r in SEGMENTS:
        if t <= t1:
            u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return p0 + (p1 - p0) * u, r
    return SEGMENTS[-1][3], SEGMENTS[-1][4]


def remplissage(r):
    return (r - R_MIN) / (R_MAX - R_MIN)


def nb_contacts(t):
    """Combien de rebonds ont déjà eu lieu à l'instant t."""
    n = 0
    for instant, _, _, _ in CONTACTS:
        if instant <= t:
            n += 1
        else:
            break
    return n


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class GrowingBall(Scene):
    def construct(self):
        t = ValueTracker(0.0)
        demi = COTE / 2

        # --- le carré, qui s'illumine quand la balle le remplit ------------
        cadre = Square(side_length=COTE, stroke_color="#49C4B9", stroke_width=4)

        def eclat_cadre(m):
            reste = DUREE - ATTENTE - t.get_value()
            f = np.clip(1 + reste / 0.7, 0, 1) if reste <= 0 else 0.0
            m.set_stroke(width=4 + 8 * f, opacity=0.35 + 0.65 * f)

        cadre.add_updater(eclat_cadre)

        # --- la balle et son halo -------------------------------------------
        balle = Circle(radius=1.0, fill_opacity=0.96,
                       stroke_color="#F0FAFA", stroke_width=2)
        halo = VGroup(*[Circle(radius=1.0, stroke_width=0, fill_opacity=o)
                        for o in (0.10, 0.06, 0.03)])

        def placer(m):
            p, r = etat(t.get_value())
            c = teinte(remplissage(r))
            m.width = 2 * r
            m.move_to(p)
            m.set_fill(c)

        def placer_halo(m):
            p, r = etat(t.get_value())
            c = teinte(remplissage(r))
            for i, anneau in enumerate(m):
                anneau.width = 2 * r * (1.12 + 0.13 * i)
                anneau.move_to(p)
                anneau.set_fill(c)

        balle.add_updater(placer)
        halo.add_updater(placer_halo)

        # --- traînée ---------------------------------------------------------
        trainee = TracedPath(balle.get_center, dissipating_time=MEMOIRE,
                             stroke_color="#49C4B9", stroke_width=5)
        trainee.add_updater(
            lambda m: m.set_stroke(color=teinte(remplissage(etat(t.get_value())[1])),
                                   opacity=0.45))

        # --- ondes de choc : une par contact, créées d'avance ----------------
        #  Chacune sait quand elle doit apparaître ; elle reste invisible avant
        #  et après. Rien n'est ajouté à la scène en cours d'animation.
        ondes = VGroup()
        for instant, point, rayon, _ in CONTACTS:
            onde = Circle(radius=1.0, stroke_width=6,
                          stroke_color=teinte(remplissage(rayon)))
            onde.move_to(point)

            def souffle(m, t0=instant, r0=rayon, centre=point):
                age = t.get_value() - t0
                if age < 0 or age > VIE_ONDE:
                    m.set_stroke(opacity=0)
                    return
                vie = 1 - age / VIE_ONDE
                m.width = 2 * (r0 + 2.7 * age)
                m.move_to(centre)
                m.set_stroke(opacity=0.5 * vie, width=2 + 7 * vie)

            onde.add_updater(souffle)
            ondes.add(onde)

        # --- compteur et jauge de remplissage --------------------------------
        #  Compteur en Text (Pango) et non en Integer : Integer compose ses
        #  chiffres avec LaTeX, qu'il faudrait alors avoir installé. On ne
        #  reconstruit le texte que lorsque le nombre change.
        def libelle(n):
            #  Il ne reste que (hauteur - COTE)/2 au-dessus du carré : on cale
            #  le texte sur le bord haut plutôt que sur le coin de l'image.
            m = Text(f"rebond {n} / {REBONDS}", font_size=18, color="#8FA0A0")
            m.next_to(cadre, UP, buff=0.09).align_to(cadre, LEFT)
            return m

        compteur = libelle(0)
        compteur.affiche = 0

        def maj_compteur(m):
            n = nb_contacts(t.get_value())
            if n != m.affiche:
                m.become(libelle(n))
                m.affiche = n

        compteur.add_updater(maj_compteur)

        rail = Line(LEFT * demi, RIGHT * demi, stroke_width=3,
                    stroke_color=WHITE, stroke_opacity=0.12)
        rail.shift(DOWN * (demi + 0.28))
        jauge = Line(LEFT * demi, LEFT * demi, stroke_width=3)
        jauge.shift(DOWN * (demi + 0.28))

        def remplir_jauge(m):
            _, r = etat(t.get_value())
            p = remplissage(r)
            depart = LEFT * demi + DOWN * (demi + 0.28)
            m.put_start_and_end_on(depart, depart + RIGHT * max(1e-3, COTE * p))
            m.set_stroke(color=teinte(p))

        jauge.add_updater(remplir_jauge)

        self.add(cadre, rail, jauge, compteur, ondes, trainee, halo, balle)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par rebond, de plus en plus grave (facultatif)
# --------------------------------------------------------------------------
def generer_bande_son(chemin="balle.wav", sr=44100):
    """Note à chaque contact ; plus la balle est grosse, plus le son descend."""
    import wave

    n = int((DUREE + 2.0) * sr)
    buf = np.zeros(n)

    # gamme pentatonique mineure sur ~3 octaves, rangée du grave à l'aigu
    demi_tons = [0, 3, 5, 7, 10]
    notes = [147.0 * 2 ** ((demi_tons[i % 5] + 12 * (i // 5)) / 12)
             for i in range(16)][::-1]

    for instant, _, rayon, _ in CONTACTS:
        p = remplissage(rayon)
        f = notes[min(len(notes) - 1, int(p * len(notes)))]
        i0 = int(instant * sr)
        env_len = int(1.6 * sr)
        tt = np.arange(env_len) / sr
        env = np.exp(-3.4 * tt) * (1 - np.exp(-tt / 0.004))
        onde = (np.sin(TAU * f * tt)
                + 0.30 * np.sin(TAU * 2 * f * tt)
                + 0.10 * np.sin(TAU * 3 * f * tt))
        fin = min(i0 + env_len, n)
        buf[i0:fin] += 0.22 * (onde * env)[: fin - i0]

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
    # Lancement direct : python growing_ball.py
    config.pixel_width, config.pixel_height = 1080, 1080
    config.frame_rate = 60
    GrowingBall().render()
