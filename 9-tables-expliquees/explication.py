"""
Les tables de multiplication, expliquées — version commentée, 39 secondes.

Reprend le sujet de l'animation 8, mais autrement : une voix off porte
l'explication, et c'est elle qui donne le tempo. Le script lit la durée réelle
de chaque phrase enregistrée et cale les étapes dessus — donc le dessin ne
devance jamais le commentaire, et refaire une phrase ne dérègle pas le reste.

Rendu (format vertical, YouTube Shorts / TikTok) :
    python3 outils/faire-la-voix.py          # une fois, pour la voix
    manim -r 1080,1920 --fps 60 explication.py TablesExpliquees

Sans les fichiers de voix, le film se rend quand même : les durées de repli
ci-dessous reproduisent le minutage, en muet.
"""

from manim import *
import colorsys
import pathlib
import wave
import numpy as np

# --------------------------------------------------------------------------
#  Repère de la scène — DOIT être au niveau module : la CLI manim importe ce
#  fichier APRÈS avoir lu ses options, donc ces valeurs-là gagnent.
#      manim -r 1080,1920 --fps 60 explication.py TablesExpliquees
# --------------------------------------------------------------------------
config.frame_width = 9.0
config.frame_height = 16.0
config.background_color = "#04060F"

# --------------------------------------------------------------------------
#  La voix mène la danse
# --------------------------------------------------------------------------
VOIX = pathlib.Path(__file__).resolve().parent / "voix"

PHRASES = [
    "Un cercle. Dix nombres, de zéro à neuf.",
    "Relie chaque nombre à son double.",
    "Un donne deux. Deux donne quatre. Trois donne six.",
    "Cinq fois deux : dix. Mais il n'y a pas de dix. Alors on repart de zéro.",
    "On continue. Et voilà la table de deux.",
    "Maintenant, beaucoup plus de nombres.",
    "Quarante. Cent vingt. Deux cent quarante.",
    "Un cœur, dessiné par une table de multiplication.",
    "Change de table, et la figure change.",
    "Trois : deux pointes. Quatre : trois pointes. Toujours une de moins.",
    "Une seule règle. Et tout ça était caché dedans.",
]

#  Durées mesurées sur les fichiers produits par outils/faire-la-voix.py. Elles
#  servent de repli : si la voix manque, le minutage reste celui du montage.
REPLI = [2.86, 1.85, 3.25, 4.89, 2.44, 2.22, 2.66, 3.27, 2.68, 4.32, 2.89]

#  Silence après chaque phrase. Court : c'est ce qui empêche le film de traîner.
RESPIRE = [0.30, 0.20, 0.25, 0.40, 0.30, 0.15, 0.30, 0.45, 0.25, 0.35, 0.00]
AMORCE = 0.25


def duree_wav(chemin, defaut):
    try:
        with wave.open(str(chemin)) as w:
            return w.getnframes() / w.getframerate()
    except (OSError, wave.Error):
        return defaut


DUREES = [duree_wav(VOIX / f"ligne-{i + 1:02d}.wav", REPLI[i])
          for i in range(len(PHRASES))]

DEBUTS, _t = [], AMORCE
for _d, _p in zip(DUREES, RESPIRE):
    DEBUTS.append(_t)
    _t += _d + _p
FINS = [DEBUTS[i] + DUREES[i] for i in range(len(DUREES))]
DUREE = _t + 2.4

# --------------------------------------------------------------------------
#  Réglages du dessin
# --------------------------------------------------------------------------
N_PETIT = 10
DENSITES = [40, 120, 240]
TABLES_LENTES = [3, 4]
TABLES_VITES = [5, 6, 7, 8, 9]
RAYON = 3.05
CENTRE = np.array([0.0, 1.15, 0.0])

BLEU = "#4FC3F7"
CLAIR = "#F2F7FB"
GRIS = "#8B9EB3"
CHAUD = "#FF6B4A"
OR = "#FFC24B"

AVEC_SON = True


