"""
Vague de pendules ("pendule sonore / métronome") — reproduction Manim.

Rendu :
    manim -r 1080,1920 --fps 60 pendulum_wave.py PendulumWave

Tous les réglages ci-dessous ont été mesurés directement sur la vidéo source
(suivi des billes image par image, 1080x1920 @ 60 fps).
"""

from manim import *
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#  La résolution, elle, vient de la ligne de commande : garder un ratio 9:16.
#      manim -r 1080,1920 --fps 60 pendulum_wave.py PendulumWave
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#000000"

# --------------------------------------------------------------------------
#  Réglages (valeurs mesurées sur la vidéo d'origine)
# --------------------------------------------------------------------------
N_PENDULES = 16
CYCLE = 96.0        # s — au bout de ce temps tout se resynchronise exactement
OSC_MAX = 30        # oscillations du pendule le plus court sur un cycle
                    # -> le pendule k en fait (OSC_MAX - k)
DUREE = 48.0        # s — 48 = demi-cycle (comme la vidéo), 96 = boucle parfaite

AMPLITUDE = 25 * DEGREES
FORME = "triangle"  # "triangle" = comme la vidéo (vitesse angulaire constante)
                    # "sinus"    = mouvement physiquement correct

PIVOT = np.array([0.0, 4.67, 0.0])
L_MIN, L_MAX = 5.23, 8.74      # longueurs des fils, réparties linéairement
RAYON_BILLE = 0.28
ANGLE_GUIDE = 26.5 * DEGREES   # les deux traits obliques
LONG_GUIDE = 20.0

PALETTE = ["#F56E51", "#F9B060", "#49C4B9", "#1F99D0"]
COULEURS = color_gradient(PALETTE, N_PENDULES)

AVEC_SON = True     # génère une note à chaque impact sur un trait

# --------------------------------------------------------------------------
#  Cinématique
# --------------------------------------------------------------------------
def periode(k):
    """Période du pendule k, en secondes."""
    return CYCLE / (OSC_MAX - k)


def longueur(k):
    return L_MIN + (L_MAX - L_MIN) * k / (N_PENDULES - 1)


def angle(k, t):
    """Angle du pendule k à l'instant t. Départ : tous à gauche à t = 0."""
    phase = (t / periode(k)) % 1.0
    if FORME == "sinus":
        return -AMPLITUDE * np.cos(TAU * phase)
    # onde triangulaire : -A -> +A -> -A, vitesse angulaire constante
    return AMPLITUDE * (4 * phase - 1 if phase < 0.5 else 3 - 4 * phase)


def position(k, t):
    a = angle(k, t)
    return PIVOT + longueur(k) * np.array([np.sin(a), -np.cos(a), 0.0])


def impacts(cote, jusqu_a):
    """Tous les (instant, k) où un pendule atteint le trait 'gauche'/'droite'."""
    out = []
    for k in range(N_PENDULES):
        p = periode(k)
        # extrêmes gauche : t = m*p (on saute m=0, c'est le lâcher initial)
        # extrêmes droite : t = (m + 1/2)*p
        depart, decalage = (1, 0.0) if cote == "gauche" else (0, 0.5)
        m = depart
        while (m + decalage) * p <= jusqu_a:
            out.append(((m + decalage) * p, k))
            m += 1
    return sorted(out)


def couleur_trait(cote, t):
    """Couleur du dernier pendule ayant touché ce trait (blanc avant le 1er)."""
    dernier = None
    for k in range(N_PENDULES):
        p = periode(k)
        if cote == "gauche":
            m = np.floor(t / p + 1e-9)
            if m < 1:
                continue
            frappe = m * p
        else:
            m = np.floor(t / p - 0.5 + 1e-9)
            if m < 0:
                continue
            frappe = (m + 0.5) * p
        # >= et non > : quand plusieurs pendules frappent au même instant
        # (t = 19,2 s par exemple), c'est le plus long qui donne sa couleur.
        if dernier is None or frappe >= dernier[0]:
            dernier = (frappe, k)
    return WHITE if dernier is None else COULEURS[dernier[1]]


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class PendulumWave(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- les deux traits obliques -------------------------------------
        traits = VGroup()
        for signe, cote in ((-1, "gauche"), (1, "droite")):
            d = np.array([signe * np.sin(ANGLE_GUIDE), -np.cos(ANGLE_GUIDE), 0.0])
            trait = Line(PIVOT, PIVOT + LONG_GUIDE * d, stroke_width=12)
            trait.add_updater(
                lambda m, c=cote: m.set_stroke(color=couleur_trait(c, t.get_value()))
            )
            traits.add(trait)

        # --- fils + billes -------------------------------------------------
        fils, billes = VGroup(), VGroup()
        for k in range(N_PENDULES):
            p0 = position(k, 0.0)
            fils.add(Line(PIVOT, p0, stroke_color=WHITE,
                          stroke_width=5, stroke_opacity=0.40))
            billes.add(Circle(radius=RAYON_BILLE,
                              fill_color=COULEURS[k], fill_opacity=0.90,
                              stroke_color="#DDE4E4", stroke_width=3).move_to(p0))

        def replacer(_):
            u = t.get_value()
            for k, (fil, bille) in enumerate(zip(fils, billes)):
                p = position(k, u)
                fil.put_start_and_end_on(PIVOT, p)
                bille.move_to(p)

        pendules = VGroup(fils, billes)
        pendules.add_updater(replacer)

        self.add(traits, pendules, Dot(PIVOT, radius=0.05, color=WHITE))

        if AVEC_SON:
            self.add_sound(generer_bande_son(DUREE))

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par impact (facultatif)
# --------------------------------------------------------------------------
def generer_bande_son(duree, chemin="pendules.wav", sr=44100):
    """Note douce à chaque contact avec un trait, aiguë = pendule court."""
    import wave

    n = int((duree + 3.0) * sr)
    buf = np.zeros(n)

    # gamme pentatonique mineure sur ~3 octaves, du grave (k=15) à l'aigu (k=0)
    demi_tons = [0, 3, 5, 7, 10]
    notes = [220.0 * 2 ** ((demi_tons[i % 5] + 12 * (i // 5)) / 12)
             for i in range(N_PENDULES)]

    for cote in ("gauche", "droite"):
        for instant, k in impacts(cote, duree):
            f = notes[N_PENDULES - 1 - k]
            i0 = int(instant * sr)
            env_len = int(2.2 * sr)
            tt = np.arange(env_len) / sr
            env = np.exp(-3.0 * tt) * (1 - np.exp(-tt / 0.004))   # attaque + chute
            onde = (np.sin(TAU * f * tt)
                    + 0.30 * np.sin(TAU * 2 * f * tt)
                    + 0.12 * np.sin(TAU * 3 * f * tt))
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
    # Lancement direct : python pendulum_wave.py
    config.pixel_width, config.pixel_height = 1080, 1920
    config.frame_rate = 60
    PendulumWave().render()
