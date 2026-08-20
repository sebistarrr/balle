"""
Rayons en fusion — rendu vidéo, format vertical.

Une balle sous pesanteur dans un récipient à fond rond. À chaque contact
avec le fond elle grossit d'un cran, et le film s'arrête quand elle le remplit.
De chaque impact part un rayon qui la suit : l'éventail balaie l'espace à mesure
qu'elle se déplace.

Repris des rayons de rebond (4), avec la couleur poussée au maximum — chaque
impact garde la teinte qu'il avait, si bien que l'éventail est un arc-en-ciel et
non un aplat — et tout ce qui pouvait donner du poids aux chocs : traînée, ondes
de choc, étincelles, halo de fond, éclair sur les contacts du fond.

Rendu :
    python rayons_fusion.py                 # écrit rayons_fusion.mp4 en 1080 x 1920, 60 im/s
    python rayons_fusion.py --graines       # essaie des tirages et donne ce qu'ils valent

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
#  Tout est à l'échelle 1,5 de la 4, pour occuper le cadre 9:16 en entier —
#  longueurs, pesanteur et vitesses ensemble. C'est ce qui préserve le
#  mouvement : avec x' = k·x et g' = k·g, la trajectoire est la même agrandie,
#  aux mêmes instants.
CX, RC = 540.0, 412.0             # axe et demi-largeur du récipient
HAUT = 640.0                      # sommet des parois
ARC_CY = 1052.0                   # centre du demi-cercle du bas
R0 = 19.5                         # rayon de départ de la balle
G = 9750.0                        # pesanteur, px/s²
SOMMET = 880.0                    # le centre de la balle ne monte jamais
                                  # au-dessus : elle ne peut pas s'échapper
PAS_RAYON = 1.95                  # ce que gagne le rayon à chaque fond touché
GAIN = 1.004                      # et ce que gagne sa vitesse
DT = 1 / 480
ATTENTE = 1.5                     # pause une fois le récipient rempli

#  La couleur tourne deux fois plus vite qu'à la 4, et de onze crans par choc au
#  lieu de quatre. Comme chaque impact garde la teinte qu'il avait au moment où
#  il s'est produit, l'éventail devient un arc-en-ciel au lieu d'un aplat :
#  c'est le premier des effets, et de loin le plus efficace.
TEINTE_PAR_S = 72.0
TEINTE_PAR_CHOC = 11.0

MAX_TRACE = 130                   # longueur de la traînée de la balle
MAX_ONDES, MAX_ETINCELLES = 40, 700

GRAINE = 7          # la plus courte des huit mesurées : 52,6 s


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        #  La partie est entièrement déterminée : la graine ne sert qu'au cap
        #  de départ, tout le reste suit.
        self.x = CX + 60 + self.rng.uniform(-30, 30)
        self.y = SOMMET
        self.vx, self.vy = 975.0, 0.0
        self.r = R0
        self.teinte = 268.0
        self.chocs = 0
        self.plein = 0.0
        self.impacts = []          # (x, y, teinte)
        self.trace = []            # (x, y, teinte)
        self.ondes = []
        self.etincelles = []
        self.eclair = 0.0
        self.t = 0.0
        self.fini = None
        self.notes = []

    def bilan(self):
        return "%d %% du récipient, %d rebonds" % (
            round(100 * (self.r - R0) / (RC - R0)), self.chocs)

    def contact(self, nx, ny, fond):
        d = 2 * (self.vx * nx + self.vy * ny)
        self.vx -= d * nx
        self.vy -= d * ny          # rebond parfaitement élastique

        ix = CX + nx * RC
        iy = ARC_CY + ny * RC if fond else self.y
        self.impacts.append((ix, iy, self.teinte))
        #  Une onde et une gerbe d'étincelles à chaque contact. Ce sont elles
        #  qui donnent au choc son poids : sans elles, la balle rebondit en
        #  silence.
        self.ondes.append({"x": ix, "y": iy, "r": self.r * 0.6, "vie": 1.0,
                           "h": self.teinte, "dur": 1.0 if fond else 0.6})
        if len(self.ondes) > MAX_ONDES:
            self.ondes.pop(0)
        n = 26 if fond else 12
        a = np.arctan2(-ny, -nx) + self.rng.uniform(-1.1, 1.1, n)
        v = self.rng.uniform(300, 1200, n) * (1.25 if fond else 0.8)
        for k in range(n):
            self.etincelles.append(
                {"x": ix, "y": iy, "vx": float(np.cos(a[k]) * v[k]),
                 "vy": float(np.sin(a[k]) * v[k]), "vie": 1.0,
                 "h": self.teinte + float(self.rng.uniform(0, 40))})
        if len(self.etincelles) > MAX_ETINCELLES:
            del self.etincelles[: len(self.etincelles) - MAX_ETINCELLES]
        if fond:
            self.eclair = 1.0

        self.chocs += 1
        self.teinte -= TEINTE_PAR_CHOC
        if fond:
            self.r = min(RC, self.r + PAS_RAYON)
            self.vx *= GAIN
            self.vy *= GAIN

        #  On repose la balle sur la paroi APRÈS l'avoir fait grossir. Sans cela
        #  elle la chevauche encore d'un cran, le choc se redéclenche à l'image
        #  suivante, et ce doublon rend toute la partie imprévisible.
        self.x = CX + nx * (RC - self.r)
        if fond:
            self.y = ARC_CY + ny * (RC - self.r)

        #  L'énergie est bornée : le centre ne doit jamais dépasser SOMMET, sans
        #  quoi la balle sortirait par le haut, qui est ouvert.
        vmax = math.sqrt(max(0.0, 2 * G * (self.y - SOMMET)))
        s = math.hypot(self.vx, self.vy)
        if s > vmax > 0:
            self.vx *= vmax / s
            self.vy *= vmax / s

        if len(self.notes) < 3000:
            p = (self.r - R0) / (RC - R0)
            self.notes.append((self.t, round(24 * (1 - p)) - 4,
                               0.16 if fond else 0.10, (self.x - CX) / RC))

    def pas(self):
        if self.fini is not None:
            self.t += DT
            return
        self.t += DT
        #  La traînée est relevée toutes les huit images de calcul : à quatre
        #  cent quatre-vingts par seconde, en garder une sur une ferait une
        #  bouillie de points et coûterait cher pour rien.
        if int(self.t * 480) % 8 == 0:
            self.trace.append((self.x, self.y, self.teinte))
            if len(self.trace) > MAX_TRACE:
                self.trace.pop(0)

        self.vy += G * DT
        self.x += self.vx * DT
        self.y += self.vy * DT
        self.teinte -= TEINTE_PAR_S * DT

        if self.y >= ARC_CY:                      # partie ronde du fond
            dx, dy = self.x - CX, self.y - ARC_CY
            d = math.sqrt(dx * dx + dy * dy)
            if d > RC - self.r:
                nx, ny = dx / d, dy / d
                self.x = CX + nx * (RC - self.r)
                self.y = ARC_CY + ny * (RC - self.r)
                self.contact(nx, ny, True)
        elif self.x < CX - RC + self.r:           # paroi gauche
            self.x = CX - RC + self.r
            self.contact(-1.0, 0.0, False)
        elif self.x > CX + RC - self.r:           # paroi droite
            self.x = CX + RC - self.r
            self.contact(1.0, 0.0, False)

        if self.r >= RC - 1e-9:
            self.plein += DT
            if self.plein > ATTENTE:
                self.fini = self.t

    def pas_effets(self, dt):
        """Ondes et étincelles : elles vivent au rythme des images, pas de la
        simulation — ce sont des effets, pas de la physique."""
        for o in list(self.ondes):
            o["vie"] -= dt * 2.2 / o["dur"]
            o["r"] += dt * 900 * o["dur"]
            if o["vie"] <= 0:
                self.ondes.remove(o)
        for e in list(self.etincelles):
            e["vie"] -= dt * 1.6
            if e["vie"] <= 0:
                self.etincelles.remove(e)
                continue
            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt
            e["vy"] += G * 0.25 * dt
            e["vx"] *= 0.985
            e["vy"] *= 0.985
        if self.eclair > 0:
            self.eclair = max(0.0, self.eclair - dt / 0.14)


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def rgba(h, l=0.55, a=1.0):
    return teinte(h, 1.0, l) + (a,)


def dessiner(ctx, jeu, dt):
    jeu.pas_effets(dt)
    p = (jeu.r - R0) / (RC - R0)

    # --- fond : un halo teinté qui monte avec l'avancement -------------------
    #  Un fond noir plat laisse l'éventail flotter dans le vide. Ce halo, centré
    #  sur le récipient et de la couleur du moment, rattache l'image au sujet.
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()
    halo = cairo.RadialGradient(CX, ARC_CY, 0, CX, ARC_CY, RC * 2.4)
    halo.add_color_stop_rgba(0, *rgba(jeu.teinte, 0.50, 0.16 + 0.20 * p))
    halo.add_color_stop_rgba(0.5, *rgba(jeu.teinte + 40, 0.45, 0.05 + 0.08 * p))
    halo.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(halo)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    ctx.push_group()               # tout ce qui suit s'additionne
    ctx.set_operator(cairo.OPERATOR_ADD)

    # --- les rayons ------------------------------------------------------------
    #  Chaque impact garde sa teinte : l'éventail est un arc-en-ciel, et l'on y
    #  lit l'ordre des chocs. Ils sont tracés par lots de teinte proche — un
    #  changement de source par rayon coûterait plus cher que le rayon.
    lots = {}
    for ix, iy, h in jeu.impacts:
        lots.setdefault(int(((h % 360) + 360) % 360 / 15) * 15, []).append((ix, iy))
    for t, liste in lots.items():
        for large, alpha in ((7.0, 0.16), (2.4, 0.46)):
            ctx.new_path()
            for ix, iy in liste:
                ctx.move_to(jeu.x, jeu.y)
                ctx.line_to(ix, iy)
            ctx.set_source_rgba(*rgba(t + 7, 0.62 if large < 4 else 0.74, alpha))
            ctx.set_line_width(large)
            ctx.stroke()

    # --- la traînée ------------------------------------------------------------
    #  Volontairement discrète : à pleine force elle forme une nappe blanche qui
    #  avale l'éventail, et c'est l'éventail le sujet.
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(1, len(jeu.trace)):
        a = i / len(jeu.trace)
        ctx.set_source_rgba(*rgba(jeu.trace[i][2], 0.62, 0.22 * a * a))
        ctx.set_line_width(jeu.r * 0.75 * a)
        ctx.new_path()
        ctx.move_to(jeu.trace[i - 1][0], jeu.trace[i - 1][1])
        ctx.line_to(jeu.trace[i][0], jeu.trace[i][1])
        ctx.stroke()

    # --- ondes de choc ---------------------------------------------------------
    for o in jeu.ondes:
        ctx.set_source_rgba(*rgba(o["h"], 0.66, 0.55 * o["vie"] ** 2))
        ctx.set_line_width(3 + 9 * o["vie"])
        ctx.new_path()
        ctx.arc(o["x"], o["y"], o["r"], 0, TAU)
        ctx.stroke()

    # --- étincelles ------------------------------------------------------------
    for e in jeu.etincelles:
        ctx.set_source_rgba(*rgba(e["h"], 0.70, e["vie"]))
        ctx.new_path()
        ctx.arc(e["x"], e["y"], 2 + 5 * e["vie"], 0, TAU)
        ctx.fill()

    ctx.pop_group_to_source()
    ctx.paint()

    # --- le récipient, en dégradé et cerné de lumière -------------------------
    par = cairo.LinearGradient(CX - RC, HAUT, CX + RC, ARC_CY + RC)
    par.add_color_stop_rgb(0, *teinte(jeu.teinte + 60, 1.0, 0.62))
    par.add_color_stop_rgb(0.5, *teinte(jeu.teinte, 1.0, 0.58))
    par.add_color_stop_rgb(1, *teinte(jeu.teinte - 60, 1.0, 0.62))

    def chemin():
        ctx.new_path()
        ctx.move_to(CX - RC, HAUT)
        ctx.line_to(CX - RC, ARC_CY)
        ctx.arc(CX, ARC_CY, RC, math.pi, TAU)
        ctx.line_to(CX + RC, HAUT)

    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    chemin()
    ctx.set_source(par)
    ctx.set_line_width(16)
    ctx.stroke()
    ctx.restore()
    chemin()
    ctx.set_source(par)
    ctx.set_line_width(5)
    ctx.stroke()

    # --- la balle --------------------------------------------------------------
    souffle = 1 + 0.012 * math.sin(jeu.plein * 16) if jeu.plein > 0 else 1
    rr = jeu.r * souffle
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    for k, a in ((2.4, 0.14), (1.6, 0.22)):
        ctx.set_source_rgba(*rgba(jeu.teinte, 0.58, a))
        ctx.new_path()
        ctx.arc(jeu.x, jeu.y, rr * k, 0, TAU)
        ctx.fill()
    ctx.restore()
    g = cairo.RadialGradient(jeu.x - rr * 0.35, jeu.y - rr * 0.4, rr * 0.05,
                             jeu.x, jeu.y, rr)
    g.add_color_stop_rgb(0, 1, 1, 1)
    g.add_color_stop_rgb(0.45, *teinte(jeu.teinte, 1.0, 0.70))
    g.add_color_stop_rgb(1, *teinte(jeu.teinte - 25, 1.0, 0.44))
    ctx.set_source(g)
    ctx.new_path()
    ctx.arc(jeu.x, jeu.y, rr, 0, TAU)
    ctx.fill_preserve()
    ctx.set_source_rgba(*rgba(jeu.teinte, 0.88, 0.8))
    ctx.set_line_width(2.5)
    ctx.stroke()

    #  Éclair sur les contacts avec le fond. Court et sec : plus long, il délave
    #  l'image au lieu de la ponctuer.
    if jeu.eclair > 0:
        ctx.set_source_rgba(*rgba(jeu.teinte, 0.80, 0.20 * jeu.eclair ** 2))
        ctx.rectangle(0, 0, W, H)
        ctx.fill()

    # --- légende et avancement -------------------------------------------------
    texte(ctx, "plus grosse à chaque rebond", CX, 300, 46, (1, 1, 1, 0.95))
    larg, xg, yg = 2 * RC, CX - RC, H - 210
    ctx.set_source_rgba(1, 1, 1, 0.10)
    ctx.rectangle(xg, yg, larg, 14)
    ctx.fill()
    jauge = cairo.LinearGradient(xg, 0, xg + larg, 0)
    jauge.add_color_stop_rgb(0, *teinte(jeu.teinte + 50, 1.0, 0.60))
    jauge.add_color_stop_rgb(1, *teinte(jeu.teinte - 50, 1.0, 0.60))
    ctx.set_source(jauge)
    ctx.rectangle(xg, yg, max(14, larg * p), 14)
    ctx.fill()
    texte(ctx, "%d %%" % round(100 * p), CX, H - 138, 40, (0.96, 0.98, 0.99))
    texte(ctx, "%d rebonds" % jeu.chocs, CX, H - 92, 30, (0.75, 0.80, 0.82),
          gras=False)


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


def rendre(graine=GRAINE, sortie="rayons_fusion.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "rayons_fusion-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "rayons_fusion.wav")
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
