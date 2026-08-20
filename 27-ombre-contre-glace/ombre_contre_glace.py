"""
Ombre contre Glace — rendu vidéo, format vertical.

Deux balles armées, chacune portant une arme au bout d'un bras qui tourne.
L'arme qui touche la balle adverse lui prend des points de vie. À côté du corps
à corps, chaque camp charge un pouvoir : le lien d'essence pour l'ombre, le
blizzard pour la glace. Le premier à zéro perd.

Reproduction d'une vidéo existante, refaite de zéro : mécanique, disposition et
couleurs relevées image par image. Les armes et les emblèmes sont redessinés,
les intitulés traduits, et la marque de l'auteur n'est pas reprise.

Rendu :
    python ombre_contre_glace.py                 # écrit ombre_contre_glace.mp4 en 1080 x 1920, 60 im/s
    python ombre_contre_glace.py --graines       # essaie des tirages et donne ce qu'ils valent

Pourquoi Cairo et non Manim, comme la plupart des animations du dépôt : Manim
est fait pour des scènes — des objets nommés, peu nombreux, qu'on anime — et
reconstruit ses objets vectoriels à chaque image. Mesuré sur ce genre de contenu
dans `16-la-prison`, il est vingt-quatre fois plus lent que Cairo pour un
résultat identique. Les images brutes partent directement dans ffmpeg par un
tube, sans passer par des milliers de PNG sur le disque ; le son est fabriqué à
part, puis collé.
"""

import colorsys
import math
import subprocess
import sys
import wave

import cairo
import numpy as np

TAU = 2 * math.pi
W, H = 1080, 1920
FPS = 60
APRES = 2.5                 # s de carte de fin


def teinte(h, s=0.80, l=0.62):
    """Une couleur, de la teinte au triplet Cairo."""
    return colorsys.hls_to_rgb((h % 360) / 360, l, s)


def texte(ctx, s, x, y, taille, couleur, gras=True, cerne=8.0):
    """Texte centré, cerné de sombre — sans quoi il se perd sur le décor."""
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if gras else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(taille)
    ext = ctx.text_extents(s)
    ctx.new_path()
    ctx.move_to(x - (ext.width / 2 + ext.x_bearing), y)
    ctx.text_path(s)
    if cerne:
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.9)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(cerne)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*couleur)
    ctx.fill()


# --------------------------------------------------------------------------
#  Réglages, identiques à la page voisine
# --------------------------------------------------------------------------
CREME = (0.980, 0.953, 0.851)
NOIR = (0.0, 0.0, 0.0)
VIOLET = (0.533, 0.004, 0.545)
CYAN = (0.020, 1.0, 1.0)
VIOLET_SOMBRE = (0.216, 0.024, 0.475)
GRIS_MORT = (0.541, 0.525, 0.471)

#  Tout est à l'échelle 1,5 de la vidéo, qui fait 720 x 1280.
X0, X1, Y0, Y1 = 60.0, 1020.0, 477.0, 1437.0
EP = 9.0
Y_TITRE = 440.0
Y_JAUGE, H_JAUGE, L_JAUGE = 1452.0, 48.0, 402.0
Y_STAT = 1545.0

R = 67.0
PV0 = 100.0
V0 = 620.0
BRAS = 125.0
TETE_ARME = 46.0
REPOS = 0.34
DEG_MELEE = 1.0

CH_LIEN, CH_BLIZZARD = 19.0, 10.5
LIEN_OUVRE, LIEN_TIENT, LIEN_FERME = 0.85, 7.0, 1.2
LIEN_RAYON = 470.0
LIEN_DRAIN = 3.6

PAS_BOND = 210.0
LAMES_PER, LAMES_DEG, LAMES_VIE = 6.0, 3.0, 3.6
BLIZ_N, BLIZ_V, BLIZ_VIE = 6, 760.0, 2.6
BLIZ_RALENTI = 1.3

DT = 1 / 240
GRAINE = 7          # 62,5 s et six points de vie d'écart : la plus serrée des huit


