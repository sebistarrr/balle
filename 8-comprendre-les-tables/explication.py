"""
Comprendre les tables de multiplication — explication en 52 secondes.

Reprend le principe de l'animation 7, mais en le déroulant pas à pas pour
quelqu'un qui n'a jamais vu la figure. Le film suit six étapes :

  1. dix points numérotés sur un cercle ;
  2. la table de 2, une corde à la fois, avec le calcul écrit ;
  3. le point clé — quand le double dépasse le tour, on continue de tourner ;
  4. on ajoute des points : 40, puis 120, puis 240 ; un cœur apparaît ;
  5. on change de table : chaque table donne sa figure, avec m − 1 pointes ;
  6. la règle, en une ligne.

Rendu (format vertical, YouTube Shorts / TikTok) :
    manim -r 1080,1920 --fps 60 explication.py Explication

Tout est vectoriel et calculé : aucune image, aucune police externe, et la bande
son est synthétisée par le script lui-même.
"""

from manim import *
import colorsys
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#  La résolution vient de la ligne de commande : garder un ratio 9:16.
#      manim -r 1080,1920 --fps 60 explication.py Explication
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#05070E"

# --------------------------------------------------------------------------
#  Minutage. Une explication se règle au chronomètre : chaque étape a son
#  début, et tout le reste — texte, cordes, son — s'y accroche.
# --------------------------------------------------------------------------
T_TITRE = 0.0          # l'accroche
T_CERCLE = 3.4         # le cercle et ses dix points numérotés
T_ANNONCE = 7.4        # « table de 2 : chaque nombre rejoint son double »
T_CORDES = 10.0        # tracé des dix cordes, une par une
PAS_CORDE = 1.15
T_MODULO = T_CORDES + 10 * PAS_CORDE       # 21,5 s — retour sur le tour bouclé
T_DENSE = T_MODULO + 2.5                   # 24,0 s — 40, 120, 240 points
PAS_DENSE = 2.2
T_COEUR = T_DENSE + 3 * PAS_DENSE          # 30,6 s — « un cœur »
T_TABLES = T_COEUR + 2.4                   # 33,0 s — défilé des tables
PAS_TABLE = 1.9
TABLES = [3, 4, 5, 6, 7, 8, 9]
T_FINAL = T_TABLES + len(TABLES) * PAS_TABLE   # 46,3 s
DUREE = T_FINAL + 5.7                          # 52,0 s

N_PETIT = 10           # points pendant l'explication
DENSITES = [40, 120, 240]
RAYON = 3.15
CENTRE = np.array([0.0, 0.9, 0.0])

BLEU = "#5AC8FA"
CLAIR = "#EAF2F8"
GRIS = "#8FA3B8"
CHAUD = "#FF6B57"

AVEC_SON = True


# --------------------------------------------------------------------------
#  Outils
# --------------------------------------------------------------------------
def doux(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * (3 - 2 * u)


def paraitre(t, debut, montee=0.45, fin=None, descente=0.45):
    """Opacité d'un élément qui paraît puis, éventuellement, s'efface."""
    o = doux((t - debut) / montee)
    if fin is not None:
        o *= 1 - doux((t - fin) / descente)
    return o


def teinte(h, l=0.62):
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, l, 1.0)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))


def sur_cercle(k, n, rayon=RAYON):
    """Point k parmi n, 0 en haut, puis dans le sens des aiguilles.

    Le sens horaire et le zéro en haut ne changent rien aux mathématiques,
    mais c'est la disposition d'un cadran : on s'y repère sans y penser.
    """
    a = np.pi / 2 - TAU * k / n
    return CENTRE + rayon * np.array([np.cos(a), np.sin(a), 0.0])


def table_courante(t):
    """Quelle table est affichée à l'instant t."""
    if t < T_TABLES:
        return 2
    i = int((t - T_TABLES) / PAS_TABLE)
    return TABLES[min(i, len(TABLES) - 1)]


def densite_courante(t):
    """Combien de points sur le cercle à l'instant t."""
    if t < T_DENSE:
        return N_PETIT
    if t >= T_COEUR:
        return DENSITES[-1]
    i = int((t - T_DENSE) / PAS_DENSE)
    return DENSITES[min(i, len(DENSITES) - 1)]


