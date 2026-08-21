"""
Feu contre Air — rendu vidéo, format vertical.

FEU : Une traînée de braises se dépose sur son passage et blesse qui la traverse. Le feu ne frappe pas : il occupe.
AIR : Le plus rapide et le plus fragile. Sa bourrasque le rend insaisissable quelques secondes : il double sa vitesse et ne subit plus les chocs.

Les deux fiches viennent du codex des éléments, à la racine du dépôt : un élément se bat exactement pareil dans ses cinq affiches.

Rendu :
    python duel.py                 # écrit duel.mp4 en 1080 x 1920, 60 im/s
    python duel.py --graines       # essaie des tirages et donne ce qu'ils valent

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
APRES = 3.2                 # s de carte de fin


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
#  Réglages communs à tous les duels d'éléments, identiques à la page voisine
# --------------------------------------------------------------------------
#  La charte et la mécanique sont celles de l'animation 27 : fond crème, carré
#  noir, deux jauges en bas, et deux balles qui portent chacune une arme au bout
#  d'un bras qui tourne.
CREME = (0.980, 0.953, 0.851)
NOIR = (0.0, 0.0, 0.0)
GRIS_MORT = (0.541, 0.525, 0.471)

X0, X1, Y0, Y1 = 60.0, 1020.0, 477.0, 1437.0
EP = 9.0
Y_TITRE = 440.0
Y_JAUGE, H_JAUGE, L_JAUGE = 1452.0, 48.0, 402.0
Y_STAT = 1545.0

R = 67.0
BRAS = 125.0
TETE = 46.0
REPOS = 0.40
T_LIMITE = 95.0
DT = 1 / 240
GRAINE = 0

#  Les deux fiches, recopiées du codex. Elles ne changent pas d'une affiche à
#  l'autre : c'est toute la raison d'être du codex.
FICHES = [{"cle": "feu", "nom": "FEU", "cotes": 0, "teinte": 14, "sat": 95, "pv": 95, "vitesse": 560, "contact": 6, "charge": 10.0, "pouvoir": "brasier", "force": 0.818}, {"cle": "air", "nom": "AIR", "cotes": 3, "teinte": 172, "sat": 48, "pv": 100, "vitesse": 760, "contact": 7, "charge": 6.5, "pouvoir": "bourrasque", "force": 1.366}]


class Combattant:
    def __init__(self, f, i, cap, ang):
        self.f = f
        self.i = i
        self.x = X1 - 280 if i else X0 + 280
        self.y = (Y0 + Y1) / 2
        self.vx = math.cos(cap) * f["vitesse"]
        self.vy = math.sin(cap) * f["vitesse"]
        self.pv = float(f["pv"])
        self.pv_max = float(f["pv"])
        self.ang = ang
        #  Les deux armes ne tournent ni à la même vitesse ni dans le même sens.
        self.omega = (-1 if i else 1) * (1.5 + f["vitesse"] / 700)
        self.charge = 0.0
        self.lancers = 0
        self.etats = {k: 0.0 for k in ("repos", "flash", "rapide", "blinde",
                                       "gele", "regen", "reflet", "embusque",
                                       "rayon", "brasier", "semis")}


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        self.duo = [Combattant(f, i, self.rng.uniform(0, TAU),
                               self.rng.uniform(0, TAU))
                    for i, f in enumerate(FICHES)]
        self.braises = []
        self.eclats = []
        self.nuages = []
        self.traits = []
        self.ondes = []
        self.t = 0.0
        self.fini = None
        self.vainqueur = -1
        self.notes = []

    def bilan(self):
        if self.vainqueur < 0:
            return "sans vainqueur"
        g = self.duo[self.vainqueur]
        return "%s l'emporte, %d pv sur %d" % (
            g.f["nom"], math.ceil(g.pv), g.pv_max)

    def autre(self, b):
        return self.duo[1 - b.i]

    # -- dégâts ----------------------------------------------------------
    def blesser(self, cible, degats, source):
        if self.fini is not None or degats <= 0:
            return
        if cible.etats["blinde"] > 0:
            degats /= 4
        if cible.etats["gele"] > 0:
            degats *= 1.5
        if cible.etats["rapide"] > 0 and source in ("arme", "braise", "eclat"):
            return
        cible.pv = max(0.0, cible.pv - degats)
        cible.etats["flash"] = 0.14
        #  Le reflet ne se reflète pas lui-même : sans ce garde-fou deux
        #  cristaux se renverraient un coup à l'infini.
        if cible.etats["reflet"] > 0 and source != "reflet":
            self.blesser(self.autre(cible), degats * 0.75, "reflet")
        if len(self.notes) < 3000:
            self.notes.append((self.t, 7 if cible.i else 0, 0.12,
                               (cible.x - W / 2) / (W / 2)))
        if cible.pv <= 0 and self.fini is None:
            self.fini = self.t
            self.vainqueur = 1 - cible.i

    # -- les douze pouvoirs ----------------------------------------------
    def pouvoir(self, b):
        e = self.autre(b)
        p = b.f["pouvoir"]
        force = b.f["force"]
        b.lancers += 1
        self.ondes.append({"x": b.x, "y": b.y, "h": b.f["teinte"],
                           "s": b.f["sat"], "vie": 0.6})
        if p == "brasier":
            b.etats["brasier"] = 4.2 * force
        elif p == "ressac":
            d = math.hypot(e.x - b.x, e.y - b.y) or 1e-9
            nx, ny = (e.x - b.x) / d, (e.y - b.y) / d
            s = math.hypot(e.vx, e.vy)
            e.vx, e.vy = nx * s, ny * s
            e.x = min(max(e.x + nx * 190, X0 + EP + R), X1 - EP - R)
            e.y = min(max(e.y + ny * 190, Y0 + EP + R), Y1 - EP - R)
            self.blesser(e, 14 * force, "ressac")
        elif p == "bourrasque":
            b.etats["rapide"] = 3.2 * force
        elif p == "carapace":
            b.etats["blinde"] = 5.5 * force
        elif p == "eclair":
            self.traits.append({"ax": b.x, "ay": b.y, "bx": e.x, "by": e.y,
                                "h": b.f["teinte"], "s": b.f["sat"], "vie": 0.3})
            self.blesser(e, 17 * force, "eclair")
        elif p == "gel":
            #  Un gelé est cassant : il encaisse moitié plus. Sans cela le gel
            #  n'était qu'une pause et la glace perdait tous ses duels.
            e.etats["gele"] = 2.6 * force
            self.blesser(e, 13 * force, "gel")
        elif p == "eclats":
            a0 = math.atan2(e.y - b.y, e.x - b.x)
            for k in range(6):
                a = a0 + (k - 2.5) * 0.30
                self.eclats.append({
                    "x": b.x + math.cos(a) * R, "y": b.y + math.sin(a) * R,
                    "vx": math.cos(a) * 720, "vy": math.sin(a) * 720,
                    "h": b.f["teinte"], "s": b.f["sat"], "i": b.i,
                    "vie": 3.2, "deg": 5.5 * force})
        elif p == "racines":
            b.etats["regen"] = 4.0 * force
        elif p == "pas":
            #  Le bond frappe lui-même : simple repositionnement, il ne valait
            #  rien — le corps à corps est trop rare pour qu'une mise en place
            #  paie, et l'ombre restait à 18 % de victoires.
            s = math.hypot(e.vx, e.vy) or 1e-9
            b.x = min(max(e.x - e.vx / s * 2.2 * R, X0 + EP + R), X1 - EP - R)
            b.y = min(max(e.y - e.vy / s * 2.2 * R, Y0 + EP + R), Y1 - EP - R)
            self.blesser(e, 12 * force, "pas")
            b.etats["embusque"] = 3.0 * force
        elif p == "rayon":
            b.etats["rayon"] = 3.2 * force
        elif p == "nuage":
            self.nuages.append({"x": e.x, "y": e.y, "r": 180.0,
                                "h": b.f["teinte"], "s": b.f["sat"], "i": b.i,
                                "vie": 10.0, "deg": 12 * force})
        elif p == "reflet":
            b.etats["reflet"] = 5.0 * force

    # -- physique ---------------------------------------------------------
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
        a, b = self.duo
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        if d >= 2 * R or d < 1e-9:
            return
        nx, ny = dx / d, dy / d
        corr = (2 * R - d) / 2
        a.x -= nx * corr; a.y -= ny * corr
        b.x += nx * corr; b.y += ny * corr
        vn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
        if vn > 0:
            return
        a.vx += vn * nx; a.vy += vn * ny
        b.vx -= vn * nx; b.vy -= vn * ny

    def armes(self):
        """La tête de l'arme contre la balle d'en face — la mécanique de la
        27."""
        for b in self.duo:
            if b.etats["repos"] > 0 or b.etats["gele"] > 0:
                continue
            c = self.autre(b)
            hx = b.x + math.cos(b.ang) * (BRAS + 32)
            hy = b.y + math.sin(b.ang) * (BRAS + 32)
            if math.hypot(c.x - hx, c.y - hy) < R + TETE:
                b.etats["repos"] = REPOS
                mult = 2.5 if b.etats["embusque"] > 0 else 1.0
                if mult > 1:
                    b.etats["embusque"] = 0.0
                self.blesser(c, b.f["contact"] * mult, "arme")

    def pas(self):
        self.t += DT
        if self.fini is not None:
            return

        #  Ordre tiré à pile ou face : sur un plateau symétrique, un ordre fixe
        #  devient un avantage fixe.
        ordre = self.duo if self.rng.random() < 0.5 else self.duo[::-1]
        for b in ordre:
            for k in ("repos", "flash", "rapide", "blinde", "gele", "regen",
                      "reflet", "embusque", "rayon"):
                b.etats[k] = max(0.0, b.etats[k] - DT)
            if b.etats["brasier"] > 0:
                #  Une braise tous les dixièmes de seconde, pas à chaque pas de
                #  calcul : tirée par pas, elle tombait soixante-douze fois par
                #  seconde et le feu gagnait 99 duels sur 100.
                b.etats["brasier"] -= DT
                b.etats["semis"] += DT
                if b.etats["semis"] >= 0.11:
                    b.etats["semis"] = 0.0
                    self.braises.append({"x": b.x, "y": b.y,
                                         "h": b.f["teinte"], "s": b.f["sat"],
                                         "i": b.i, "vie": 4.0,
                                         "deg": 5 * b.f["force"]})
            if b.etats["regen"] > 0:
                b.pv = min(b.pv_max, b.pv + 4.2 * b.f["force"] * DT)
            if b.etats["gele"] > 0:
                continue
            b.charge += DT
            if b.charge >= b.f["charge"]:
                b.charge = 0.0
                self.pouvoir(b)
            v = b.f["vitesse"] * (2 if b.etats["rapide"] > 0 else 1)
            s = math.hypot(b.vx, b.vy) or 1e-9
            b.vx *= v / s; b.vy *= v / s
            b.ang += b.omega * (2 if b.etats["rapide"] > 0 else 1) * DT
            b.x += b.vx * DT
            b.y += b.vy * DT
            self.murs(b)
        self.entre_elles()
        self.armes()

        for b in self.duo:
            if b.etats["rayon"] > 0:
                self.blesser(self.autre(b), 10 * b.f["force"] * DT, "rayon")

        for o in self.braises:
            o["vie"] -= DT
            c = self.duo[1 - o["i"]]
            if o["vie"] > 0 and math.hypot(c.x - o["x"], c.y - o["y"]) < R + 16:
                o["vie"] = 0.0
                self.blesser(c, o["deg"], "braise")
        self.braises = [o for o in self.braises if o["vie"] > 0]

        for o in self.eclats:
            o["vie"] -= DT
            o["x"] += o["vx"] * DT
            o["y"] += o["vy"] * DT
            if not X0 + EP < o["x"] < X1 - EP:
                o["vx"] = -o["vx"]
                o["x"] = min(max(o["x"], X0 + EP), X1 - EP)
            if not Y0 + EP < o["y"] < Y1 - EP:
                o["vy"] = -o["vy"]
                o["y"] = min(max(o["y"], Y0 + EP), Y1 - EP)
            c = self.duo[1 - o["i"]]
            if o["vie"] > 0 and math.hypot(c.x - o["x"], c.y - o["y"]) < R + 10:
                o["vie"] = 0.0
                self.blesser(c, o["deg"], "eclat")
        self.eclats = [o for o in self.eclats if o["vie"] > 0]

        for o in self.nuages:
            o["vie"] -= DT
            c = self.duo[1 - o["i"]]
            if math.hypot(c.x - o["x"], c.y - o["y"]) < o["r"]:
                self.blesser(c, o["deg"] * DT, "nuage")
        self.nuages = [o for o in self.nuages if o["vie"] > 0]

        for o in self.traits:
            o["vie"] -= DT
        self.traits = [o for o in self.traits if o["vie"] > 0]
        for o in self.ondes:
            o["vie"] -= DT
        self.ondes = [o for o in self.ondes if o["vie"] > 0]

        #  Deux éléments très défensifs s'annulent : au bout du compte, la plus
        #  grosse part de vie restante l'emporte.
        if self.t > T_LIMITE and self.fini is None:
            self.fini = self.t
            a, b = self.duo
            pa, pb = a.pv / a.pv_max, b.pv / b.pv_max
            self.vainqueur = (int(self.rng.random() < 0.5) if pa == pb
                              else (0 if pa > pb else 1))


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def coul(h, s, l, a=1.0):
    return teinte(h, s / 100.0, l / 100.0) + (a,)


def forme(ctx, x, y, r, cotes, ang):
    ctx.new_path()
    if cotes == 0:
        ctx.arc(x, y, r, 0, TAU)
        return
    n = 16 if cotes == -1 else cotes
    for k in range(n):
        if cotes == -1:
            a = ang + k * math.pi / 8
            rr = r * 0.44 if k % 2 else r
        else:
            a = ang + k * TAU / cotes
            rr = r
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        (ctx.line_to if k else ctx.move_to)(px, py)
    ctx.close_path()


def jauge(ctx, x, y, l, h, frac, c):
    ctx.set_source_rgb(0.078, 0.102, 0.141)
    ctx.rectangle(x, y, l, h)
    ctx.fill()
    ctx.set_source_rgba(*c)
    ctx.rectangle(x, y, l * min(1.0, max(0.0, frac)), h)
    ctx.fill()


def cerne(ctx, s, x, y, taille, coul, align="gauche", ep=7.0):
    """Texte gras cerné de noir : la lettre de la 27."""
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(taille)
    ext = ctx.text_extents(s)
    if align == "centre":
        dx = -(ext.width / 2 + ext.x_bearing)
    elif align == "droite":
        dx = -(ext.width + ext.x_bearing)
    else:
        dx = -ext.x_bearing
    ctx.new_path()
    ctx.move_to(x + dx, y)
    ctx.text_path(s)
    if ep:
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(ep)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*coul)
    ctx.fill()


def arme(ctx, b, mort):
    """Le manche part du centre de la balle et sort du disque, et la tête est
    la forme de l'élément : c'est à elle qu'on le reconnaît d'un duel à
    l'autre, avant même de lire son nom."""
    ax = b.x + math.cos(b.ang) * BRAS
    ay = b.y + math.sin(b.ang) * BRAS
    ctx.set_source_rgb(*(GRIS_MORT if mort else (0.169, 0.169, 0.200)))
    ctx.set_line_width(15)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.move_to(b.x, b.y)
    ctx.line_to(ax + math.cos(b.ang) * 18, ay + math.sin(b.ang) * 18)
    ctx.stroke()
    forme(ctx, ax + math.cos(b.ang) * 30, ay + math.sin(b.ang) * 30, TETE,
          b.f["cotes"], b.ang)
    if mort:
        ctx.set_source_rgb(*GRIS_MORT)
    else:
        ctx.set_source_rgba(*coul(b.f["teinte"], b.f["sat"], 55))
    ctx.fill_preserve()
    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(5)
    ctx.stroke()