# --------------------------------------------------------------------------
#  Les armes, en pixels — redessinées, pas décalquées
# --------------------------------------------------------------------------
EPEE = (
    '.......oooooo...',
    '..ooo.obbbbbbo..',
    '.ohhhobbwbbbbbo.',
    'ohgghobbbbbbbbbo',
    '.ohhhobbwbbbbbo.',
    '..ooo.obbbbbbo..',
    '.......oooooo...',
)
#  La lame est plus claire que le champ du lien, pas plus sombre : posée à la
#  teinte du fer sombre, elle disparaissait dès que le pouvoir s'ouvrait.
PAL_EPEE = {'o': (0.082, 0.039, 0.118), 'h': (0.200, 0.161, 0.235),
            'g': (0.816, 0.188, 0.910), 'b': (0.290, 0.227, 0.361),
            'w': (0.561, 0.435, 0.690)}

ECLAT = (
    '..oo..',
    '.owwo.',
    'owwbwo',
    'owbwwo',
    '.owwo.',
    '..oo..',
)

PIOCHE = (
    '..........oooo..',
    '.........obbbbo.',
    '.......oobwwwwbo',
    '......obwwwwwwbo',
    '.ooo.obwwwwwwwbo',
    'ohhhobwwwwbwwwbo',
    '.ooo.obwwwwwwwbo',
    '......obwwwwwwbo',
    '.......oobwwwwbo',
    '.........obbbbo.',
    '..........oooo..',
)
PAL_PIOCHE = {'o': (0.039, 0.180, 0.227), 'h': (0.290, 0.290, 0.322),
              'b': (0.224, 0.714, 0.847), 'w': (0.867, 0.984, 1.0)}

LAME_CHUTE = (
    '....oooooo',
    '.ooobbbbbo',
    'ohhobbwbbo',
    '.ooobbbbbo',
    '....oooooo',
)


def pixels(ctx, grille, pal, cx, cy, ang, cell, alpha=1.0):
    h, w = len(grille), len(grille[0])
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    ctx.translate(-w * cell / 2, -h * cell / 2)
    #  Un chemin par couleur : changer la source entre chaque case coûterait
    #  plus cher que la case, et il y a jusqu'à cinq armes à l'image.
    for cle, coul in pal.items():
        ctx.new_path()
        vide = True
        for j in range(h):
            ligne = grille[j]
            for i in range(w):
                if ligne[i] == cle:
                    #  Un demi-pixel de recouvrement : sans lui, la rotation
                    #  laisse des fentes claires entre les cases et l'arme
                    #  paraît grillagée.
                    ctx.rectangle(i * cell, j * cell, cell + 0.6, cell + 0.6)
                    vide = False
        if not vide:
            ctx.set_source_rgba(coul[0], coul[1], coul[2], alpha)
            ctx.fill()
    ctx.restore()


def ecrire(ctx, s, x, y, taille, couleur, align='centre', cerne=7.0):
    """Texte gras cerné de noir, aligné à gauche, au centre ou à droite."""
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(taille)
    ext = ctx.text_extents(s)
    if align == 'centre':
        dx = -(ext.width / 2 + ext.x_bearing)
    elif align == 'droite':
        dx = -(ext.width + ext.x_bearing)
    else:
        dx = -ext.x_bearing
    ctx.new_path()
    ctx.move_to(x + dx, y)
    ctx.text_path(s)
    if cerne:
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(cerne)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*couleur)
    ctx.fill()
    return ext.width


def largeur(ctx, s, taille):
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(taille)
    return ctx.text_extents(s).width


