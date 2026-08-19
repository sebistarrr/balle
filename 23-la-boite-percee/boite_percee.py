"""
La boîte percée — rendu vidéo, format vertical.

Une boîte carrée dont le plancher est percé sur un tiers de sa largeur.
Deux balles au départ, une pesanteur franche. Chaque balle qui trouve le trou en
fait naître deux en haut de la boîte : le remplissage l'emporte vite sur la
fuite. Les fuyardes continuent leur chute sous la boîte et forment une colonne
qui traverse tout l'écran.

Reproduction d'une vidéo existante, refaite de zéro.

Rendu :
    python boite_percee.py                 # écrit boite_percee.mp4 en 1080 x 1920, 60 im/s
    python boite_percee.py --graines       # essaie des tirages et donne ce qu'ils valent

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
APRES = 4.0                 # s de carte de fin


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
X0, X1, Y0, Y1 = 70.0, 1010.0, 430.0, 1430.0
TROU_G, TROU_D = 610.0, 960.0     # la brèche, dans le bord du bas
R_BALLE = 11.0
G = 1500.0                        # px/s² — ici il y a une pesanteur
REBOND = 0.86
V_MAX = 2200.0
PRIME = 2                         # balles gagnées à chaque évasion
N_MAX = 1600
EP = 3.0
DT = 1 / 240
T_LIMITE = 60.0

GRAINE = 0


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        #  Tableaux parallèles plutôt qu'une liste d'objets : à mille six cents
        #  balles, Python paierait cher chaque attribut.
        self.x = np.array([X0 + 180.0, X1 - 180.0])
        self.y = np.array([Y0 + 120.0, Y0 + 200.0])
        self.vx = self.rng.uniform(-350, 350, 2)
        self.vy = self.rng.uniform(-200, 200, 2)
        self.h = self.rng.uniform(0, 360, 2)
        self.dx = np.zeros(0); self.dy = np.zeros(0)
        self.dvx = np.zeros(0); self.dvy = np.zeros(0); self.dh = np.zeros(0)
        self.t = 0.0
        self.fini = None
        self.evasions = 0
        self.notes = []

    def bilan(self):
        return "%d balles, %d évasions" % (len(self.x), self.evasions)

    def pas(self):
        if self.fini is not None:
            self.t += DT
            return
        self.t += DT

        self.vy += G * DT
        self.x += self.vx * DT
        self.y += self.vy * DT
        s = np.hypot(self.vx, self.vy)
        trop = s > V_MAX
        if trop.any():
            self.vx[trop] *= V_MAX / s[trop]
            self.vy[trop] *= V_MAX / s[trop]

        k = self.x < X0 + EP + R_BALLE
        self.x[k] = X0 + EP + R_BALLE; self.vx[k] = np.abs(self.vx[k]) * REBOND
        k = self.x > X1 - EP - R_BALLE
        self.x[k] = X1 - EP - R_BALLE; self.vx[k] = -np.abs(self.vx[k]) * REBOND
        k = self.y < Y0 + EP + R_BALLE
        self.y[k] = Y0 + EP + R_BALLE; self.vy[k] = np.abs(self.vy[k]) * REBOND

        #  Le sol n'existe qu'en dehors de la brèche.
        sol = ((self.y > Y1 - EP - R_BALLE)
               & ~((self.x > TROU_G) & (self.x < TROU_D)))
        k = np.flatnonzero(sol)
        if k.size:
            self.y[k] = Y1 - EP - R_BALLE
            self.vy[k] = -np.abs(self.vy[k]) * REBOND
            #  Une pincée de hasard à chaque contact. Un plancher parfaitement
            #  horizontal range les balles en couches immobiles, et plus rien ne
            #  se dirige vers le trou : le tas se fige et la partie s'arrête.
            self.vx[k] += self.rng.uniform(-60, 60, k.size)
            mou = np.abs(self.vy[k]) < 260
            self.vy[k[mou]] = -260
            if self.x.size < 300 and len(self.notes) < 4000:
                for j in k[:2]:
                    self.notes.append((self.t, int(self.h[j]) % 12, 0.09,
                                       float((self.x[j] - W / 2) / (W / 2))))

        # --- les sorties ---------------------------------------------------
        sorties = np.flatnonzero(self.y > Y1 + 60)
        if sorties.size:
            self.dx = np.concatenate([self.dx, self.x[sorties]])
            self.dy = np.concatenate([self.dy, self.y[sorties]])
            self.dvx = np.concatenate([self.dvx, self.vx[sorties]])
            self.dvy = np.concatenate([self.dvy, self.vy[sorties]])
            self.dh = np.concatenate([self.dh, self.h[sorties]])
            self.evasions += sorties.size
            if len(self.notes) < 4000:
                self.notes.append((self.t, 24, 0.09, 0.0))
            garde = np.setdiff1d(np.arange(self.x.size), sorties)
            self.x, self.y = self.x[garde], self.y[garde]
            self.vx, self.vy = self.vx[garde], self.vy[garde]
            self.h = self.h[garde]
            m = sorties.size * PRIME
            if self.x.size + m <= N_MAX:
                self.x = np.concatenate(
                    [self.x, self.rng.uniform(X0 + 60, X1 - 60, m)])
                self.y = np.concatenate([self.y, np.full(m, Y0 + 60.0)])
                self.vx = np.concatenate([self.vx, self.rng.uniform(-350, 350, m)])
                self.vy = np.concatenate([self.vy, self.rng.uniform(-200, 200, m)])
                self.h = np.concatenate([self.h, self.rng.uniform(0, 360, m)])

        self.chocs()

        if self.dx.size:
            self.dvy += G * DT
            self.dx += self.dvx * DT
            self.dy += self.dvy * DT
            garde = self.dy < H + 80
            self.dx, self.dy = self.dx[garde], self.dy[garde]
            self.dvx, self.dvy = self.dvx[garde], self.dvy[garde]
            self.dh = self.dh[garde]

        if self.x.size >= N_MAX or self.t > T_LIMITE:
            self.fini = self.t

    def chocs(self):
        """Chocs entre balles, par grille : en force brute, mille six cents
        balles feraient plus d'un million de tests par pas de calcul."""
        n = self.x.size
        if n < 2:
            return
        case = 4 * R_BALLE
        cles = ((self.x / case).astype(np.int64) * 100000
                + (self.y / case).astype(np.int64))
        ordre = np.argsort(cles, kind="stable")
        cles_t = cles[ordre]
        debuts = np.flatnonzero(np.r_[True, cles_t[1:] != cles_t[:-1]])
        index = {int(cles_t[d]): p
                 for d, p in zip(debuts, np.split(ordre, debuts[1:]))}
        for cle, p in index.items():
            a, b = cle // 100000, cle % 100000
            for ddx in (0, 1):
                for ddy in ((-1, 0, 1) if ddx else (0, 1)):
                    q = index.get(int((a + ddx) * 100000 + b + ddy))
                    if q is None:
                        continue
                    meme = q is p
                    for i in p:
                        for j in q:
                            if meme and j <= i:
                                continue
                            ex = self.x[j] - self.x[i]
                            ey = self.y[j] - self.y[i]
                            dd = math.hypot(ex, ey)
                            if dd >= 2 * R_BALLE or dd < 1e-9:
                                continue
                            nx, ny = ex / dd, ey / dd
                            corr = (2 * R_BALLE - dd) / 2
                            self.x[i] -= nx * corr; self.y[i] -= ny * corr
                            self.x[j] += nx * corr; self.y[j] += ny * corr
                            vn = ((self.vx[j] - self.vx[i]) * nx
                                  + (self.vy[j] - self.vy[i]) * ny)
                            if vn > 0:
                                continue
                            pp = 0.92 * vn
                            self.vx[i] += pp * nx; self.vy[i] += pp * ny
                            self.vx[j] -= pp * nx; self.vy[j] -= pp * ny


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def troupeau(ctx, x, y, h):
    """Les balles, par lots d'une même teinte : changer la source de
    remplissage entre chaque coûterait plus cher que le tracé."""
    if x.size == 0:
        return
    lots = (h / 12).astype(np.int32)
    for t in np.unique(lots):
        k = np.flatnonzero(lots == t)
        ctx.new_path()
        for i in k:
            ctx.move_to(x[i] + R_BALLE, y[i])
            ctx.arc(x[i], y[i], R_BALLE, 0, TAU)
        ctx.set_source_rgb(*teinte(t * 12 + 6, 0.76, 0.68))
        ctx.fill_preserve()
        ctx.set_source_rgb(*teinte(t * 12 + 6, 0.80, 0.28))
        ctx.set_line_width(2.5)
        ctx.stroke()


