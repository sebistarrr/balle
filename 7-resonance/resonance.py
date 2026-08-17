"""
Résonance — 10 secondes, format vertical, pensé pour être vu en boucle.

Sur un cercle de N points, on relie le point k au point m·k. En faisant varier
le multiplicateur m, la figure obtenue traverse toute une famille de courbes :
cardioïde à m = 2, néphroïde à m = 3, puis des rosaces de plus en plus fines.
Le film tient en trois temps — une détonation, huit paliers rythmés, un
effondrement — et se referme sur l'image exacte du départ, donc il boucle.

Rendu (format YouTube Shorts) :
    manim -r 1080,1920 --fps 60 resonance.py Resonance

Tout est vectoriel et calculé : aucune image, aucune police externe, aucune
bande son empruntée — la musique est synthétisée par le script lui-même.
"""

from manim import *
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#  La résolution vient de la ligne de commande : garder un ratio 9:16.
#      manim -r 1080,1920 --fps 60 resonance.py Resonance
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#02030A"

# --------------------------------------------------------------------------
#  Découpage du film
# --------------------------------------------------------------------------
DUREE = 10.0
T_ECLAT = 0.55        # la détonation initiale
T_TABLE = 8.30        # fin des paliers, début de l'effondrement
T_NOIR = 9.55         # tout est rentré au centre
M_MIN, M_MAX = 2, 10  # multiplicateurs traversés
PALIERS = M_MAX - M_MIN            # 8 intervalles, donc 8 temps forts

N = 240               # points sur le cercle
RAYON = 3.55
POUSSIERES = 70       # champ d'étoiles de fond

#  Chaque corde est un cubique de 4 points ; on les empile dans un seul
#  VMobject, les sous-chemins se séparant d'eux-mêmes puisque la fin d'une
#  corde ne coïncide pas avec le début de la suivante.
K = np.arange(N)

AVEC_SON = True


# --------------------------------------------------------------------------
#  Petites fonctions de forme
# --------------------------------------------------------------------------
def doux(u):
    """Accélère puis freine, entre 0 et 1."""
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def sortie(u, p=3.0):
    u = np.clip(u, 0.0, 1.0)
    return 1 - (1 - u) ** p


def teinte(h, l=0.58, s=1.0):
    import colorsys
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))


# --------------------------------------------------------------------------
#  État de la figure à l'instant t
# --------------------------------------------------------------------------
def multiplicateur(t):
    """m par paliers : il tient une mesure, puis bascule vite sur la suivante.

    Le palier est ce qui donne le rythme — une figure lisible, puis un
    basculement net, plutôt qu'un fondu continu où l'œil ne se pose jamais.
    """
    if t <= T_ECLAT:
        return float(M_MIN)
    if t >= T_TABLE:
        return float(M_MAX)
    u = (t - T_ECLAT) / (T_TABLE - T_ECLAT) * PALIERS
    i = int(u)
    f = u - i
    return M_MIN + i + (0.0 if f < 0.68 else doux((f - 0.68) / 0.32))


#  Instants d'arrivée sur chaque nouveau multiplicateur : les temps forts.
MESURE = (T_TABLE - T_ECLAT) / PALIERS
TEMPS_FORTS = [T_ECLAT] + [T_ECLAT + (i + 1) * MESURE for i in range(PALIERS)]


def rayon(t):
    if t < T_ECLAT:                       # la détonation : le cercle se déploie
        return RAYON * sortie(t / T_ECLAT, 2.4)
    if t < T_TABLE:
        return RAYON
    if t < T_NOIR:                        # puis tout rentre au centre
        return RAYON * (1 - doux((t - T_TABLE) / (T_NOIR - T_TABLE)))
    return 0.0


def rotation(t):
    """Rotation lente, qui s'emballe pendant l'effondrement."""
    phi = TAU * 0.22 * t / DUREE
    if t > T_TABLE:
        phi += TAU * 1.15 * doux((t - T_TABLE) / (T_NOIR - T_TABLE)) ** 2
    return phi