# --------------------------------------------------------------------------
#  Le duel
# --------------------------------------------------------------------------
class Balle:
    def __init__(self, i, x, y, cap, rng):
        self.i = i
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(cap) * V0, math.sin(cap) * V0
        self.pv = PV0
        self.ang = rng.uniform(0, TAU)
        #  Les deux armes ne tournent ni à la même vitesse ni dans le même
        #  sens : à vitesses égales elles se croisent toujours dans la même
        #  figure, et le duel prend un air de mécanique d'horlogerie.
        self.omega = -2.35 if i else 1.85
        self.repos = 0.0
        self.flash = 0.0
        self.gel = 0.0


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        a = self.rng.uniform(0, TAU)
        self.ombre = Balle(0, X0 + 280, (Y0 + Y1) / 2, a, self.rng)
        self.glace = Balle(1, X1 - 280, (Y0 + Y1) / 2, a + math.pi + 0.4, self.rng)
        self.lien = None
        self.motes = []
        self.lames = []
        self.eclats = []
        self.sillages = []
        self.fantomes = []
        self.chLien = 0.0
        self.chBliz = 0.0
        self.tPas = 0.0
        self.perdant = -1
        self.tMort = 0.0
        self.t = 0.0
        self.fini = None
        self.notes = []

    def bilan(self):
        n = ("ombre", "glace")[1 - self.perdant] if self.perdant >= 0 else "?"
        return "%s l'emporte, %d pv restants" % (
            n, math.ceil((self.glace if self.perdant == 0 else self.ombre).pv))

    def pas_delai(self):
        return max(0.7, 3.0 - 0.055 * self.t)

    def degats_glace(self):
        return 1 + int(self.t / 4.4)

    # -- outils ----------------------------------------------------------
    def murs(self, b):
        if b.x < X0 + EP + R:
            b.x = X0 + EP + R; b.vx = abs(b.vx)
        if b.x > X1 - EP - R:
            b.x = X1 - EP - R; b.vx = -abs(b.vx)
        if b.y < Y0 + EP + R:
            b.y = Y0 + EP + R; b.vy = abs(b.vy)
        if b.y > Y1 - EP - R:
            b.y = Y1 - EP - R; b.vy = -abs(b.vy)

    def entre_elles(self):
        o, g = self.ombre, self.glace
        dx, dy = g.x - o.x, g.y - o.y
        d = math.hypot(dx, dy)
        if d >= 2 * R or d < 1e-9:
            return
        nx, ny = dx / d, dy / d
        corr = (2 * R - d) / 2
        o.x -= nx * corr; o.y -= ny * corr
        g.x += nx * corr; g.y += ny * corr
        vn = (g.vx - o.vx) * nx + (g.vy - o.vy) * ny
        if vn > 0:
            return
        o.vx += vn * nx; o.vy += vn * ny
        g.vx -= vn * nx; g.vy -= vn * ny

    def tenir_vitesse(self, b):
        #  La vitesse est tenue à V0, modulée par le gel. Sans cette remise à
        #  niveau, les chocs successifs finissent par vider les deux balles de
        #  leur énergie et le duel s'endort dans un coin.
        cible = V0 * (0.46 if b.gel > 0 else 1.0)
        s = math.hypot(b.vx, b.vy) or 1e-9
        b.vx *= cible / s
        b.vy *= cible / s

    def note(self, i, pan):
        if len(self.notes) < 3000:
            self.notes.append((self.t, 9 if i else 2, 0.13, pan))

    def blesser(self, cible, degats, pan):
        if self.fini is not None:
            return
        cible.pv = max(0.0, cible.pv - degats)
        cible.flash = 0.13
        self.note(cible.i, pan)
        if cible.pv <= 0:
            self.fini = self.t
            self.perdant = cible.i
            self.tMort = self.t

    # -- pouvoirs ---------------------------------------------------------
    def lancer_lien(self):
        self.lien = {"x": self.ombre.x, "y": self.ombre.y, "t": 0.0}
        self.motes = [{"a": self.rng.uniform(0, TAU),
                       "r": math.sqrt(self.rng.uniform(0, 1)) * LIEN_RAYON,
                       "dr": self.rng.uniform(12, 42),
                       "da": self.rng.uniform(-0.125, 0.125),
                       "c": self.rng.uniform(0, 1)} for _ in range(190)]

    def lancer_blizzard(self):
        a0 = math.atan2(self.ombre.y - self.glace.y, self.ombre.x - self.glace.x)
        for k in range(BLIZ_N):
            a = (a0 + (k - (BLIZ_N - 1) / 2) * 0.19
                 + self.rng.uniform(-0.045, 0.045))
            self.eclats.append({
                "x": self.glace.x + math.cos(a) * (R + 18),
                "y": self.glace.y + math.sin(a) * (R + 18),
                "vx": math.cos(a) * BLIZ_V, "vy": math.sin(a) * BLIZ_V,
                "vie": BLIZ_VIE, "tr": [], "ta": 0.0})

    def lancer_lames(self):
        a0 = self.rng.uniform(0, TAU)
        for k in range(3):
            a = a0 + k * 0.5
            self.lames.append({
                "x": self.rng.uniform(X0 + 120, X1 - 120),
                "y": self.rng.uniform(Y0 + 120, Y1 - 120),
                "vx": math.cos(a) * 230, "vy": math.sin(a) * 230,
                "ang": a, "vie": LAMES_VIE})

    # -- un pas -----------------------------------------------------------
    def pas(self):
        avant = self.t
        self.t += DT
        o, g = self.ombre, self.glace
        mort = self.fini is not None

        for b in (o, g):
            if mort and b.i == self.perdant:
                continue
            b.ang += b.omega * DT
            b.gel = max(0.0, b.gel - DT)
            b.repos = max(0.0, b.repos - DT)
            b.flash = max(0.0, b.flash - DT)
            self.tenir_vitesse(b)
            b.x += b.vx * DT
            b.y += b.vy * DT
            self.murs(b)
        if not mort:
            self.entre_elles()

        # --- corps à corps ----------------------------------------------
        if not mort:
            for b in (o, g):
                c = o if b.i else g
                if b.repos > 0:
                    continue
                hx = b.x + math.cos(b.ang) * (BRAS + 32)
                hy = b.y + math.sin(b.ang) * (BRAS + 32)
                if math.hypot(c.x - hx, c.y - hy) < R + TETE_ARME:
                    b.repos = REPOS
                    self.blesser(c, DEG_MELEE, (hx - W / 2) / (W / 2))

        # --- le pas de l'ombre ------------------------------------------
        if not mort or self.perdant == 1:
            self.tPas += DT
            if self.tPas >= self.pas_delai():
                self.tPas = 0.0
                s = math.hypot(o.vx, o.vy) or 1e-9
                ax, ay = o.x, o.y
                o.x = min(max(ax + o.vx / s * PAS_BOND, X0 + EP + R), X1 - EP - R)
                o.y = min(max(ay + o.vy / s * PAS_BOND, Y0 + EP + R), Y1 - EP - R)
                self.sillages.append({"ax": ax, "ay": ay, "bx": o.x, "by": o.y,
                                      "vie": 0.55})
                self.fantomes.append({"x": ax, "y": ay, "vie": 0.5})

        # --- charges -----------------------------------------------------
        if not mort:
            self.chLien += DT
            if self.chLien >= CH_LIEN and self.lien is None:
                self.chLien = 0.0
                self.lancer_lien()
            self.chBliz += DT
            if self.chBliz >= CH_BLIZZARD:
                self.chBliz = 0.0
                self.lancer_blizzard()
            if self.t > 4 and int(self.t / LAMES_PER) != int(avant / LAMES_PER):
                self.lancer_lames()

        # --- le lien d'essence -------------------------------------------
        if self.lien is not None:
            self.lien["t"] += DT
            lt = self.lien["t"]
            if LIEN_OUVRE < lt < LIEN_OUVRE + LIEN_TIENT and not mort:
                g.pv = max(0.0, g.pv - LIEN_DRAIN * DT)
                if g.pv <= 0:
                    self.blesser(g, 0.0, 0.4)
            if lt > LIEN_OUVRE + LIEN_TIENT + LIEN_FERME:
                self.lien = None
                self.motes = []
        for m in self.motes:
            m["a"] += m["da"] * DT
            m["r"] += m["dr"] * DT
            #  Une poussière sortie du disque repart du centre. Avec une durée
            #  de vie propre, elles s'éteignaient toutes vers la septième
            #  seconde et le champ finissait vide alors qu'il tenait encore.
            #  Renaître par tirage uniforme en SURFACE, pas près du centre :
            #  rendues au milieu du disque, les cent quatre-vingt-dix
            #  poussières s'y nouaient en un amas visible en quelques secondes.
            if m["r"] > LIEN_RAYON:
                m["r"] = math.sqrt(self.rng.uniform(0, 1)) * LIEN_RAYON
                m["a"] = self.rng.uniform(0, TAU)

        # --- les éclats de blizzard --------------------------------------
        for e in self.eclats:
            e["vie"] -= DT
            e["x"] += e["vx"] * DT
            e["y"] += e["vy"] * DT
            #  Un éclat qui atteint la paroi s'y brise. Le faire rebondir lui
            #  offrait une deuxième puis une troisième chance de toucher :
            #  mesuré, le blizzard faisait à lui seul 94 dégâts sur les 106
            #  encaissés par l'ombre, et la glace gagnait quarante duels sur
            #  quarante.
            if not (X0 + EP < e["x"] < X1 - EP and Y0 + EP < e["y"] < Y1 - EP):
                e["vie"] = 0.0
            e["ta"] += DT
            if e["ta"] > 0.028:
                e["ta"] = 0.0
                e["tr"].append((e["x"], e["y"]))
                if len(e["tr"]) > 22:
                    e["tr"].pop(0)
            if (not mort and e["vie"] > 0
                    and math.hypot(o.x - e["x"], o.y - e["y"]) < R + 12):
                e["vie"] = 0.0
                o.gel = BLIZ_RALENTI
                self.blesser(o, self.degats_glace(), (e["x"] - W / 2) / (W / 2))
        self.eclats = [e for e in self.eclats if e["vie"] > 0]

        # --- les lames d'ombre -------------------------------------------
        for l in self.lames:
            l["vie"] -= DT
            l["x"] += l["vx"] * DT
            l["y"] += l["vy"] * DT
            l["ang"] += 0.6 * DT
            if (not mort and l["vie"] > 0
                    and math.hypot(g.x - l["x"], g.y - l["y"]) < R + 26):
                l["vie"] = 0.0
                self.blesser(g, LAMES_DEG, (l["x"] - W / 2) / (W / 2))
        self.lames = [l for l in self.lames if l["vie"] > 0]

        for s in self.sillages:
            s["vie"] -= DT
        self.sillages = [s for s in self.sillages if s["vie"] > 0]
        for f in self.fantomes:
            f["vie"] -= DT
        self.fantomes = [f for f in self.fantomes if f["vie"] > 0]


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def jauge(ctx, x, gauche, frac, couleur, nom, mort):
    ctx.set_source_rgb(*CREME)
    ctx.rectangle(x, Y_JAUGE, L_JAUGE, H_JAUGE)
    ctx.fill()
    l = L_JAUGE * min(1.0, frac)
    ctx.set_source_rgb(*(GRIS_MORT if mort else couleur))
    ctx.rectangle(x if gauche else x + L_JAUGE - l, Y_JAUGE, l, H_JAUGE)
    ctx.fill()
    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(4)
    ctx.rectangle(x + 2, Y_JAUGE + 2, L_JAUGE - 4, H_JAUGE - 4)
    ctx.stroke()
    ecrire(ctx, nom, x + 12 if gauche else x + L_JAUGE - 12, Y_JAUGE + 35, 30,
           (GRIS_MORT + (1.0,)) if mort else (1.0, 1.0, 1.0, 1.0),
           'gauche' if gauche else 'droite', 6)