def jauge(ctx, x, gauche, frac, c, nom, mort):
    ctx.set_source_rgb(*CREME)
    ctx.rectangle(x, Y_JAUGE, L_JAUGE, H_JAUGE)
    ctx.fill()
    l = L_JAUGE * min(1.0, frac)
    ctx.set_source_rgba(*((GRIS_MORT + (1.0,)) if mort else c))
    ctx.rectangle(x if gauche else x + L_JAUGE - l, Y_JAUGE, l, H_JAUGE)
    ctx.fill()
    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(4)
    ctx.rectangle(x + 2, Y_JAUGE + 2, L_JAUGE - 4, H_JAUGE - 4)
    ctx.stroke()
    cerne(ctx, nom, x + 12 if gauche else x + L_JAUGE - 12, Y_JAUGE + 35, 30,
          (GRIS_MORT + (1.0,)) if mort else (1.0, 1.0, 1.0, 1.0),
          "gauche" if gauche else "droite", 6)


def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(*CREME)
    ctx.paint()

    A, B = FICHES
    mortA = jeu.vainqueur == 1
    mortB = jeu.vainqueur == 0

    # --- l'arène et ce qu'elle enferme -----------------------------------
    ctx.save()
    ctx.new_path()
    ctx.rectangle(X0 + EP, Y0 + EP, X1 - X0 - 2 * EP, Y1 - Y0 - 2 * EP)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.clip()

    for o in jeu.nuages:
        v = min(1.0, o["vie"] / 1.5)
        deg = cairo.RadialGradient(o["x"], o["y"], 0, o["x"], o["y"], o["r"])
        r, g, b = teinte(o["h"], o["s"] / 100.0, 0.52)
        deg.add_color_stop_rgba(0, r, g, b, 0.45 * v)
        deg.add_color_stop_rgba(1, r, g, b, 0.0)
        ctx.set_source(deg)
        ctx.new_path(); ctx.arc(o["x"], o["y"], o["r"], 0, TAU); ctx.fill()
    for o in jeu.braises:
        v = min(1.0, o["vie"] / 1.2)
        ctx.set_source_rgba(*coul(o["h"], o["s"], 52, 0.8 * v))
        ctx.new_path(); ctx.arc(o["x"], o["y"], 13 * v + 4, 0, TAU); ctx.fill()
    for o in jeu.eclats:
        ctx.set_source_rgba(*coul(o["h"], o["s"], 45, min(1.0, o["vie"])))
        ctx.set_line_width(5)
        ctx.new_path()
        ctx.move_to(o["x"], o["y"])
        ctx.line_to(o["x"] - o["vx"] * 0.022, o["y"] - o["vy"] * 0.022)
        ctx.stroke()
    for o in jeu.traits:
        v = o["vie"] / 0.3
        ctx.set_source_rgba(*coul(o["h"], o["s"], 50, v))
        ctx.set_line_width(11 * v)
        ctx.new_path(); ctx.move_to(o["ax"], o["ay"]); ctx.line_to(o["bx"], o["by"])
        ctx.stroke()
    for b in jeu.duo:
        if b.etats["rayon"] <= 0:
            continue
        e = jeu.autre(b)
        ctx.set_source_rgba(*coul(b.f["teinte"], b.f["sat"], 55, 0.9))
        ctx.set_line_width(18)
        ctx.new_path(); ctx.move_to(b.x, b.y); ctx.line_to(e.x, e.y); ctx.stroke()
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(5)
        ctx.new_path(); ctx.move_to(b.x, b.y); ctx.line_to(e.x, e.y); ctx.stroke()
    for o in jeu.ondes:
        v = o["vie"] / 0.6
        ctx.set_source_rgba(*coul(o["h"], o["s"], 50, 0.65 * v))
        ctx.set_line_width(6 * v)
        ctx.new_path(); ctx.arc(o["x"], o["y"], R + 210 * (1 - v), 0, TAU)
        ctx.stroke()
    ctx.restore()

    ctx.set_source_rgb(*NOIR)
    ctx.set_line_width(EP * 2)
    ctx.rectangle(X0, Y0, X1 - X0, Y1 - Y0)
    ctx.stroke()

    # --- les deux éléments, par-dessus le cadre comme dans la 27 ----------
    for b in jeu.duo:
        mort = jeu.vainqueur == 1 - b.i
        if mort:
            v = 1 - min(1.0, (jeu.t - jeu.fini) / 0.7)
            if v <= 0:
                continue
            ctx.set_source_rgba(1, 1, 1, v)
            ctx.new_path()
            ctx.arc(b.x, b.y, R * (1 + (1 - v) * 0.5), 0, TAU)
            ctx.fill()
            continue
        #  Les auras d'état : on doit pouvoir lire d'un coup d'œil ce qui
        #  protège ou entrave chacun.
        auras = []
        if b.etats["blinde"] > 0:
            auras.append(((0.659, 0.455, 0.122), b.etats["blinde"]))
        if b.etats["reflet"] > 0:
            auras.append((teinte(322, 0.88, 0.50), b.etats["reflet"]))
        if b.etats["rapide"] > 0:
            auras.append((teinte(172, 0.60, 0.45), b.etats["rapide"]))
        if b.etats["regen"] > 0:
            auras.append((teinte(108, 0.85, 0.40), b.etats["regen"]))
        if b.etats["gele"] > 0:
            auras.append((teinte(196, 0.88, 0.50), b.etats["gele"]))
        for k, (c, v) in enumerate(auras):
            ctx.set_source_rgba(c[0], c[1], c[2], min(1.0, v) * 0.85)
            ctx.set_line_width(4)
            ctx.new_path()
            ctx.arc(b.x, b.y, R + 12 + k * 10, 0, TAU)
            ctx.stroke()

        arme(ctx, b, False)
        if b.etats["flash"] > 0:
            ctx.set_source_rgb(1, 1, 1)
        else:
            ctx.set_source_rgba(*coul(b.f["teinte"], b.f["sat"], 55))
        ctx.new_path()
        ctx.arc(b.x, b.y, R, 0, TAU)
        ctx.fill_preserve()
        ctx.set_source_rgb(*NOIR)
        ctx.set_line_width(5)
        ctx.stroke()
        cerne(ctx, str(math.ceil(b.pv)), b.x, b.y + 21, 58, (0, 0, 0, 1),
              "centre", 0)

    # --- jauges et compteurs ---------------------------------------------
    jauge(ctx, X0, True, jeu.duo[0].charge / A["charge"],
          coul(A["teinte"], A["sat"], 50), A["pouvoir"].upper(), mortA)
    jauge(ctx, X1 - L_JAUGE, False, jeu.duo[1].charge / B["charge"],
          coul(B["teinte"], B["sat"], 50), B["pouvoir"].upper(), mortB)

    cerne(ctx, "%s × %d" % (A["pouvoir"], jeu.duo[0].lancers), X0, Y_STAT, 40,
          (GRIS_MORT + (1.0,)) if mortA else coul(A["teinte"], A["sat"], 45),
          "gauche")
    cerne(ctx, "%s × %d" % (B["pouvoir"], jeu.duo[1].lancers), X1, Y_STAT, 40,
          (GRIS_MORT + (1.0,)) if mortB else coul(B["teinte"], B["sat"], 45),
          "droite")

    # --- titre, en dernier -----------------------------------------------
    lA = mesure(ctx, A["nom"], 76)
    lB = mesure(ctx, B["nom"], 76)
    lV = mesure(ctx, "VS", 47) + 16
    x = W / 2 - (lA + 112 + lV + 112 + lB) / 2
    cerne(ctx, A["nom"], x, Y_TITRE, 76,
          (GRIS_MORT + (1.0,)) if mortA else coul(A["teinte"], A["sat"], 50))
    x += lA + 22
    for fiche, mort in ((A, mortA),):
        forme(ctx, x + 34, Y_TITRE - 24, 32, fiche["cotes"], 0)
        ctx.set_source_rgba(*((GRIS_MORT + (1.0,)) if mort
                              else coul(fiche["teinte"], fiche["sat"], 55)))
        ctx.fill_preserve()
        ctx.set_source_rgb(*NOIR); ctx.set_line_width(5); ctx.stroke()
    x += 90
    cerne(ctx, "VS", x, Y_TITRE - 6, 47, (0.231, 0.231, 0.231, 1.0), "gauche", 5)
    x += lV + 22
    for fiche, mort in ((B, mortB),):
        forme(ctx, x + 34, Y_TITRE - 24, 32, fiche["cotes"], 0)
        ctx.set_source_rgba(*((GRIS_MORT + (1.0,)) if mort
                              else coul(fiche["teinte"], fiche["sat"], 55)))
        ctx.fill_preserve()
        ctx.set_source_rgb(*NOIR); ctx.set_line_width(5); ctx.stroke()
    x += 90
    cerne(ctx, B["nom"], x, Y_TITRE, 76,
          (GRIS_MORT + (1.0,)) if mortB else coul(B["teinte"], B["sat"], 50))


def mesure(ctx, s, taille):
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(taille)
    return ctx.text_extents(s).width


def ecrire(ctx, s, x, y, taille, couleur, align="gauche", gras=True):
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if gras else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(taille)
    ext = ctx.text_extents(s)
    if align == "centre":
        dx = -(ext.width / 2 + ext.x_bearing)
    elif align == "droite":
        dx = -(ext.width + ext.x_bearing)
    else:
        dx = -ext.x_bearing
    ctx.new_path()
    ctx.move_to(x + dx, y)
    ctx.set_source_rgba(*couleur)
    ctx.show_text(s)


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


def rendre(graine=GRAINE, sortie="duel.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "duel-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "duel.wav")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", muet,
                    "-i", son, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", sortie], check=True)
    print("%s : %.1f s, %d images — %s" % (sortie, duree, images, jeu.bilan()))
    return duree


if __name__ == "__main__":
    if "--graines" in sys.argv:
        print("graine   durée  bilan")
        for g in range(6):
            jeu = Partie(g)
            while jeu.fini is None and jeu.t < 200:
                jeu.pas()
            print("%5d %7.1f  %s" % (g, jeu.t, jeu.bilan()))
    else:
        rendre()