def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(0.016, 0.024, 0.039)
    ctx.paint()

    ctx.set_source_rgb(0.949, 0.965, 0.973)
    ctx.set_line_width(2 * EP)
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    ctx.new_path()
    ctx.move_to(X0, Y1); ctx.line_to(X0, Y0)
    ctx.line_to(X1, Y0); ctx.line_to(X1, Y1)
    ctx.move_to(X0, Y1); ctx.line_to(TROU_G, Y1)
    ctx.move_to(TROU_D, Y1); ctx.line_to(X1, Y1)
    ctx.stroke()

    troupeau(ctx, jeu.dx, jeu.dy, jeu.dh)
    troupeau(ctx, jeu.x, jeu.y, jeu.h)

    texte(ctx, "+2 balles à chaque évasion", W / 2, 96, 44, (0.92, 0.96, 0.97))
    texte(ctx, "Balles : %d" % jeu.x.size, W / 2, Y0 - 46, 40,
          (0.95, 0.965, 0.973))
    texte(ctx, "%d évasions" % jeu.evasions, W / 2, H - 70, 30,
          (0.59, 0.67, 0.71), gras=False)

    if jeu.fini is not None:
        v = min(1.0, (jeu.t - jeu.fini) / 0.4)
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.72 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "%d" % jeu.x.size, W / 2, H / 2 + 20, 200,
              (0.95, 0.965, 0.973, v), cerne=0)
        texte(ctx, "balles dans la boîte", W / 2, H / 2 + 100, 44,
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


def rendre(graine=GRAINE, sortie="boite_percee.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "boite_percee-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "boite_percee.wav")
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