# --------------------------------------------------------------------------
#  Formes et couleurs
# --------------------------------------------------------------------------
def doux(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * (3 - 2 * u)


def rebond(u):
    """Arrive en dépassant un peu, puis se pose : un point qui « pop »."""
    u = float(np.clip(u, 0.0, 1.0))
    return 1 - (1 - u) ** 3 * np.cos(6.0 * u)


def paraitre(t, debut, montee=0.35, fin=None, descente=0.35):
    o = doux((t - debut) / montee)
    if fin is not None:
        o *= 1 - doux((t - fin) / descente)
    return o


def teinte(h, l=0.62):
    r, v, b = colorsys.hls_to_rgb((h % 360) / 360, l, 1.0)
    return "#%02X%02X%02X" % (round(r * 255), round(v * 255), round(b * 255))


def sur_cercle(k, n, rayon=RAYON):
    """Point k parmi n : zéro en haut, puis dans le sens des aiguilles."""
    a = np.pi / 2 - TAU * k / n
    return CENTRE + rayon * np.array([np.cos(a), np.sin(a), 0.0])


# --------------------------------------------------------------------------
#  Le calendrier des dix cordes, accroché aux phrases
# --------------------------------------------------------------------------
def calendrier():
    """(k, instant, durée du tracé) pour chacune des dix cordes."""
    plan = []
    # phrase 3 — « un donne deux, deux donne quatre, trois donne six »
    for j, k in enumerate((1, 2, 3)):
        plan.append((k, DEBUTS[2] + 0.15 + j * DUREES[2] / 3.15, 0.32))
    # phrase 4 — quatre, puis le passage par dix
    plan.append((4, DEBUTS[3] + 0.10, 0.32))
    plan.append((5, DEBUTS[3] + DUREES[3] * 0.72, 0.40))
    # phrase 5 — le reste en rafale
    for j, k in enumerate((6, 7, 8, 9, 0)):
        plan.append((k, DEBUTS[4] + j * DUREES[4] / 5.6, 0.24))
    return sorted(plan, key=lambda x: x[1])


PLAN = calendrier()
T_MODULO = DEBUTS[3] + DUREES[3] * 0.72        # l'instant où 5 × 2 dépasse le tour
T_FIGURE = FINS[4]                             # la table de 2 est complète
T_ETIQUETTES = DEBUTS[5]                       # les numéros s'effacent
T_DENSE = DEBUTS[6]                            # 40, 120, 240
T_COEUR = DEBUTS[7]
T_TABLES = DEBUTS[8]
T_LENTES = DEBUTS[9]
T_FINAL = DEBUTS[10]


def densite(t):
    if t < T_DENSE:
        return N_PETIT
    if t >= FINS[6]:
        return DENSITES[-1]
    i = int((t - T_DENSE) / (DUREES[6] / 3))
    return DENSITES[min(i, 2)]


def table(t):
    """Le multiplicateur affiché : 2, puis 3 et 4 posément, puis 5 à 9 vite."""
    if t < T_TABLES:
        return 2
    if t < T_LENTES:
        return 3
    if t < T_FINAL:
        part = DUREES[9] / (len(TABLES_LENTES) + 1)
        i = int((t - T_LENTES) / part)
        if i < len(TABLES_LENTES):
            return TABLES_LENTES[i]
        # dernier tiers de la phrase : on enchaîne
        u = (t - T_LENTES - len(TABLES_LENTES) * part) / max(part, 1e-6)
        return TABLES_VITES[min(int(u * len(TABLES_VITES)), len(TABLES_VITES) - 1)]
    # final : on balaie vite et haut
    u = (t - T_FINAL) / max(DUREE - T_FINAL, 1e-6)
    return 5 + int(u * 12)


def cordes(n, m):
    """Les n cordes k -> m·k, empilées en un seul tableau de points.

    Chaque corde est un cubique de quatre points ; les sous-chemins se séparent
    d'eux-mêmes, la fin d'une corde ne coïncidant pas avec le début de la
    suivante.
    """
    k = np.arange(n)
    a = np.pi / 2 - TAU * k / n
    b = np.pi / 2 - TAU * (m * k % n) / n
    A = CENTRE + RAYON * np.stack([np.cos(a), np.sin(a), np.zeros(n)], axis=1)
    B = CENTRE + RAYON * np.stack([np.cos(b), np.sin(b), np.zeros(n)], axis=1)
    pts = np.empty((4 * n, 3))
    pts[0::4] = A
    pts[1::4] = A + (B - A) / 3
    pts[2::4] = A + 2 * (B - A) / 3
    pts[3::4] = B
    return pts


# --------------------------------------------------------------------------
#  Texte : par Pango, jamais par LaTeX. La taille est réglée sur une hauteur en
#  unités de scène, puis bornée à la largeur du cadre — font_size dépend de la
#  police réellement trouvée, et déborde sans prévenir.
# --------------------------------------------------------------------------
def texte(contenu, hauteur, couleur, gras=False):
    m = Text(contenu, color=couleur, weight=BOLD if gras else NORMAL)
    m.scale_to_fit_height(hauteur)
    if m.width > config.frame_width - 1.0:
        m.scale_to_fit_width(config.frame_width - 1.0)
    return m


def bloc(lignes, hauteur, couleur, gras=True):
    """Empile des lignes courtes plutôt que d'écraser une longue phrase.

    Une seule ligne trop longue finit bornée par la largeur du cadre, donc
    minuscule. Deux lignes courtes restent grandes — et se lisent mieux sur un
    téléphone.
    """
    g = VGroup(*[texte(l, hauteur, couleur, gras) for l in lignes])
    return g.arrange(DOWN, buff=hauteur * 0.35)


# --------------------------------------------------------------------------
#  Scène
# --------------------------------------------------------------------------
class TablesExpliquees(Scene):
    def construct(self):
        t = ValueTracker(0.0)

        # --- le cercle ------------------------------------------------------
        cercle = Circle(radius=RAYON, stroke_color=GRIS, stroke_width=2.5)
        cercle.move_to(CENTRE)
        cercle.add_updater(lambda m: m.set_stroke(
            opacity=0.40 * paraitre(t.get_value(), DEBUTS[0], 0.35)))

        # --- les dix nombres, qui arrivent en dépassant un peu --------------
        points = VGroup(*[Dot(sur_cercle(k, N_PETIT), radius=0.085, color=CLAIR)
                          for k in range(N_PETIT)])
        etiquettes = VGroup(*[texte(str(k), 0.42, GRIS) for k in range(N_PETIT)])
        for k in range(N_PETIT):
            etiquettes[k].move_to(sur_cercle(k, N_PETIT, RAYON + 0.50))
            etiquettes[k].base = etiquettes[k].height

        def maj_reperes(_):
            u = t.get_value()
            evanouir = 1 - doux((u - T_ETIQUETTES) / 0.5)
            for k in range(N_PETIT):
                #  Ils apparaissent pendant la première phrase, dans l'ordre.
                depart = DEBUTS[0] + 0.55 + k * (DUREES[0] - 0.8) / N_PETIT
                av = rebond((u - depart) / 0.30)
                o = float(np.clip(av, 0, 1)) * evanouir
                points[k].set_opacity(o)
                points[k].move_to(sur_cercle(k, N_PETIT))
                if av > 0.01:
                    points[k].width = 0.17 * max(av, 0.05)
                etiquettes[k].set_opacity(o * 0.95)

        points.add_updater(maj_reperes)

        # --- les dix cordes, tracées une par une ---------------------------
        traits = VGroup(*[Line(ORIGIN, ORIGIN, stroke_width=5)
                          for _ in range(N_PETIT)])
        tetes = VGroup(*[Dot(radius=0.10, color=OR) for _ in range(N_PETIT)])

        def maj_traits(_):
            u = t.get_value()
            fondu = 1 - doux((u - T_ETIQUETTES) / 0.55)
            for k, debut, duree in PLAN:
                A, B = sur_cercle(k, N_PETIT), sur_cercle(2 * k % N_PETIT, N_PETIT)
                av = doux((u - debut) / duree)
                if av <= 0:
                    traits[k].set_stroke(opacity=0)
                    tetes[k].set_opacity(0)
                    continue
                #  Un segment de longueur nulle n'a pas de direction : on garde
                #  un epsilon, sinon Manim ne sait pas l'orienter.
                bout = A + (B - A) * max(av, 1e-3)
                traits[k].put_start_and_end_on(A, bout)
                frais = 1 - doux((u - debut - duree) / 0.45)
                traits[k].set_stroke(
                    color=interpolate_color(ManimColor(BLEU), ManimColor(OR), frais),
                    width=5 + 4 * frais,
                    opacity=(0.80 + 0.20 * frais) * fondu)
                #  La tête lumineuse court le long de la corde : c'est ce qui
                #  rend le tracé lisible à cette vitesse.
                vole = av < 1 and np.linalg.norm(B - A) > 0.05
                tetes[k].move_to(bout)
                tetes[k].set_opacity(1.0 * fondu if vole else 0.0)

        traits.add_updater(maj_traits)

        # --- le moment « il n'y a pas de dix » -----------------------------
        badge = texte("5 × 2 = 10", 0.62, CLAIR, gras=True)
        badge.affiche = ""

        def maj_badge(m):
            u = t.get_value()
            if not (T_MODULO - 1.5 <= u < FINS[3] + 0.5):
                m.set_opacity(0)
                return
            veut = "5 × 2 = 10" if u < T_MODULO else "10 → on revient à 0"
            if veut != m.affiche:
                coul = CLAIR if u < T_MODULO else CHAUD
                m.become(texte(veut, 0.62, coul, gras=True))
                m.affiche = veut
            m.move_to([0, -4.35, 0])
            m.set_opacity(1)

        badge.add_updater(maj_badge)

        #  Une flèche fait le tour : on voit le dépassement, on ne le lit pas.
        boucle = Arc(radius=RAYON + 0.95, start_angle=np.pi / 2, angle=-TAU * 0.999,
                     stroke_color=CHAUD, stroke_width=7)
        boucle.shift(CENTRE)

        def maj_boucle(m):
            u = t.get_value()
            av = doux((u - T_MODULO) / 0.75)
            if av <= 0 or u > FINS[3] + 0.4:
                m.set_stroke(opacity=0)
                return
            m.become(Arc(radius=RAYON + 0.95, start_angle=np.pi / 2,
                         angle=-TAU * 0.999 * max(av, 1e-3),
                         stroke_color=CHAUD, stroke_width=7).shift(CENTRE))
            m.set_stroke(opacity=0.9 * (1 - doux((u - FINS[3]) / 0.4)))

        boucle.add_updater(maj_boucle)

        halo_zero = Circle(radius=0.30, stroke_color=CHAUD, stroke_width=6,
                           fill_opacity=0).move_to(sur_cercle(0, N_PETIT))

        def maj_halo(m):
            u = t.get_value()
            age = u - T_MODULO - 0.55
            if not (0 <= age < 0.9):
                m.set_stroke(opacity=0)
                return
            v = 1 - age / 0.9
            m.width = 0.6 + 1.5 * (1 - v)
            m.move_to(sur_cercle(0, N_PETIT))
            m.set_stroke(opacity=0.95 * v, width=3 + 6 * v)

        halo_zero.add_updater(maj_halo)

        # --- la figure dense ------------------------------------------------
        #  Trois épaisseurs superposées : Manim n'a pas de flou, c'est ainsi
        #  qu'on obtient une lueur.
        COUCHES = ((9.0, 0.06), (3.6, 0.17), (1.5, 0.95))
        toile = VGroup(*[VMobject(stroke_width=w) for w, _ in COUCHES])
        instants_cle = ([T_DENSE + i * DUREES[6] / 3 for i in range(3)]
                        + [T_COEUR, T_TABLES, T_LENTES, T_FINAL])

        def maj_toile(g):
            u = t.get_value()
            n, m = densite(u), table(u)
            op = paraitre(u, T_DENSE - 0.15, 0.4)
            repere = max([x for x in instants_cle if x <= u] or [-9])
            f = float(np.clip(1 - (u - repere) / 0.40, 0, 1))
            if u < T_COEUR:
                couleur = BLEU
            elif u < T_TABLES:
                couleur = CHAUD
            else:
                couleur = teinte(205 + 40 * (m - 3))
            pts = cordes(n, m)
            for (w, o), couche in zip(COUCHES, g):
                couche.set_points(pts)
                #  Léger battement : rien ne reste jamais tout à fait immobile.
                couche.rotate(0.06 * np.sin(u * 0.7), about_point=CENTRE)
                couche.set_stroke(color=couleur,
                                  width=w * (1 + 0.30 * f),
                                  opacity=o * op * (1 + 0.7 * f))

        toile.add_updater(maj_toile)

        # --- les cartouches de texte ----------------------------------------
        cartouche = bloc(["", ""], 0.60, CLAIR)
        cartouche.affiche = None

        def libelle(u):
            """Ce qui doit être écrit à l'instant u — au plus une idée à la fois."""
            if DEBUTS[1] <= u < DEBUTS[2] - 0.1:
                return (("chaque nombre", "→ son double"), 0.60, BLEU)
            if T_FIGURE - 0.35 <= u < T_ETIQUETTES - 0.1:
                return (("la table de 2",), 0.74, CLAIR)
            if T_DENSE <= u < T_COEUR - 0.15:
                return ((f"{densite(u)} nombres",), 0.70, CLAIR)
            if T_COEUR <= u < T_TABLES - 0.15:
                return (("un cœur",), 0.86, CHAUD)
            if T_TABLES <= u < T_FINAL - 0.15:
                m = table(u)
                return ((f"table de {m}", f"{m - 1} pointes"), 0.62, CLAIR)
            if u >= T_FINAL:
                return (("relier chaque nombre", "à son multiple"), 0.60, CLAIR)
            return None

        def maj_cartouche(m):
            u = t.get_value()
            veut = libelle(u)
            if veut is None:
                m.set_opacity(0)
                m.affiche = None
                return
            if veut != m.affiche:
                m.become(bloc(veut[0], veut[1], veut[2]))
                m.affiche = veut
            m.move_to([0, -4.55, 0])
            #  Le badge du modulo occupe la même ligne : on lui laisse la place.
            occupe = T_MODULO - 1.5 <= u < FINS[3] + 0.5
            m.set_opacity(0.0 if occupe else 1.0)

        cartouche.add_updater(maj_cartouche)

        self.add(cercle, toile, traits, tetes, points, etiquettes,
                 boucle, halo_zero, badge, cartouche)

        if AVEC_SON:
            self.add_sound(generer_bande_son())

        self.play(t.animate.set_value(DUREE), run_time=DUREE, rate_func=linear)


# --------------------------------------------------------------------------
#  Bande son : la voix aux instants du montage, plus quelques repères sonores
#  discrets. La voix passe devant — les bruits sont là pour marquer, pas pour
#  couvrir.
# --------------------------------------------------------------------------
def generer_bande_son(chemin="narration.wav", sr=44100):
    n = int((DUREE + 0.6) * sr)
    voix = np.zeros(n)
    bruits = np.zeros(n)

    def poser(buf, debut, onde, force=1.0):
        i0 = max(0, int(debut * sr))
        fin = min(i0 + len(onde), n)
        if fin > i0:
            buf[i0:fin] += force * onde[: fin - i0]

    def lire(chemin_wav):
        """Lit un wav mono et le ramène à sr par interpolation linéaire."""
        with wave.open(str(chemin_wav)) as w:
            brut = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
            src = w.getframerate()
        x = brut.astype(np.float64) / 32768.0
        if src == sr:
            return x
        cible = int(len(x) * sr / src)
        return np.interp(np.linspace(0, len(x) - 1, cible),
                         np.arange(len(x)), x)

    for i, debut in enumerate(DEBUTS):
        f = VOIX / f"ligne-{i + 1:02d}.wav"
        if f.exists():
            poser(voix, debut, lire(f))

    def cloche(freq, duree=0.9, force=0.16):
        d = int(duree * sr)
        tt = np.arange(d) / sr
        env = np.exp(-tt * 5.0) * (1 - np.exp(-tt / 0.002))
        return force * env * (np.sin(TAU * freq * tt)
                              + 0.35 * np.sin(TAU * 2 * freq * tt))

    def grave(force=0.35):
        d = int(0.40 * sr)
        tt = np.arange(d) / sr
        f = 100 * np.exp(-tt * 22) + 46
        return force * np.sin(TAU * np.cumsum(f) / sr) * np.exp(-tt * 9)

    gamme = [0, 2, 4, 7, 9]
    hauteur = lambda i: 330 * 2 ** ((gamme[i % 5] + 12 * (i // 5)) / 12)

    for j, (k, debut, _) in enumerate(PLAN):        # une note par corde
        poser(bruits, debut, cloche(hauteur(j), 0.7, 0.13))
    poser(bruits, T_MODULO, grave(0.45))
    poser(bruits, T_MODULO, cloche(hauteur(1), 1.3, 0.15))
    for i in range(3):                              # les trois densifications
        poser(bruits, T_DENSE + i * DUREES[6] / 3, grave(0.30 + 0.07 * i))
    poser(bruits, T_COEUR, grave(0.50))
    poser(bruits, T_COEUR, cloche(hauteur(7), 2.0, 0.17))
    for i, m in enumerate(TABLES_LENTES + TABLES_VITES):
        poser(bruits, T_TABLES + i * (T_FINAL - T_TABLES) / 7, cloche(hauteur(3 + i), 0.8, 0.11))
    poser(bruits, T_FINAL, grave(0.55))
    for j, i in enumerate((0, 4, 7)):
        poser(bruits, T_FINAL + 0.02 * j, cloche(hauteur(i), 2.6, 0.13))

    #  La voix sort de piper à pleine échelle : on la borne avant de mélanger,
    #  sinon la somme sature dès le premier bruit posé dessous.
    crete = max(1e-9, np.abs(voix).max())
    melange = 0.86 * voix / crete + bruits
    melange = np.tanh(melange * 1.05)
    pcm = (melange / max(1e-9, np.abs(melange).max()) * 0.94 * 32767).astype("<i2")

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
    TablesExpliquees().render()