def embleme_ombre(ctx, x, y, r, mort):
    deg = cairo.RadialGradient(x, y, r * 0.1, x, y, r)
    if mort:
        deg.add_color_stop_rgb(0, 0.490, 0.478, 0.439)
        deg.add_color_stop_rgb(0.55, 0.290, 0.282, 0.259)
    else:
        deg.add_color_stop_rgb(0, 0.357, 0.122, 0.816)
        deg.add_color_stop_rgb(0.55, 0.165, 0.027, 0.322)
    deg.add_color_stop_rgb(1, 0.051, 0.008, 0.071)
    ctx.set_source(deg)
    ctx.new_path()
    ctx.arc(x, y, r, 0, TAU)
    ctx.fill_preserve()
    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(5)
    ctx.stroke()


def embleme_glace(ctx, x, y, r, mort):
    ctx.save()
    ctx.translate(x, y)
    ctx.set_source_rgb(*(GRIS_MORT if mort else (0.804, 0.957, 1.0)))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(6):
        ctx.save()
        ctx.rotate(k * math.pi / 3)
        ctx.set_line_width(7)
        ctx.new_path(); ctx.move_to(0, 0); ctx.line_to(0, -r); ctx.stroke()
        ctx.set_line_width(5)
        ctx.new_path()
        ctx.move_to(0, -r * 0.55); ctx.line_to(r * 0.3, -r * 0.8)
        ctx.move_to(0, -r * 0.55); ctx.line_to(-r * 0.3, -r * 0.8)
        ctx.stroke()
        ctx.restore()
    ctx.restore()


