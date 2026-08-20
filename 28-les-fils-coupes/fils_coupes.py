"""
Les fils coupés — rendu vidéo, format vertical.

Cinq balles dans un cercle. Chacune tient une gerbe de fils tendus entre
elle et des points fixes du bord : la gerbe suit la balle, les points ne bougent
pas. Toucher le bord en tend un de plus, traverser le fil d'une autre le coupe.
À court de fils, on est éliminée ; la dernière l'emporte.

Reproduction d'une vidéo existante, refaite de zéro.

Rendu :
    python fils_coupes.py                 # écrit fils_coupes.mp4 en 1080 x 1920, 60 im/s
    python fils_coupes.py --graines       # essaie des tirages et donne ce qu'ils valent

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
CX, CY, RC = 540.0, 975.0, 498.0
EP_BORD = 7.0

R = 34.0
V = 900.0
N0 = 14
OUVERTURE = 0.9
MAX_FILS = 160

#  Un fil n'est coupé que loin de son point d'attache : au ras de la balle qui
#  le tient, toutes ses gerbes passent à portée d'un adversaire de passage et
#  disparaîtraient d'un coup.
GARDE = 3.2 * R

#  Un passage = une coupe. La gerbe de l'adversaire balaie l'écran en même
#  temps que lui : sans ce délai par paire, elle vient se présenter fil après
#  fil sous la balle qui la coupe, et le saignement est continu au lieu d'être
#  un coup de faux.
PASSE_REPOS = 1.3

#  Un rebond ne plante pas un point d'attache mais toute une grappe. Compté sur
#  la vidéo, image par image, en dénombrant les paquets de couleur sur le bord :
#  le vert passe de 15 points à 33 en une seconde, le jaune de 18 à 37.
#
#  La grappe maigrit ensuite, et c'est ce qui fait qu'il y a une fin. Mesuré sur
#  quarante secondes : chaque balle gagnait 500 fils et en perdait 450. Or la
#  perte est proportionnelle à la taille de la gerbe — plus on a de fils, plus
#  on en présente à couper — tandis que le gain est fixe. Chaque balle converge
#  donc vers le même équilibre, autour de cent fils, et personne ne descend
#  jamais à zéro : aucune partie sur quarante ne se terminait en cinq minutes.
#  Le plancher est zéro et non un : à deux, il ne reste que deux gerbes à
#  traverser, les coupes se raréfient et l'équilibre remonte à quarante.
GAIN0 = 12
GAIN_PENTE = 0.26
GAIN_ETALE = 0.16

NOMS = ("VERT", "VIOLET", "ROSE", "JAUNE", "BLEU")
TEINTES = (125.0, 268.0, 335.0, 58.0, 195.0)

DT = 1 / 240
GRAINE = 2          # 54,7 s, le vert l'emporte de justesse — comme la vidéo


class Balle:
    def __init__(self, i, a, cap):
        self.i = i
        self.x = CX + math.cos(a) * RC * 0.55
        self.y = CY + math.sin(a) * RC * 0.55
        self.vx, self.vy = math.cos(cap) * V, math.sin(cap) * V
        #  Départ en étoile, comme la première image de la vidéo : chaque balle
        #  à mi-rayon, sa gerbe ouverte vers le bord derrière elle.
        self.fils = [a + (k / (N0 - 1) - 0.5) * 2 * OUVERTURE for k in range(N0)]
        self.vivante = True
        self.mort = 0.0
        self.eclat = 0.0
        self.repos = [0.0] * 5


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        a0 = self.rng.uniform(0, TAU)
        self.b = [Balle(i, a0 + i * TAU / 5, self.rng.uniform(0, TAU))
                  for i in range(5)]
        self.coupes = []
        self.t = 0.0
        self.fini = None
        self.vainqueur = -1
        self.notes = []

    def bilan(self):
        if self.vainqueur < 0:
            return "aucune survivante"
        return "%s l'emporte, %d fils tenus" % (
            NOMS[self.vainqueur], len(self.b[self.vainqueur].fils))

    def vivantes(self):
        return [b for b in self.b if b.vivante]

    def gain(self):
        return max(0, round(GAIN0 - self.t * GAIN_PENTE))

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
        #  Les points d'attache sont sur le bord, pas sur la balle : c'est ce
        #  qui fait que les fils touchent le cercle et non un anneau intérieur.
        #  Et il en naît toute une grappe d'un coup.
        a0 = math.atan2(ny, nx)
        g = self.gain()
        for k in range(g):
            if len(b.fils) >= MAX_FILS:
                break
            b.fils.append(a0 + (0 if g == 1 else
                                (k / (g - 1) - 0.5) * 2 * GAIN_ETALE))
        b.eclat = 0.22
        if len(self.notes) < 3000:
            self.notes.append((self.t, (len(b.fils) % 5) * 2 + b.i, 0.11,
                               (b.x - W / 2) / (W / 2)))

    def couper(self, tueur, cible):
        """Traverser une gerbe la tranche EN ENTIER : tous les fils que la
        balle coupe à cet instant tombent d'un coup. Mesuré sur la vidéo : le
        jaune perd quarante-quatre fils en une seconde, le rose treize. Seul le
        début du fil est épargné — au ras de la balle qui le tient, toute sa
        gerbe passe à portée d'un adversaire de passage."""
        if tueur.repos[cible.i] > 0:
            return
        ax, ay = cible.x, cible.y
        n = 0
        for k in range(len(cible.fils) - 1, -1, -1):
            bx = CX + math.cos(cible.fils[k]) * RC
            by = CY + math.sin(cible.fils[k]) * RC
            ex, ey = bx - ax, by - ay
            L = math.hypot(ex, ey)
            if L < 1e-6:
                continue
            t = ((tueur.x - ax) * ex + (tueur.y - ay) * ey) / (L * L)
            if t * L < GARDE:
                continue
            t = min(1.0, t)
            px, py = ax + ex * t, ay + ey * t
            if math.hypot(tueur.x - px, tueur.y - py) > R:
                continue
            self.coupes.append({"x": px, "y": py, "h": TEINTES[cible.i],
                                "vie": 0.45})
            cible.fils.pop(k)
            n += 1
        if not n:
            return
        tueur.repos[cible.i] = PASSE_REPOS
        if not cible.fils:
            cible.vivante = False
            cible.mort = self.t

    def entre_elles(self, a, b):
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

        #  L'ordre de mise à jour est retiré à chaque pas. Sur un plateau
        #  symétrique, un ordre fixe devient un avantage fixe : c'est ce qui
        #  avait faussé les statistiques de la 19, mesures à l'appui.
        ordre = list(self.rng.permutation(5))

        for i in ordre:
            b = self.b[i]
            if not b.vivante:
                continue
            b.eclat = max(0.0, b.eclat - DT)
            for k in range(5):
                b.repos[k] = max(0.0, b.repos[k] - DT)
            b.x += b.vx * DT
            b.y += b.vy * DT
            self.bord(b)

        v = self.vivantes()
        for a in range(len(v)):
            for c in range(a + 1, len(v)):
                self.entre_elles(v[a], v[c])

        for i in ordre:
            t = self.b[i]
            if not t.vivante:
                continue
            for c in self.b:
                if c is t or not c.vivante:
                    continue
                self.couper(t, c)

        for c in self.coupes:
            c["vie"] -= DT
        self.coupes = [c for c in self.coupes if c["vie"] > 0]

        reste = self.vivantes()
        if len(reste) <= 1:
            self.fini = self.t
            self.vainqueur = reste[0].i if reste else -1


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    #  Les gerbes d'abord, le cercle par-dessus : dans la vidéo les fils
    #  s'arrêtent net sur le trait blanc, ils ne le débordent pas.
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    for b in jeu.b:
        if not b.vivante:
            continue
        ctx.new_path()
        for a in b.fils:
            ctx.move_to(b.x, b.y)
            ctx.line_to(CX + math.cos(a) * RC, CY + math.sin(a) * RC)
        ctx.set_source_rgb(*teinte(TEINTES[b.i], 0.92, 0.55))
        ctx.set_line_width(2.6)
        ctx.stroke()

    #  Les coupes : une croix qui s'ouvre là où un fil vient d'être tranché.
    ctx.push_group()
    ctx.set_operator(cairo.OPERATOR_ADD)
    for c in jeu.coupes:
        v = c["vie"] / 0.45
        ctx.set_source_rgba(*teinte(c["h"], 1.0, 0.78), v)
        ctx.set_line_width(3 * v)
        t = 26 * (1 - v) + 8
        ctx.new_path()
        ctx.move_to(c["x"] - t, c["y"] - t); ctx.line_to(c["x"] + t, c["y"] + t)
        ctx.move_to(c["x"] - t, c["y"] + t); ctx.line_to(c["x"] + t, c["y"] - t)
        ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint()

    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(EP_BORD * 2)
    ctx.new_path()
    ctx.arc(CX, CY, RC, 0, TAU)
    ctx.stroke()

    #  Les points d'attache par-dessus le trait blanc, comme dans la vidéo : le
    #  bord y est piqueté de couleurs. Dessinés avant, ils passaient dessous et
    #  on ne les voyait pas.
    for b in jeu.b:
        if not b.vivante:
            continue
        ctx.set_source_rgb(*teinte(TEINTES[b.i], 1.0, 0.70))
        ctx.new_path()
        for a in b.fils:
            ctx.rectangle(CX + math.cos(a) * RC - 3, CY + math.sin(a) * RC - 3,
                          6, 6)
        ctx.fill()

    for b in jeu.b:
        if not b.vivante:
            continue
        if b.eclat > 0:
            ctx.push_group()
            ctx.set_operator(cairo.OPERATOR_ADD)
            deg = cairo.RadialGradient(b.x, b.y, R * 0.4, b.x, b.y, R * 2.6)
            r, v, bl = teinte(TEINTES[b.i], 1.0, 0.60)
            deg.add_color_stop_rgba(0, r, v, bl, 0.5 * (b.eclat / 0.22))
            deg.add_color_stop_rgba(1, r, v, bl, 0.0)
            ctx.set_source(deg)
            ctx.new_path()
            ctx.arc(b.x, b.y, R * 2.6, 0, TAU)
            ctx.fill()
            ctx.pop_group_to_source()
            ctx.paint()
        ctx.set_source_rgb(*teinte(TEINTES[b.i], 0.95, 0.52))
        ctx.new_path()
        ctx.arc(b.x, b.y, R, 0, TAU)
        ctx.fill_preserve()
        ctx.set_source_rgb(*teinte(TEINTES[b.i], 1.0, 0.82))
        ctx.set_line_width(3)
        ctx.stroke()

    #  Le compte des fils, en bas : c'est le seul chiffre du cadre, et c'est
    #  celui qui dit qui est en train de perdre.
    larg = W / 5
    for b in jeu.b:
        x = larg * (b.i + 0.5)
        if b.vivante:
            texte(ctx, NOMS[b.i], x, H - 118, 26,
                  teinte(TEINTES[b.i], 0.90, 0.62), cerne=0)
            texte(ctx, str(len(b.fils)), x, H - 62, 52,
                  teinte(TEINTES[b.i], 1.0, 0.66), cerne=0)
        else:
            texte(ctx, NOMS[b.i], x, H - 118, 26, (0.23, 0.23, 0.23), cerne=0)
            texte(ctx, "—", x, H - 62, 52, (0.17, 0.17, 0.17), cerne=0)

    if jeu.fini is not None and jeu.vainqueur >= 0:
        v = min(1.0, (jeu.t - jeu.fini) / 0.4)
        g = jeu.vainqueur
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.66 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "vainqueur", W / 2, H / 2 - 120, 44, (0.78, 0.84, 0.86, v),
              gras=False, cerne=0)
        texte(ctx, NOMS[g], W / 2, H / 2 + 10, 118,
              teinte(TEINTES[g], 1.0, 0.64) + (v,), cerne=0)
        texte(ctx, "%d fils tenus" % len(jeu.b[g].fils), W / 2, H / 2 + 90, 40,
              (0.63, 0.71, 0.75, v), gras=False, cerne=0)


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


def rendre(graine=GRAINE, sortie="fils_coupes.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "fils_coupes-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "fils_coupes.wav")
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
