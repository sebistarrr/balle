"""
L'anneau percé — rendu vidéo, format vertical.

Un anneau percé de deux trouées, qui tourne lentement. Une balle à
l'intérieur, sans pesanteur. Chaque évasion en fait naître trois au centre : la
population double toutes les quelques secondes. Les fuyardes ne sont pas
effacées — elles continuent tout droit, et comme l'anneau tourne, elles
s'ordonnent d'elles-mêmes en spirales.

Reproduction d'une vidéo existante, refaite de zéro.

Rendu :
    python anneau_perce.py                 # écrit anneau_perce.mp4 en 1080 x 1920, 60 im/s
    python anneau_perce.py --graines       # essaie des tirages et donne ce qu'ils valent

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
CX, CY, R = 540.0, 1010.0, 395.0
R_BALLE = 9.0
V0 = 700.0                  # px/s, constante : pas de pesanteur
OUVERTURES = 2
OUVERTURE = 0.30            # rad — largeur d'une trouée
OMEGA = 0.60                # rad/s — l'anneau tourne
EP = 6.0
PRIME = 3                   # balles gagnées à chaque évasion
EVASION = R + 40
N_MAX = 6000
DT = 1 / 240
T_LIMITE = 60.0

GRAINE = 0


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        a = self.rng.uniform(0, TAU)
        #  Positions, vitesses et teintes en tableaux parallèles : à six mille
        #  balles, une liste d'objets Python coûterait dix fois plus cher.
        self.x = np.array([CX + 120.0])
        self.y = np.array([CY])
        self.vx = np.array([math.cos(a) * V0])
        self.vy = np.array([math.sin(a) * V0])
        self.h = self.rng.uniform(0, 360, 1)
        #  Les fuyardes, gardées tant qu'elles sont dans le cadre : ce sont
        #  elles qui dessinent les spirales.
        self.dx = np.zeros(0); self.dy = np.zeros(0)
        self.dvx = np.zeros(0); self.dvy = np.zeros(0); self.dh = np.zeros(0)
        self.phase = self.rng.uniform(0, TAU)
        self.t = 0.0
        self.fini = None
        self.evasions = 0
        self.notes = []

    def bilan(self):
        return "%d balles, %d évasions" % (len(self.x), self.evasions)

    def troue(self, angle):
        """Vrai si cet angle tombe dans une trouée de l'anneau."""
        pas = TAU / OUVERTURES
        a = np.mod(angle - self.phase, pas)
        return (a < OUVERTURE / 2) | (a > pas - OUVERTURE / 2)

    def pas(self):
        if self.fini is not None:
            self.t += DT
            return
        self.t += DT
        self.phase += OMEGA * DT

        self.x += self.vx * DT
        self.y += self.vy * DT
        dx, dy = self.x - CX, self.y - CY
        d = np.hypot(dx, dy)
        d[d < 1e-9] = 1e-9

        # --- les sorties ---------------------------------------------------
        sorties = np.flatnonzero(d > EVASION)
        if sorties.size:
            self.dx = np.concatenate([self.dx, self.x[sorties]])
            self.dy = np.concatenate([self.dy, self.y[sorties]])
            self.dvx = np.concatenate([self.dvx, self.vx[sorties]])
            self.dvy = np.concatenate([self.dvy, self.vy[sorties]])
            self.dh = np.concatenate([self.dh, self.h[sorties]])
            self.evasions += sorties.size
            if len(self.notes) < 4000:
                for k in sorties[:2]:
                    self.notes.append((self.t, 24, 0.10,
                                       float((self.x[k] - CX) / R)))
            garde = np.setdiff1d(np.arange(self.x.size), sorties)
            self.x, self.y = self.x[garde], self.y[garde]
            self.vx, self.vy = self.vx[garde], self.vy[garde]
            self.h = self.h[garde]
            if self.x.size + sorties.size * PRIME <= N_MAX:
                #  Les nouvelles naissent au centre, dispersées sur un petit
                #  disque : toutes au même point, elles se repoussent d'un coup
                #  et partent toutes dans la même direction.
                m = sorties.size * PRIME
                aa = self.rng.uniform(0, TAU, m)
                rr = self.rng.uniform(0, 30, m)
                cc = self.rng.uniform(0, TAU, m)
                self.x = np.concatenate([self.x, CX + np.cos(aa) * rr])
                self.y = np.concatenate([self.y, CY + np.sin(aa) * rr])
                self.vx = np.concatenate([self.vx, np.cos(cc) * V0])
                self.vy = np.concatenate([self.vy, np.sin(cc) * V0])
                self.h = np.concatenate([self.h, self.rng.uniform(0, 360, m)])
            dx, dy = self.x - CX, self.y - CY
            d = np.hypot(dx, dy)
            d[d < 1e-9] = 1e-9

        # --- l'anneau ------------------------------------------------------
        mini, maxi = R - EP - R_BALLE, R + EP + R_BALLE
        pres = (d > mini) & (d < maxi) & ~self.troue(np.arctan2(dy, dx))
        k = np.flatnonzero(pres)
        if k.size:
            nx, ny = dx[k] / d[k], dy[k] / d[k]
            vers = self.vx[k] * nx + self.vy[k] * ny
            cible = np.where(vers > 0, mini, maxi)
            self.x[k] = CX + nx * cible
            self.y[k] = CY + ny * cible
            p = 2 * vers
            self.vx[k] -= p * nx
            self.vy[k] -= p * ny
            s = np.hypot(self.vx[k], self.vy[k])
            s[s < 1e-9] = 1e-9
            self.vx[k] *= V0 / s
            self.vy[k] *= V0 / s
            if self.x.size < 400 and len(self.notes) < 4000:
                for j in k[:2]:
                    self.notes.append((self.t, 12 + int(self.h[j]) % 12, 0.09,
                                       float((self.x[j] - CX) / R)))

        # --- chocs entre balles, par grille --------------------------------
        #  À six mille balles, comparer toutes les paires ferait dix-huit
        #  millions de tests par pas. On range les balles dans des cases de
        #  quatre rayons et l'on ne compare que les voisines.
        self.chocs()

        # --- les fuyardes ---------------------------------------------------
        if self.dx.size:
            self.dx += self.dvx * DT
            self.dy += self.dvy * DT
            garde = ((self.dx > -60) & (self.dx < W + 60)
                     & (self.dy > -60) & (self.dy < H + 60))
            self.dx, self.dy = self.dx[garde], self.dy[garde]
            self.dvx, self.dvy = self.dvx[garde], self.dvy[garde]
            self.dh = self.dh[garde]

        if self.x.size >= N_MAX or self.t > T_LIMITE:
            self.fini = self.t

    def chocs(self):
        n = self.x.size
        if n < 2:
            return
        case = 4 * R_BALLE
        cx = (self.x / case).astype(np.int32)
        cy = (self.y / case).astype(np.int32)
        cles = cx.astype(np.int64) * 100000 + cy
        ordre = np.argsort(cles, kind="stable")
        cles_t = cles[ordre]
        debuts = np.flatnonzero(np.r_[True, cles_t[1:] != cles_t[:-1]])
        paquets = np.split(ordre, debuts[1:])
        index = {int(cles_t[d]): p for d, p in zip(debuts, paquets)}
        for cle, p in index.items():
            a, b = divmod(cle + 0, 100000)
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
                            self.vx[i] += vn * nx; self.vy[i] += vn * ny
                            self.vx[j] -= vn * nx; self.vy[j] -= vn * ny
                            for m in (i, j):
                                s = math.hypot(self.vx[m], self.vy[m]) or 1e-9
                                self.vx[m] *= V0 / s
                                self.vy[m] *= V0 / s


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def troupeau(ctx, x, y, h):
    """Les balles, par lots d'une même teinte.

    À six mille disques, changer la source de remplissage entre chaque coûte
    plus cher que le tracé lui-même : on regroupe par tranche de douze degrés,
    et l'on remplit trente chemins au lieu de six mille.
    """
    if x.size == 0:
        return
    lots = (h / 12).astype(np.int32)
    for t in np.unique(lots):
        k = np.flatnonzero(lots == t)
        ctx.new_path()
        for i in k:
            ctx.move_to(x[i] + R_BALLE, y[i])
            ctx.arc(x[i], y[i], R_BALLE, 0, TAU)
        ctx.set_source_rgb(*teinte(t * 12 + 6, 0.78, 0.62))
        ctx.fill_preserve()
        ctx.set_source_rgb(*teinte(t * 12 + 6, 0.80, 0.26))
        ctx.set_line_width(2)
        ctx.stroke()