def cordes(n, m, rayon=RAYON):
    """Les n cordes k -> m·k, empilées en un seul tableau de points.

    Chaque corde est un cubique de quatre points. Les sous-chemins se séparent
    d'eux-mêmes : la fin d'une corde ne coïncide pas avec le début de la
    suivante.
    """
    k = np.arange(n)
    a = np.pi / 2 - TAU * k / n
    b = np.pi / 2 - TAU * (m * k % n) / n
    A = CENTRE + rayon * np.stack([np.cos(a), np.sin(a), np.zeros(n)], axis=1)
    B = CENTRE + rayon * np.stack([np.cos(b), np.sin(b), np.zeros(n)], axis=1)
    pts = np.empty((4 * n, 3))
    pts[0::4] = A
    pts[1::4] = A + (B - A) / 3
    pts[2::4] = A + 2 * (B - A) / 3
    pts[3::4] = B
    return pts


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class Explication(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # ------------------------------------------------------------------
        #  Étape 0 — l'accroche
        # ------------------------------------------------------------------
        accroche = VGroup(
            texte("une table de multiplication,", 0.78, CLAIR, gras=True),
            texte("ça se dessine ?", 0.78, BLEU, gras=True),
        ).arrange(DOWN, buff=0.30)
        accroche.move_to(CENTRE + UP * 0.4)
        accroche.add_updater(lambda g: g.set_opacity(
            paraitre(t.get_value(), T_TITRE + 0.2, 0.5, T_CERCLE - 0.6, 0.5)))

        # ------------------------------------------------------------------
        #  Étape 1 — le cercle et ses dix points numérotés
        # ------------------------------------------------------------------
        cercle = Circle(radius=RAYON, stroke_color=GRIS, stroke_width=2.5)
        cercle.move_to(CENTRE)
        cercle.add_updater(lambda m: m.set_stroke(
            opacity=0.45 * paraitre(t.get_value(), T_CERCLE, 0.6)))

        points = VGroup(*[Dot(sur_cercle(k, N_PETIT), radius=0.085, color=CLAIR)
                          for k in range(N_PETIT)])
        etiquettes = VGroup(*[
            texte(str(k), 0.44, GRIS).move_to(sur_cercle(k, N_PETIT, RAYON + 0.52))
            for k in range(N_PETIT)])

        def maj_reperes(_):
            u = t.get_value()
            # les points arrivent l'un après l'autre, puis s'effacent quand on
            # passe aux grandes densités : à 240 points, les numéros sont illisibles
            depart = 1 - doux((u - T_DENSE + 0.3) / 0.7)
            for k in range(N_PETIT):
                o = paraitre(u, T_CERCLE + 0.25 + k * 0.09, 0.35) * depart
                points[k].set_opacity(o)
                etiquettes[k].set_opacity(o * 0.9)

        points.add_updater(maj_reperes)

        # ------------------------------------------------------------------
        #  Étape 2 — l'annonce de la règle
        # ------------------------------------------------------------------
        regle = texte("table de 2 : chaque nombre", 0.52, CLAIR)
        regle2 = texte("rejoint son double", 0.52, BLEU, gras=True)
        annonce = VGroup(regle, regle2).arrange(DOWN, buff=0.16)
        annonce.move_to([0, -4.55, 0])
        #  Disparaît AVANT le premier calcul : les deux occupent la même ligne,
        #  et se chevauchaient d'une demi-seconde.
        annonce.add_updater(lambda g: g.set_opacity(
            paraitre(t.get_value(), T_ANNONCE, 0.4, T_CORDES - 0.6, 0.35)))

        # ------------------------------------------------------------------
        #  Étape 3 — les dix cordes, une par une, calcul à l'appui
        # ------------------------------------------------------------------
        traits = VGroup(*[Line(ORIGIN, ORIGIN, stroke_width=4) for _ in range(N_PETIT)])

        def maj_traits(g):
            u = t.get_value()
            evanouir = 1 - doux((u - T_DENSE + 0.3) / 0.7)
            for k in range(N_PETIT):
                debut = T_CORDES + k * PAS_CORDE
                av = doux((u - debut) / (PAS_CORDE * 0.55))
                A, B = sur_cercle(k, N_PETIT), sur_cercle(2 * k % N_PETIT, N_PETIT)
                if av <= 0:
                    g[k].set_stroke(opacity=0)
                    continue
                # un trait de longueur nulle n'a pas de direction : on garde un
                # epsilon, sinon Manim ne sait pas l'orienter
                g[k].put_start_and_end_on(A, A + (B - A) * max(av, 1e-3))
                frais = 1 - doux((u - debut - PAS_CORDE) / 0.5)
                g[k].set_stroke(color=BLEU,
                                width=4 + 3 * frais,
                                opacity=(0.55 + 0.45 * frais) * evanouir)

        traits.add_updater(maj_traits)

        curseur = Dot(radius=0.16, color=CHAUD)

        def maj_curseur(m):
            u = t.get_value()
            dedans = T_CORDES <= u < T_MODULO
            if not dedans:
                m.set_opacity(0)
                return
            k = int((u - T_CORDES) / PAS_CORDE)
            m.move_to(sur_cercle(min(k, N_PETIT - 1), N_PETIT))
            m.set_opacity(1)

        curseur.add_updater(maj_curseur)

        # le calcul, réécrit seulement quand il change
        def ligne_calcul(k):
            double = 2 * k
            if double < N_PETIT:
                s = f"{k} × 2 = {double}"
            else:
                # le point à retenir : on a fait plus d'un tour
                s = f"{k} × 2 = {double}  →  {double % N_PETIT}"
            return texte(s, 0.70, CLAIR, gras=True).move_to([0, -4.55, 0])

        calcul = ligne_calcul(0)
        calcul.affiche = -1

        def maj_calcul(m):
            u = t.get_value()
            if not (T_CORDES <= u < T_MODULO + 1.4):
                m.set_opacity(0)
                return
            k = min(int((u - T_CORDES) / PAS_CORDE), N_PETIT - 1)
            if k != m.affiche:
                m.become(ligne_calcul(k))
                m.affiche = k
            m.set_opacity(1)

        calcul.add_updater(maj_calcul)

        # ------------------------------------------------------------------
        #  Étape 4 — le tour bouclé, dit explicitement
        # ------------------------------------------------------------------
        tour = VGroup(
            texte("au-delà du tour,", 0.52, GRIS),
            texte("on continue de tourner", 0.52, CHAUD, gras=True),
        ).arrange(DOWN, buff=0.16)
        tour.move_to([0, -5.75, 0])
        tour.add_updater(lambda g: g.set_opacity(
            paraitre(t.get_value(), T_CORDES + 4.6, 0.5, T_DENSE - 0.4, 0.4)))

        # ------------------------------------------------------------------
        #  Étape 5 — on densifie, puis on change de table
        # ------------------------------------------------------------------
        #  Trois épaisseurs superposées : Manim n'a pas de flou, c'est ainsi
        #  qu'on obtient une lueur.
        COUCHES = ((9.0, 0.06), (3.6, 0.18), (1.4, 0.95))
        toile = VGroup(*[VMobject(stroke_width=w) for w, _ in COUCHES])

        def maj_toile(g):
            u = t.get_value()
            n, m = densite_courante(u), table_courante(u)
            op = paraitre(u, T_DENSE - 0.1, 0.5)
            # un éclat bref chaque fois que le dessin change : dernier
            # changement survenu avant l'instant courant
            changements = ([T_DENSE + i * PAS_DENSE for i in range(3)]
                           + [T_TABLES + i * PAS_TABLE for i in range(len(TABLES))])
            repere = max([x for x in changements if x <= u] or [-9])
            f = float(np.clip(1 - (u - repere) / 0.45, 0, 1))
            couleur = BLEU if u < T_TABLES else teinte(200 + 46 * (m - 3))
            pts = cordes(n, m)
            for (w, o), couche in zip(COUCHES, g):
                couche.set_points(pts)
                couche.set_stroke(color=couleur,
                                  width=w * (1 + 0.35 * f),
                                  opacity=o * op * (1 + 0.8 * f))

        toile.add_updater(maj_toile)

        # compteur de points pendant la densification
        def ligne_points(n):
            return texte(f"{n} points", 0.62, CLAIR, gras=True).move_to([0, -4.55, 0])

        compte = ligne_points(DENSITES[0])
        compte.affiche = -1

        def maj_compte(m):
            u = t.get_value()
            if not (T_DENSE - 0.2 <= u < T_COEUR + 0.2):
                m.set_opacity(0)
                return
            n = densite_courante(u)
            if n != m.affiche:
                m.become(ligne_points(n))
                m.affiche = n
            m.set_opacity(1)

        compte.add_updater(maj_compte)

        coeur = VGroup(
            texte("même règle,", 0.52, GRIS),
            texte("un cœur apparaît", 0.66, CHAUD, gras=True),
        ).arrange(DOWN, buff=0.16)
        coeur.move_to([0, -4.75, 0])
        coeur.add_updater(lambda g: g.set_opacity(
            paraitre(t.get_value(), T_COEUR, 0.4, T_TABLES - 0.3, 0.4)))

        # ------------------------------------------------------------------
        #  Étape 6 — le défilé des tables, avec le nombre de pointes
        # ------------------------------------------------------------------
        def ligne_table(m):
            g = VGroup(
                texte(f"table de {m}", 0.72, CLAIR, gras=True),
                texte(f"{m - 1} pointes", 0.48, GRIS),
            ).arrange(DOWN, buff=0.18)
            return g.move_to([0, -4.75, 0])

        defile = ligne_table(3)
        defile.affiche = -1

        def maj_defile(g):
            u = t.get_value()
            if not (T_TABLES - 0.1 <= u < T_FINAL + 0.2):
                g.set_opacity(0)
                return
            m = table_courante(u)
            if m != g.affiche:
                g.become(ligne_table(m))
                g.affiche = m
            g.set_opacity(1)

        defile.add_updater(maj_defile)

        # ------------------------------------------------------------------
        #  Étape 7 — la règle, en une ligne
        # ------------------------------------------------------------------
        final = VGroup(
            texte("une seule règle :", 0.54, GRIS),
            texte("relier chaque nombre", 0.60, CLAIR, gras=True),
            texte("à son multiple", 0.60, CLAIR, gras=True),
        ).arrange(DOWN, buff=0.16)
        final.move_to([0, -5.0, 0])
        final.add_updater(lambda g: g.set_opacity(
            paraitre(t.get_value(), T_FINAL + 0.4, 0.6)))

        self.add(cercle, toile, traits, points, etiquettes, curseur,
                 accroche, annonce, calcul, tour, compte, coeur, defile, final)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Texte : toujours par Pango, jamais par LaTeX — rien à installer.
#  On règle la taille sur une hauteur en unités de scène plutôt que par
#  font_size, dont l'effet dépend de la police réellement trouvée.
# --------------------------------------------------------------------------
def texte(contenu, hauteur, couleur, gras=False):
    m = Text(contenu, color=couleur, weight=BOLD if gras else NORMAL)
    largeur_max = config.frame_width - 1.1
    m.scale_to_fit_height(hauteur)
    if m.width > largeur_max:
        m.scale_to_fit_width(largeur_max)
    return m


# --------------------------------------------------------------------------
#  Bande son : entièrement synthétisée. Une note par corde tracée, un accord
#  à chaque densification, une note par table.
# --------------------------------------------------------------------------
def generer_bande_son(chemin="explication.wav", sr=44100):
    import wave

    n = int((DUREE + 1.0) * sr)
    buf = np.zeros(n)

    def poser(debut, onde):
        i0 = max(0, int(debut * sr))
        fin = min(i0 + len(onde), n)
        if fin > i0:
            buf[i0:fin] += onde[: fin - i0]

    def note(freq, duree=1.1, force=0.22, brillance=0.35):
        d = int(duree * sr)
        tt = np.arange(d) / sr
        env = np.exp(-tt * 4.2) * (1 - np.exp(-tt / 0.003))
        return force * env * (np.sin(TAU * freq * tt)
                              + brillance * np.sin(TAU * 2 * freq * tt)
                              + brillance * 0.4 * np.sin(TAU * 3 * freq * tt))

    def grave(force=0.7):
        d = int(0.5 * sr)
        tt = np.arange(d) / sr
        f = 105 * np.exp(-tt * 20) + 48
        return force * 0.8 * np.sin(TAU * np.cumsum(f) / sr) * np.exp(-tt * 8)

    gamme = [0, 2, 4, 7, 9]                     # pentatonique majeure, apaisée
    hauteur = lambda i: 294 * 2 ** ((gamme[i % 5] + 12 * (i // 5)) / 12)

    poser(T_TITRE + 0.25, note(hauteur(0), 2.0, 0.20))
    poser(T_CERCLE, note(hauteur(2), 2.2, 0.20))
    for k in range(N_PETIT):                    # une note par corde
        poser(T_CORDES + k * PAS_CORDE, note(hauteur(k), 1.0, 0.19))
    poser(T_MODULO, note(hauteur(1), 1.8, 0.20, 0.5))
    for i in range(3):                          # densification
        poser(T_DENSE + i * PAS_DENSE, grave(0.55 + 0.15 * i))
        poser(T_DENSE + i * PAS_DENSE, note(hauteur(4 + i), 1.5, 0.17))
    poser(T_COEUR, grave(0.8))
    poser(T_COEUR, note(hauteur(7), 2.6, 0.24, 0.5))
    for i, m in enumerate(TABLES):              # une note par table
        poser(T_TABLES + i * PAS_TABLE, grave(0.5))
        poser(T_TABLES + i * PAS_TABLE, note(hauteur(3 + i), 1.4, 0.18))
    poser(T_FINAL, grave(0.9))
    for j, i in enumerate((0, 4, 7)):           # accord final
        poser(T_FINAL + 0.02 * j, note(hauteur(i), 3.2, 0.20, 0.45))

    buf = np.tanh(buf * 1.1)
    pcm = (buf / max(1e-9, np.abs(buf).max()) * 0.9 * 32767).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Lancement direct : python explication.py
    config.pixel_width, config.pixel_height = 1080, 1920
    config.frame_rate = 60
    Explication().render()