def balle(ctx, jeu, b):
    if jeu.fini is not None and b.i == jeu.perdant:
        #  Le perdant ne disparaît pas d'un coup : il laisse un halo blanc qui
        #  s'efface, le temps qu'on comprenne ce qui vient d'arriver.
        v = 1 - min(1.0, (jeu.t - jeu.tMort) / 0.7)
        if v <= 0:
            return
        ctx.set_source_rgba(1, 1, 1, v)
        ctx.new_path()
        ctx.arc(b.x, b.y, R * (1 + (1 - v) * 0.5), 0, TAU)
        ctx.fill()
        return

    base = CYAN if b.i else VIOLET

    #  L'ombre porte un halo qui bat au rythme de sa charge : c'est le seul
    #  indice, dans le cadre, que le pouvoir approche.
    if not b.i:
        p = min(1.0, jeu.chLien / CH_LIEN)
        deg = cairo.RadialGradient(b.x, b.y, R * 0.6, b.x, b.y, R * 1.55)
        deg.add_color_stop_rgba(0, 0.471, 0.235, 0.863, 0.55 * p)
        deg.add_color_stop_rgba(1, 0.471, 0.235, 0.863, 0.0)
        ctx.set_source(deg)
        ctx.new_path(); ctx.arc(b.x, b.y, R * 1.55, 0, TAU); ctx.fill()
    if b.gel > 0:
        ctx.set_source_rgba(0.706, 0.941, 1.0, 0.5 * min(1.0, b.gel))
        ctx.new_path(); ctx.arc(b.x, b.y, R * 1.3, 0, TAU); ctx.fill()

    #  L'arme passe derrière la balle : la vidéo la montre sortir du disque,
    #  pas posée dessus.
    ax = b.x + math.cos(b.ang) * BRAS
    ay = b.y + math.sin(b.ang) * BRAS
    if b.i:
        pixels(ctx, PIOCHE, PAL_PIOCHE, ax, ay, b.ang, 10.5)
    else:
        pixels(ctx, EPEE, PAL_EPEE, ax, ay, b.ang, 10.5)

    ctx.set_source_rgb(*((1, 1, 1) if b.flash > 0 else base))
    ctx.new_path(); ctx.arc(b.x, b.y, R, 0, TAU)
    ctx.fill_preserve()
    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(5)
    ctx.stroke()

    ecrire(ctx, str(math.ceil(b.pv)), b.x, b.y + 21, 58, (0, 0, 0, 1),
           'centre', 0)


