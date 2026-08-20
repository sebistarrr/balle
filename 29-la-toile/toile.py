"""
La toile — rendu vidéo, format vertical.

Deux balles dans un cercle, sans pesanteur. Chaque rebond sur le bord y
plante un point d'attache, et un fil relie pour toujours la balle à chacun de
ses points. Rien ne se coupe, rien ne s'efface : les deux gerbes s'épaississent
jusqu'à tisser le disque entier. Celle qui a planté le plus de points l'emporte.

Reproduction d'une vidéo existante, refaite de zéro.

Rendu :
    python toile.py                 # écrit toile.mp4 en 1080 x 1920, 60 im/s
    python toile.py --graines       # essaie des tirages et donne ce qu'ils valent

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
APRES = 3.5                 # s de carte de fin


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
CX, CY, RC = 540.0, 975.0, 440.0
EP_BORD = 2.5
R = 26.0
V = 700.0
DUREE = 62.0
MAX_FILS = 190

NOMS = ("ORANGE", "VIOLET")
TEINTES = (34.0, 285.0)

DT = 1 / 240
GRAINE = 0


class Balle:
    def __init__(self, i, x, y, cap):
        self.i = i
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(cap) * V, math.sin(cap) * V
        self.fils = []
        self.eclat = 0.0


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        a0 = self.rng.uniform(0, TAU)
        self.b = []
        for i in range(2):
            a = a0 + i * math.pi
            self.b.append(Balle(i, CX + math.cos(a) * RC * 0.45,
                                CY + math.sin(a) * RC * 0.45,
                                self.rng.uniform(0, TAU)))
        self.ondes = []
        self.t = 0.0
        self.fini = None
        self.vainqueur = -1
        self.notes = []

    def bilan(self):
        return "%d fils contre %d" % (len(self.b[0].fils), len(self.b[1].fils))

    def bord(self, b):
        dx, dy = b.x - CX, b.y - CY
        d = math.hypot(dx, dy)
        if d <= RC - EP_BORD - R:
            return
        nx, ny = dx / d, dy / d
        b.x, b.y = CX + nx * (RC - EP_BORD - R), CY + ny * (RC - EP_BORD - R)
        p = 2 * (b.vx * nx + b.vy * ny)
        b.vx -= p * nx
        b.vy -= p * ny
        #  Une pincée de hasard sur la sortie. Sans elle une balle finit par
        #  tomber sur une corde périodique — un triangle, une étoile à cinq
        #  branches — et repasse indéfiniment par les mêmes points : la toile
        #  cesse alors de s'épaissir, ce qui est tout le sujet de l'animation.
        s = math.hypot(b.vx, b.vy)
        c = math.atan2(b.vy, b.vx) + self.rng.uniform(-0.045, 0.045)
        b.vx, b.vy = math.cos(c) * s, math.sin(c) * s

        if len(b.fils) < MAX_FILS:
            b.fils.append(math.atan2(ny, nx))
        b.eclat = 0.3
        self.ondes.append({"x": b.x, "y": b.y, "h": TEINTES[b.i], "vie": 0.5})
        if len(self.notes) < 3000:
            self.notes.append((self.t, (len(b.fils) % 6) * 2 + (7 if b.i else 0),
                               0.10, (b.x - W / 2) / (W / 2)))

    def entre_elles(self):
        a, b = self.b
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

    def pas(self):
        self.t += DT
        if self.fini is not None:
            return
        #  L'ordre de mise à jour est tiré à pile ou face à chaque pas. Avec un
        #  ordre fixe, la balle jouée en premier gagnait 21 parties sur 30 : la
        #  partie se jouant à quelques fils près sur une durée fixe, le moindre
        #  avantage systématique décide presque toutes les parties.
        deux = self.b if self.rng.random() < 0.5 else self.b[::-1]
        for b in deux:
            b.eclat = max(0.0, b.eclat - DT)
            b.x += b.vx * DT
            b.y += b.vy * DT
            self.bord(b)
        self.entre_elles()

        for o in self.ondes:
            o["vie"] -= DT
        self.ondes = [o for o in self.ondes if o["vie"] > 0]

        if self.t >= DUREE:
            self.fini = self.t
            na, nb = len(self.b[0].fils), len(self.b[1].fils)
            self.vainqueur = (int(self.rng.random() < 0.5) if na == nb
                              else (0 if na > nb else 1))


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    #  Les deux gerbes en fusion additive : c'est ce qui fait qu'à cent vingt
    #  fils la toile s'éclaire au lieu de virer à la bouillie grise, et que les
    #  croisements se voient. Le groupe sert à cantonner l'opérateur.
    ctx.push_group()
    ctx.set_operator(cairo.OPERATOR_ADD)
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    for b in jeu.b:
        ctx.new_path()
        for a in b.fils:
            ctx.move_to(b.x, b.y)
            ctx.line_to(CX + math.cos(a) * RC, CY + math.sin(a) * RC)
        ctx.set_source_rgba(*teinte(TEINTES[b.i], 0.88, 0.42), 0.85)
        ctx.set_line_width(1.9)
        ctx.stroke()

    for o in jeu.ondes:
        v = o["vie"] / 0.5
        ctx.set_source_rgba(*teinte(o["h"], 1.0, 0.70), 0.55 * v)
        ctx.set_line_width(2.5 * v)
        ctx.new_path()
        ctx.arc(o["x"], o["y"], R + 46 * (1 - v), 0, TAU)
        ctx.stroke()

    for b in jeu.b:
        if b.eclat <= 0:
            continue
        deg = cairo.RadialGradient(b.x, b.y, R * 0.3, b.x, b.y, R * 3)
        r, v, bl = teinte(TEINTES[b.i], 1.0, 0.60)
        deg.add_color_stop_rgba(0, r, v, bl, 0.55 * (b.eclat / 0.3))
        deg.add_color_stop_rgba(1, r, v, bl, 0.0)
        ctx.set_source(deg)
        ctx.new_path()
        ctx.arc(b.x, b.y, R * 3, 0, TAU)
        ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint()

    ctx.set_source_rgba(1, 1, 1, 0.92)
    ctx.set_line_width(EP_BORD * 2)
    ctx.new_path()
    ctx.arc(CX, CY, RC, 0, TAU)
    ctx.stroke()

    for b in jeu.b:
        ctx.set_source_rgb(*teinte(TEINTES[b.i], 0.95, 0.55))
        ctx.new_path()
        ctx.arc(b.x, b.y, R, 0, TAU)
        ctx.fill()

    #  Le décompte en haut, dans la bande vide du cadre : entre les deux
    #  compteurs il se retrouvait coincé et illisible.
    texte(ctx, "%d s" % max(0, math.ceil(DUREE - jeu.t)), W / 2, 300, 44,
          (0.82, 0.86, 0.88), gras=False, cerne=0)

    for b in jeu.b:
        x = W / 2 + (230 if b.i else -230)
        c = teinte(TEINTES[b.i], 0.92, 0.60)
        texte(ctx, NOMS[b.i], x, H - 168, 40, c, cerne=0)
        texte(ctx, str(len(b.fils)), x, H - 96, 68, c, cerne=0)

    if jeu.fini is not None:
        v = min(1.0, (jeu.t - jeu.fini) / 0.4)
        g = jeu.vainqueur
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.68 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "vainqueur", W / 2, H / 2 - 120, 44, (0.78, 0.84, 0.86, v),
              gras=False, cerne=0)
        texte(ctx, NOMS[g], W / 2, H / 2 + 10, 118,
              teinte(TEINTES[g], 1.0, 0.62) + (v,), cerne=0)
        texte(ctx, "%d contre %d" % (len(jeu.b[g].fils), len(jeu.b[1 - g].fils)),
              W / 2, H / 2 + 90, 40, (0.63, 0.71, 0.75, v), gras=False, cerne=0)


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


def rendre(graine=GRAINE, sortie="toile.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "toile-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "toile.wav")
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
