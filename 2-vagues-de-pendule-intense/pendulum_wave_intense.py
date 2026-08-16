"""
Vagues de pendule, intensifié — reproduction Manim.

Même cinématique que `1-vagues-de-pendule/pendulum_wave.py` (mêmes longueurs,
mêmes périodes, même onde triangulaire), jouée deux fois plus vite et habillée :
traînées derrière les billes, onde de choc à chaque contact, traits obliques en
dégradé qui s'avivent au moment de l'impact.

Rendu :
    manim -r 1080,1920 --fps 60 pendulum_wave_intense.py PendulumWaveIntense

Différence assumée avec la page `index.html` voisine : les gerbes de
particules ne sont pas reprises ici. Manim dessine des formes vectorielles, et
les quelques milliers d'étincelles d'un cycle complet coûteraient bien plus
cher que ce qu'elles apportent.
"""

from manim import *
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#      manim -r 1080,1920 --fps 60 pendulum_wave_intense.py PendulumWaveIntense
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#020306"

# --------------------------------------------------------------------------
#  Réglages — identiques à l'animation 1, sauf VITESSE et l'habillage
# --------------------------------------------------------------------------
N_PENDULES = 16
CYCLE = 96.0        # s d'animation — au bout de ce temps tout se resynchronise
OSC_MAX = 30        # oscillations du pendule le plus court sur un cycle
DUREE = 48.0        # s d'animation à rendre (48 = demi-cycle, 96 = boucle)
VITESSE = 2.0       # 2 s d'animation par seconde de vidéo

AMPLITUDE = 25 * DEGREES
PIVOT = np.array([0.0, 4.67, 0.0])
L_MIN, L_MAX = 5.23, 8.74
RAYON_BILLE = 0.28
ANGLE_GUIDE = 26.5 * DEGREES
LONG_GUIDE = 20.0

MEMOIRE = 0.8       # longueur de la traînée, en secondes d'animation
VIE_ONDE = 0.66     # durée d'une onde de choc
VIE_ECLAT = 0.29    # durée de l'avivement d'un trait après contact

PALETTE = ["#F56E51", "#F9B060", "#49C4B9", "#1F99D0"]
COULEURS = color_gradient(PALETTE, N_PENDULES)

AVEC_SON = True


# --------------------------------------------------------------------------
#  Cinématique (reprise telle quelle de l'animation 1)
# --------------------------------------------------------------------------
def periode(k):
    return CYCLE / (OSC_MAX - k)


def longueur(k):
    return L_MIN + (L_MAX - L_MIN) * k / (N_PENDULES - 1)


def angle(k, t):
    """Angle du pendule k. Onde triangulaire : vitesse angulaire constante."""
    phase = (t / periode(k)) % 1.0
    return AMPLITUDE * (4 * phase - 1 if phase < 0.5 else 3 - 4 * phase)


def position(k, t):
    a = angle(k, t)
    return PIVOT + longueur(k) * np.array([np.sin(a), -np.cos(a), 0.0])


def impacts(jusqu_a):
    """Tous les (instant, k, cote) où un pendule atteint un trait.

    Les extrêmes tombent à t = m * periode/2 : m pair à gauche, m impair à
    droite. m = 0 est le lâcher initial, pas un contact.
    """
    out = []
    for k in range(N_PENDULES):
        demi = periode(k) / 2
        m = 1
        while m * demi <= jusqu_a:
            out.append((m * demi, k, "droite" if m % 2 else "gauche"))
            m += 1
    return sorted(out)


def couleur_trait(cote, t):
    """Couleur du dernier pendule ayant touché ce trait (blanc avant le 1er)."""
    dernier = None
    for k in range(N_PENDULES):
        demi = periode(k) / 2
        m = int(np.floor(t / demi + 1e-9))
        if m % 2 != (0 if cote == "gauche" else 1):
            m -= 1
        if m < (2 if cote == "gauche" else 1):
            continue
        # >= et non > : quand plusieurs pendules frappent au même instant
        # (t = 19,2 s par exemple), c'est le plus long qui donne sa couleur.
        if dernier is None or m * demi >= dernier[0]:
            dernier = (m * demi, k)
    return WHITE if dernier is None else COULEURS[dernier[1]]