def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(*CREME)
    ctx.paint()

    mortO = jeu.perdant == 0
    mortG = jeu.perdant == 1

    #  L'ordre de dessin est relevé sur la vidéo, et il n'est pas celui qu'on
    #  écrirait spontanément : les traînées restent enfermées dans le carré,
    #  mais le champ du lien, les balles et leurs armes le débordent. C'est ce
    #  débordement qui donne au pouvoir son ampleur — contenu dans le cadre, il
    #  n'aurait l'air que d'un disque de plus.
    ctx.save()
    ctx.new_path()
    ctx.rectangle(X0 + EP, Y0 + EP, X1 - X0 - 2 * EP, Y1 - Y0 - 2 * EP)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.clip()

    for l in jeu.lames:
        pixels(ctx, LAME_CHUTE, PAL_EPEE, l["x"], l["y"], l["ang"], 8.5,
               min(1.0, l["vie"] / 0.6))

    for e in jeu.eclats:
        n = len(e["tr"])
        for k in range(n):
            v = (k + 1) / n
            t = 4 + 5 * v
            ctx.set_source_rgba(0.549, 0.882, 1.0, 0.55 * v)
            ctx.rectangle(e["tr"][k][0] - t / 2, e["tr"][k][1] - t / 2, t, t)
            ctx.fill()
        pixels(ctx, ECLAT, PAL_PIOCHE, e["x"], e["y"],
               math.atan2(e["vy"], e["vx"]), 4.6)
    ctx.restore()

    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(EP * 2)
    ctx.rectangle(X0, Y0, X1 - X0, Y1 - Y0)
    ctx.stroke()

    # --- le champ du lien, par-dessus le cadre ---------------------------
    if jeu.lien is not None:
        lt = jeu.lien["t"]
        if lt < LIEN_OUVRE:
            r, a = LIEN_RAYON * (lt / LIEN_OUVRE), 1.0
        elif lt < LIEN_OUVRE + LIEN_TIENT:
            r, a = LIEN_RAYON, 1.0
        else:
            r = LIEN_RAYON
            a = max(0.0, 1 - (lt - LIEN_OUVRE - LIEN_TIENT) / LIEN_FERME)
        lx, ly = jeu.lien["x"], jeu.lien["y"]
        ctx.set_source_rgba(0.110, 0.078, 0.165, 0.79 * a)
        ctx.new_path(); ctx.arc(lx, ly, r, 0, TAU); ctx.fill()
        ctx.set_source_rgba(VIOLET_SOMBRE[0], VIOLET_SOMBRE[1],
                            VIOLET_SOMBRE[2], a)
        ctx.new_path(); ctx.arc(lx, ly, r, 0, TAU)
        ctx.set_line_width(9); ctx.stroke()

        ctx.save()
        ctx.new_path(); ctx.arc(lx, ly, r, 0, TAU); ctx.clip()
        for pale in (False, True):
            ctx.new_path()
            vide = True
            for m in jeu.motes:
                if (m["c"] > 0.5) != pale:
                    continue
                px = lx + math.cos(m["a"]) * m["r"]
                py = ly + math.sin(m["a"]) * m["r"]
                t = 9 + int(m["c"] * 3) * 5
                ctx.rectangle(px, py, t, t)
                vide = False
            if vide:
                continue
            if pale:
                ctx.set_source_rgba(0.588, 0.353, 0.902, 0.85 * a)
            else:
                ctx.set_source_rgba(0.353, 0.157, 0.627, 0.90 * a)
            ctx.fill()
        ctx.restore()

        #  Le fil : c'est lui qui vide la glace, il doit se voir.
        #  Le fil disparaît avec le duel : tracé après la mise à mort, il
        #  partait d'une balle effacée et pendait dans le vide.
        if LIEN_OUVRE < lt < LIEN_OUVRE + LIEN_TIENT and jeu.fini is None:
            ctx.set_source_rgba(0.706, 0.361, 1.0, a)
            ctx.set_line_width(5)
            ctx.new_path()
            ctx.move_to(jeu.ombre.x, jeu.ombre.y)
            ctx.line_to(jeu.glace.x, jeu.glace.y)
            ctx.stroke()

    #  Sillages et fantômes du pas de l'ombre, par-dessus le champ : dessinés
    #  dessous, le voile sombre les réduisait à des taches plates.
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for s in jeu.sillages:
        v = s["vie"] / 0.55
        deg = cairo.LinearGradient(s["ax"], s["ay"], s["bx"], s["by"])
        deg.add_color_stop_rgba(0, 0.353, 0.078, 0.549, 0.05 * v)
        deg.add_color_stop_rgba(1, 0.698, 0.345, 1.0, 0.78 * v)
        ctx.set_source(deg)
        ctx.set_line_width(R * 0.95 * v)
        ctx.new_path()
        ctx.move_to(s["ax"], s["ay"]); ctx.line_to(s["bx"], s["by"])
        ctx.stroke()
    for f in jeu.fantomes:
        v = f["vie"] / 0.5
        ctx.set_source_rgba(0.667, 0.235, 0.863, 0.6 * v)
        ctx.new_path(); ctx.arc(f["x"], f["y"], R * v, 0, TAU); ctx.fill()

    balle(ctx, jeu, jeu.glace)
    balle(ctx, jeu, jeu.ombre)

    # --- jauges et compteurs ---------------------------------------------
    jauge(ctx, X0, True, jeu.chLien / CH_LIEN, VIOLET, "LIEN D'ESSENCE", mortO)
    jauge(ctx, X1 - L_JAUGE, False, jeu.chBliz / CH_BLIZZARD, CYAN,
          'BLIZZARD', mortG)

    ecrire(ctx, "Pas de l'ombre : %s s" % ("%.1f" % jeu.pas_delai()).replace('.', ','),
           X0, Y_STAT, 40, (GRIS_MORT if mortO else VIOLET) + (1.0,), 'gauche')
    ecrire(ctx, "Dégâts / ralent. : %d" % jeu.degats_glace(),
           X1, Y_STAT, 40, (GRIS_MORT if mortG else CYAN) + (1.0,), 'droite')

    # --- titre, en dernier -----------------------------------------------
    #  Le champ du lien monte au-dessus du cadre quand l'ombre est haute ;
    #  posé avant, le titre disparaîtrait sous lui une fois sur trois.
    lO = largeur(ctx, 'OMBRE', 76)
    lG = largeur(ctx, 'GLACE', 76)
    lVs = largeur(ctx, 'VS', 47)
    x = W / 2 - (lO + 112 + lVs + 112 + lG) / 2
    ecrire(ctx, 'OMBRE', x, Y_TITRE, 76,
           (GRIS_MORT if mortO else VIOLET) + (1.0,), 'gauche')
    x += lO + 22
    embleme_ombre(ctx, x + 34, Y_TITRE - 24, 34, mortO)
    x += 90
    ecrire(ctx, 'VS', x, Y_TITRE - 6, 47, (0.231, 0.231, 0.231, 1.0), 'gauche', 5)
    x += lVs + 22
    embleme_glace(ctx, x + 34, Y_TITRE - 24, 34, mortG)
    x += 90
    ecrire(ctx, 'GLACE', x, Y_TITRE, 76,
           (GRIS_MORT if mortG else CYAN) + (1.0,), 'gauche')