def frappe(t):
    """Intensité du dernier temps fort, entre 1 (à l'instant même) et 0."""
    dernier = -10.0
    for u in TEMPS_FORTS:
        if u <= t:
            dernier = u
    return float(np.clip(1 - (t - dernier) / 0.42, 0, 1))


def couleur_maitresse(t):
    """La teinte fait exactement deux tours du spectre sur les dix secondes.

    Deux tours entiers, et non une fraction : la couleur d'arrivée est celle du
    départ, sans quoi la boucle se verrait à la reprise.
    """
    return 205 + 720 * t / DUREE


def cordes(t):
    """Les N cordes, empilées en un seul tableau de points de contrôle."""
    r, phi, m = rayon(t), rotation(t), multiplicateur(t)
    a = TAU * K / N + phi
    b = TAU * m * K / N + phi
    A = np.stack([r * np.cos(a), r * np.sin(a), np.zeros(N)], axis=1)
    B = np.stack([r * np.cos(b), r * np.sin(b), np.zeros(N)], axis=1)
    pts = np.empty((4 * N, 3))
    pts[0::4] = A
    pts[1::4] = A + (B - A) / 3
    pts[2::4] = A + 2 * (B - A) / 3
    pts[3::4] = B
    return pts


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class Resonance(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- halo de fond ------------------------------------------------------
        halo = VGroup(*[
            Circle(radius=r, stroke_width=0, fill_opacity=o)
            for r, o in ((7.2, 0.030), (5.4, 0.035), (3.6, 0.040))
        ])
        halo.add_updater(lambda g: [c.set_fill(teinte(couleur_maitresse(t.get_value()), 0.5))
                                    for c in g])

        # --- poussières : elles dérivent en boucle exacte sur dix secondes ------
        graine = np.random.default_rng(7)
        p0 = graine.uniform([-4.5, -8.0], [4.5, 8.0], size=(POUSSIERES, 2))
        amp = graine.uniform(0.10, 0.55, size=(POUSSIERES, 2))
        pha = graine.uniform(0, TAU, size=(POUSSIERES, 2))
        tours = graine.integers(1, 3, size=(POUSSIERES, 2))
        poussieres = VGroup(*[
            Dot(radius=0.018, fill_opacity=0.0) for _ in range(POUSSIERES)
        ])

        def bouger_poussieres(g):
            u = t.get_value()
            ang = TAU * tours * u / DUREE + pha
            pos = p0 + amp * np.sin(ang)
            scint = 0.25 + 0.35 * (0.5 + 0.5 * np.sin(TAU * 3 * tours[:, 0] * u / DUREE + pha[:, 0]))
            c = teinte(couleur_maitresse(u) + 40, 0.75)
            for i, d in enumerate(g):
                d.move_to([pos[i, 0], pos[i, 1], 0.0])
                d.set_fill(c, opacity=float(scint[i]))

        poussieres.add_updater(bouger_poussieres)

        # --- le cercle porteur --------------------------------------------------
        anneau = Circle(radius=1.0, stroke_width=2, fill_opacity=0)

        def maj_anneau(m):
            u = t.get_value()
            r = rayon(u)
            m.width = max(1e-3, 2 * r)
            f = frappe(u)
            m.set_stroke(color=teinte(couleur_maitresse(u) + 30, 0.72),
                         width=1.6 + 4.0 * f,
                         opacity=0.30 + 0.55 * f if r > 0.01 else 0)

        anneau.add_updater(maj_anneau)

        # --- les cordes, en trois couches pour simuler la diffusion lumineuse ---
        #  Manim n'a pas de flou : on superpose le même tracé en large et très
        #  transparent, puis moyen, puis fin et vif. Les teintes des couches sont
        #  légèrement décalées, ce qui donne la frange colorée des halos.
        COUCHES = ((11.0, 0.055, -34), (4.5, 0.16, -14), (1.5, 0.95, 0))
        toile = VGroup(*[VMobject(stroke_width=w) for w, _, _ in COUCHES])

        def maj_toile(g):
            u = t.get_value()
            pts = cordes(u)
            f = frappe(u)
            base = couleur_maitresse(u)
            visible = rayon(u) > 0.01
            for (w, o, dh), couche in zip(COUCHES, g):
                couche.set_points(pts)
                couche.set_stroke(color=teinte(base + dh, 0.60),
                                  width=w * (1 + 0.45 * f),
                                  opacity=(o * (1 + 0.9 * f)) if visible else 0)

        toile.add_updater(maj_toile)

        # --- ondes de choc : une par temps fort, créées d'avance -----------------
        ondes = VGroup()
        for i, instant in enumerate(TEMPS_FORTS):
            onde = Circle(radius=1.0, stroke_width=6, fill_opacity=0)

            def souffle(m, t0=instant):
                age = t.get_value() - t0
                if age < 0 or age > 0.75:
                    m.set_stroke(opacity=0)
                    return
                v = 1 - age / 0.75
                m.width = 2 * (RAYON * 0.35 + 7.5 * age)
                m.set_stroke(color=teinte(couleur_maitresse(t0) + 60, 0.70),
                             width=1 + 7 * v, opacity=0.55 * v * v)

            onde.add_updater(souffle)
            ondes.add(onde)

        # --- cœur : le point d'où tout part et où tout revient -------------------
        coeur = Dot(radius=0.11)

        def maj_coeur(m):
            u = t.get_value()
            f = frappe(u)
            if u < T_ECLAT:
                e = 1 - u / T_ECLAT
                taille, op = 0.10 + 0.55 * e ** 3, 1.0
            elif u < T_TABLE:
                taille, op = 0.07 + 0.13 * f, 0.55 + 0.45 * f
            else:
                #  0,65 à l'arrivée : exactement la taille du point de départ,
                #  pour que la dernière image soit la première.
                v = doux((u - T_TABLE) / (T_NOIR - T_TABLE))
                taille, op = 0.07 + 0.58 * v ** 3, 1.0
            m.width = 2 * taille
            m.set_fill(teinte(couleur_maitresse(u) + 50, 0.88), opacity=op)

        coeur.add_updater(maj_coeur)

        # --- le multiplicateur affiché ------------------------------------------
        #  En Text (Pango) et non en MathTex : pas de LaTeX à installer.
        def etiquette(valeur, couleur):
            m = Text(f"×{valeur}", font_size=76, weight=BOLD, color=couleur)
            m.move_to([0, -5.55, 0])
            return m

        compteur = etiquette(M_MIN, WHITE)
        compteur.affiche = M_MIN

        def maj_compteur(m):
            u = t.get_value()
            val = int(np.floor(multiplicateur(u) + 1e-6))
            if val != m.affiche:
                m.become(etiquette(val, WHITE))
                m.affiche = val
            f = frappe(u)
            dedans = T_ECLAT * 0.6 < u < T_TABLE + 0.25
            m.set_color(teinte(couleur_maitresse(u) + 30, 0.88))
            m.set_opacity((0.78 + 0.22 * f) if dedans else 0.0)
            m.scale_to_fit_height(0.62 * (1 + 0.12 * f))
            m.move_to([0, -5.55, 0])

        compteur.add_updater(maj_compteur)

        # --- éclair de bascule ---------------------------------------------------
        #  Un voile blanc très bref à l'effondrement : il masque la couture de la
        #  boucle, l'image d'arrivée redevenant celle du départ.
        voile = Rectangle(width=config.frame_width, height=config.frame_height,
                          stroke_width=0, fill_color=WHITE, fill_opacity=0)

        def maj_voile(m):
            u = t.get_value()
            f = np.clip(1 - abs(u - T_NOIR) / 0.16, 0, 1)
            m.set_fill(WHITE, opacity=0.92 * f ** 2)

        voile.add_updater(maj_voile)

        self.add(halo, poussieres, ondes, toile, anneau, coeur, compteur, voile)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : entièrement synthétisée ici — un coup grave par temps fort, une
#  note qui monte avec le multiplicateur, une montée de bruit sur la fin.
# --------------------------------------------------------------------------
def generer_bande_son(chemin="resonance.wav", sr=44100):
    import wave

    n = int(DUREE * sr)
    gauche = np.zeros(n)
    droite = np.zeros(n)
    rng = np.random.default_rng(11)

    def poser(buf, debut, onde):
        i0 = max(0, int(debut * sr))
        fin = min(i0 + len(onde), n)
        if fin > i0:
            buf[i0:fin] += onde[: fin - i0]

    def frappe_grave(force=1.0):
        d = int(0.42 * sr)
        tt = np.arange(d) / sr
        f = 118 * np.exp(-tt * 24) + 44          # la hauteur plonge : le « boum »
        env = np.exp(-tt * 9.5)
        return force * 0.85 * np.sin(TAU * np.cumsum(f) / sr) * env

    def cloche(freq, duree=1.5, force=0.30):
        d = int(duree * sr)
        tt = np.arange(d) / sr
        env = np.exp(-tt * 3.6) * (1 - np.exp(-tt / 0.002))
        return force * env * (np.sin(TAU * freq * tt)
                              + 0.5 * np.sin(TAU * freq * 2.01 * tt)
                              + 0.25 * np.sin(TAU * freq * 3.02 * tt))

    # gamme pentatonique mineure, une note plus haute à chaque palier
    demi = [0, 3, 5, 7, 10, 12, 15, 17, 19]
    for i, instant in enumerate(TEMPS_FORTS):
        force = 0.75 + 0.32 * i / max(1, len(TEMPS_FORTS) - 1)
        poser(gauche, instant, frappe_grave(force))
        poser(droite, instant, frappe_grave(force))
        f = 262 * 2 ** (demi[min(i, len(demi) - 1)] / 12)
        pan = 0.5 + 0.5 * np.sin(i * 1.7)        # les notes voyagent d'un bord à l'autre
        poser(gauche, instant, cloche(f) * (1 - pan * 0.55))
        poser(droite, instant, cloche(f) * (1 - (1 - pan) * 0.55))
        # contretemps discret
        if i < len(TEMPS_FORTS) - 1:
            poser(gauche, instant + MESURE / 2, cloche(f * 2, 0.5, 0.09))
            poser(droite, instant + MESURE / 2, cloche(f * 2, 0.5, 0.09))

    # montée de bruit filtrée sur la dernière mesure, puis impact final
    d = int((T_NOIR - T_TABLE + 0.3) * sr)
    tt = np.arange(d) / sr
    bruit = rng.normal(0, 1, d)
    # filtre passe-bas dont la coupure s'ouvre : moyenne glissante qui rétrécit
    montee = np.cumsum(bruit) / 40
    montee = montee - np.convolve(montee, np.ones(400) / 400, mode="same")
    montee *= (tt / tt[-1]) ** 2.2 * 0.5
    poser(gauche, T_TABLE, montee)
    poser(droite, T_TABLE, montee)
    poser(gauche, T_NOIR - 0.02, frappe_grave(1.35))
    poser(droite, T_NOIR - 0.02, frappe_grave(1.35))
    poser(gauche, T_NOIR - 0.02, cloche(262 * 2 ** (24 / 12), 2.4, 0.34))
    poser(droite, T_NOIR - 0.02, cloche(262 * 2 ** (24 / 12), 2.4, 0.34))

    stereo = np.stack([np.tanh(gauche * 1.15), np.tanh(droite * 1.15)], axis=1)
    crete = max(1e-9, np.abs(stereo).max())
    pcm = (stereo / crete * 0.92 * 32767).astype("<i2")

    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Lancement direct : python resonance.py
    config.pixel_width, config.pixel_height = 1080, 1920
    config.frame_rate = 60
    Resonance().render()