def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(0.016, 0.024, 0.039)
    ctx.paint()

    #  L'anneau : deux arcs, deux trouées.
    ctx.set_source_rgb(0.949, 0.965, 0.973)
    ctx.set_line_width(2 * EP)
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    ctx.new_path()
    pas = TAU / OUVERTURES
    for k in range(OUVERTURES):
        a0 = jeu.phase + k * pas + OUVERTURE / 2
        a1 = jeu.phase + (k + 1) * pas - OUVERTURE / 2
        ctx.new_sub_path()
        ctx.arc(CX, CY, R, a0, a1)
    ctx.stroke()

    troupeau(ctx, jeu.dx, jeu.dy, jeu.dh)
    troupeau(ctx, jeu.x, jeu.y, jeu.h)

    texte(ctx, "+3 balles à chaque évasion", W / 2, 96, 44, (0.92, 0.96, 0.97))
    texte(ctx, "Balles : %d" % jeu.x.size, W / 2, CY - R - 46, 40,
          (0.95, 0.965, 0.973))
    texte(ctx, "%d évasions" % jeu.evasions, W / 2, H - 96, 30,
          (0.59, 0.67, 0.71), gras=False)

    if jeu.fini is not None:
        v = min(1.0, (jeu.t - jeu.fini) / 0.4)
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.72 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "%d" % jeu.x.size, W / 2, H / 2 + 20, 200,
              (0.95, 0.965, 0.973, v), cerne=0)
        texte(ctx, "balles dans l'anneau", W / 2, H / 2 + 100, 44,
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


def rendre(graine=GRAINE, sortie="anneau_perce.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "anneau_perce-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "anneau_perce.wav")
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