# --------------------------------------------------------------------------
#  Bande son. Écrite ici, rien d'emprunté : une cloche par choc, un accord à la
#  fin, le tout passé dans une réverbération.
# --------------------------------------------------------------------------
def bande_son(evenements, fin, duree, chemin, sr=44100):
    """evenements : liste de (instant, demi-ton, force, pan)."""
    n = int((duree + 2.0) * sr)
    gauche, droite = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(5)

    def poser(debut, onde, pan=0.0):
        i0 = max(0, int(debut * sr))
        f = min(i0 + len(onde), n)
        if f > i0:
            g = float(np.clip(0.5 * (1 - pan), 0, 1))
            gauche[i0:f] += g * onde[: f - i0]
            droite[i0:f] += (1 - g) * onde[: f - i0]

    def cloche(demi, force, duree_note=0.8):
        f = 175.0 * 2 ** (demi / 12)
        tt = np.arange(int(duree_note * sr)) / sr
        s = np.zeros_like(tt)
        for mult, amp, chute in ((1, 1.0, 4.0), (2, 0.34, 6.5), (3, 0.13, 9.0)):
            s += amp * np.exp(-tt * chute) * np.sin(TAU * f * mult * tt)
        return force * (1 - np.exp(-tt / 0.002)) * s

    for instant, demi, force, pan in evenements:
        poser(instant, cloche(demi, force), pan)
    for i, demi in enumerate((0, 4, 7, 12)):
        poser(fin + 0.15 + i * 0.11, cloche(demi + 12, 0.26, 1.8))

    def reverbe(sig, ir):
        taille = 1 << (len(sig) + len(ir) - 2).bit_length()
        return np.fft.irfft(np.fft.rfft(sig, taille) * np.fft.rfft(ir, taille),
                            taille)[: len(sig)]

    tt = np.arange(int(1.6 * sr)) / sr
    lissage = np.ones(24) / 24
    for canal in (gauche, droite):
        ir = rng.normal(0, 1, len(tt)) * np.exp(-tt * 3.4)
        ir[: int(0.008 * sr)] *= np.linspace(0, 1, int(0.008 * sr))
        ir = np.convolve(ir, lissage, mode="same")
        canal += 0.32 * reverbe(canal, ir / np.abs(ir).sum() * 6.0)

    stereo = np.stack([np.tanh(gauche * 1.1), np.tanh(droite * 1.1)], axis=1)
    pcm = (stereo / max(1e-9, np.abs(stereo).max()) * 0.92 * 32767).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def rendre(graine=GRAINE, sortie="ombre_contre_glace.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "ombre_contre_glace-muet.mp4"
    proc = subprocess.Popen(
        [ffmpeg(), "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "%dx%d" % (W, H),
         "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "21",
         "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", muet],
        stdin=subprocess.PIPE)

    images = 0
    reste = 0.0
    while True:
        reste += 1 / FPS
        while reste >= DT:
            reste -= DT
            jeu.pas()
        dessiner(ctx, jeu, 1 / FPS)
        surf.flush()
        proc.stdin.write(bytes(surf.get_data()))
        images += 1
        if jeu.fini is not None and jeu.t - jeu.fini > APRES:
            break
        if images > FPS * 200:        # garde-fou
            break

    proc.stdin.close()
    proc.wait()

    duree = images / FPS
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "ombre_contre_glace.wav")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", muet,
                    "-i", son, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", sortie], check=True)
    print("%s : %.1f s, %d images — %s" % (sortie, duree, images, jeu.bilan()))
    return duree


if __name__ == "__main__":
    if "--graines" in sys.argv:
        print("graine   durée  bilan")
        for g in range(8):
            jeu = Partie(g)
            while jeu.fini is None and jeu.t < 200:
                jeu.pas()
            print("%5d %7.1f  %s" % (g, jeu.t, jeu.bilan()))
    else:
        rendre()