def dernier_contact(cote, t):
    """Instant du dernier contact sur ce trait, pour l'avivement."""
    meilleur = -1.0
    for k in range(N_PENDULES):
        demi = periode(k) / 2
        m = int(np.floor(t / demi + 1e-9))
        if m % 2 != (0 if cote == "gauche" else 1):
            m -= 1
        if m < (2 if cote == "gauche" else 1):
            continue
        meilleur = max(meilleur, m * demi)
    return meilleur


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class PendulumWaveIntense(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- les deux traits obliques ---------------------------------------
        traits = VGroup()
        for signe, cote in ((-1, "gauche"), (1, "droite")):
            d = np.array([signe * np.sin(ANGLE_GUIDE), -np.cos(ANGLE_GUIDE), 0.0])
            trait = Line(PIVOT, PIVOT + LONG_GUIDE * d, stroke_width=12)

            def aviver(m, c=cote):
                u = t.get_value()
                age = u - dernier_contact(c, u)
                f = np.clip(1 - age / VIE_ECLAT, 0, 1) if age >= 0 else 0.0
                m.set_stroke(color=couleur_trait(c, u), width=12 + 9 * f)

            trait.add_updater(aviver)
            traits.add(trait)

        # --- fils, billes, halos ---------------------------------------------
        fils, billes, halos = VGroup(), VGroup(), VGroup()
        for k in range(N_PENDULES):
            p0 = position(k, 0.0)
            fils.add(Line(PIVOT, p0, stroke_color="#D2E6EB",
                          stroke_width=5, stroke_opacity=0.22))
            billes.add(Circle(radius=RAYON_BILLE,
                              fill_color=COULEURS[k], fill_opacity=0.95,
                              stroke_color="#F0FAFA", stroke_width=2).move_to(p0))
            halos.add(VGroup(*[
                Circle(radius=RAYON_BILLE * f, fill_color=COULEURS[k],
                       fill_opacity=o, stroke_width=0).move_to(p0)
                for f, o in ((1.5, 0.10), (2.1, 0.05))]))

        def replacer(_):
            u = t.get_value()
            for k in range(N_PENDULES):
                p = position(k, u)
                fils[k].put_start_and_end_on(PIVOT, p)
                billes[k].move_to(p)
                halos[k].move_to(p)

        pendules = VGroup(fils, halos, billes)
        pendules.add_updater(replacer)

        # --- traînées ---------------------------------------------------------
        #  On capture la position par une fonction dédiée : passer
        #  billes[k].get_center ferait suivre la traînée d'un objet déjà déplacé
        #  dans l'ordre des updaters, avec une image de retard.
        trainees = VGroup()
        for k in range(N_PENDULES):
            #  dissipating_time se compte en secondes de vidéo, MEMOIRE en
            #  secondes d'animation : on divise par VITESSE, on ne multiplie pas.
            trainees.add(TracedPath(
                (lambda kk=k: position(kk, t.get_value())),
                dissipating_time=MEMOIRE / VITESSE,
                stroke_color=COULEURS[k], stroke_width=9))

        # --- ondes de choc : une par contact, créées d'avance -----------------
        ondes = VGroup()
        for instant, k, cote in impacts(DUREE):
            signe = 1 if cote == "droite" else -1
            a = signe * AMPLITUDE
            centre = PIVOT + longueur(k) * np.array([np.sin(a), -np.cos(a), 0.0])
            onde = Circle(radius=1.0, stroke_width=6, stroke_color=COULEURS[k])
            onde.move_to(centre)

            def souffle(m, t0=instant, c=centre):
                age = t.get_value() - t0
                if age < 0 or age > VIE_ONDE:
                    m.set_stroke(opacity=0)
                    return
                vie = 1 - age / VIE_ONDE
                m.width = 2 * (RAYON_BILLE + 5.2 * age)
                m.move_to(c)
                m.set_stroke(opacity=0.55 * vie, width=3 + 9 * vie)

            onde.add_updater(souffle)
            ondes.add(onde)

        pivot = Dot(PIVOT, radius=0.06, color=WHITE)

        self.add(traits, ondes, trainees, pendules, pivot)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE),
                  run_time=DUREE / VITESSE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : une note par contact (facultatif)
# --------------------------------------------------------------------------
def generer_bande_son(chemin="pendules_intense.wav", sr=44100):
    """Note douce à chaque contact, aiguë = pendule court.

    Les instants sont divisés par VITESSE : la bande son suit la vidéo, pas le
    temps d'animation.
    """
    import wave

    duree_video = DUREE / VITESSE
    n = int((duree_video + 3.0) * sr)
    buf = np.zeros(n)

    demi_tons = [0, 3, 5, 7, 10]
    notes = [220.0 * 2 ** ((demi_tons[i % 5] + 12 * (i // 5)) / 12)
             for i in range(N_PENDULES)]

    for instant, k, _ in impacts(DUREE):
        f = notes[N_PENDULES - 1 - k]
        i0 = int(instant / VITESSE * sr)
        env_len = int(2.0 * sr)
        tt = np.arange(env_len) / sr
        env = np.exp(-3.0 * tt) * (1 - np.exp(-tt / 0.004))
        onde = (np.sin(TAU * f * tt)
                + 0.50 * np.sin(TAU * f * 1.003 * tt)   # quinte désaccordée
                + 0.28 * np.sin(TAU * 2 * f * tt)
                + 0.10 * np.sin(TAU * 3 * f * tt))
        fin = min(i0 + env_len, n)
        buf[i0:fin] += 0.18 * (onde * env)[: fin - i0]

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
    # Lancement direct : python pendulum_wave_intense.py
    config.pixel_width, config.pixel_height = 1080, 1920
    config.frame_rate = 60
    PendulumWaveIntense().render()
