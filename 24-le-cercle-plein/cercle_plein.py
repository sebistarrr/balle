"""
Le cercle plein — rendu vidéo, format vertical.

Une balle sans pesanteur dans un cercle hérissé de trois pointes qui
tournent. Elle grossit à chaque rebond ; sur une pointe, elle éclate en cent
cinquante billes qui restent dans le cercle. Une nouvelle balle repart, d'une
autre couleur, et le cercle se remplit.

Repris de la balle et les pointes (5), avec des pointes quatre fois plus larges
— 8,5 % du bord contre 2,3 % — et rien qui s'efface : le but est de remplir.

Rendu :
    python cercle_plein.py                 # écrit cercle_plein.mp4 en 1080 x 1920, 60 im/s
    python cercle_plein.py --graines       # essaie des tirages et donne ce qu'ils valent

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
APRES = 4.5                 # s de carte de fin


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
CX, CY, R = 540.0, 976.0, 514.0
V0 = 1000.0                 # vitesse de la balle, px/s
DT = 1 / 480
R0 = 24.0                   # rayon de la balle au départ
PAS_RAYON = 11.0            # gain par rebond
R_MAX = 112.0               # au-delà, elle éclate

#  Des pointes nettement plus grandes qu'à la 5 : elles y couvraient 2,3 % du
#  bord, elles en couvrent ici 8,5 %. La balle en trouve donc une bien plus
#  vite, éclate bien plus souvent, et c'est exactement ce qu'on veut — chaque
#  éclatement est une poignée de billes de plus dans le cercle.
N_POINTES = 3
DEMI_POINTE = 10.2 * math.pi / 180
HAUT_POINTE = 96.0
ROTATION = -52 * math.pi / 180      # rad/s

N_ECLATS = 150              # billes libérées par éclatement
MAX_ECLATS = 4200
AIRE_CERCLE = math.pi * R * R

#  On n'arrête pas sur une cible, mais sur un palier — la mesure a montré
#  pourquoi : le remplissage monte jusqu'à environ 70 %, puis s'arrête net. La
#  balle, prisonnière du tas, ne peut plus atteindre le bord, donc plus toucher
#  de pointe, donc plus éclater. Ce plafond n'est pas un réglage, c'est la
#  saturation du cercle, et c'est le maximum qu'on cherchait.
PALIER = 9.0                # s sans toucher le bord
REMPLI_VISE = 0.72          # pour l'échelle de la jauge seulement

#  Les billes : mêmes règles qu'à la 5, une horloge deux fois plus lente.
DT_BILLES = 1 / 240
REBOND_BORD = 0.94
REBOND_BILLE = 0.92
FROTTEMENT = 0.99985
CASE = 44.0
MASSE_BALLE = 40.0

#  Graine 2, la plus remplie des huit essayées : 49 s, 58 % du cercle,
#  1950 billes en treize éclatements.
GRAINE = 2

from scipy.spatial import cKDTree


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        self.teinte = 150.0
        self.lancer(0.6)
        self.ex = np.zeros(0); self.ey = np.zeros(0)
        self.evx = np.zeros(0); self.evy = np.zeros(0)
        self.er = np.zeros(0); self.eh = np.zeros(0); self.el = np.zeros(0)
        self.t = 0.0
        self.reste_billes = 0.0
        self.rebonds = 0
        self.eclatements = 0
        self.t_palier = 0.0
        self.fini = None
        self.rempli = 0.0
        self.notes = []

    def bilan(self):
        return "%d %% du cercle, %d billes, %d éclatements" % (
            round(100 * self.taux()), self.ex.size, self.eclatements)

    def taux(self):
        return float(np.sum(math.pi * self.er ** 2) / AIRE_CERCLE)

    def lancer(self, cap):
        self.bx, self.by = CX, CY - R * 0.45
        self.vx, self.vy = math.cos(cap) * V0, math.sin(cap) * V0
        self.r = R0

    def sur_une_pointe(self, angle):
        for i in range(N_POINTES):
            a = ROTATION * self.t + i * TAU / N_POINTES
            d = (angle - a) % TAU
            if d > math.pi:
                d -= TAU
            if abs(d) < DEMI_POINTE:
                return True
        return False

    def eclater(self):
        self.eclatements += 1
        self.t_palier = self.t
        n = N_ECLATS
        a = self.rng.uniform(0, TAU, n)
        v = self.rng.uniform(260, 1160, n)
        #  Elles partent de la surface de la balle, pas de son centre : sur une
        #  balle devenue large, un jet issu d'un point serait un artifice
        #  visible.
        self.ex = np.concatenate([self.ex, self.bx + np.cos(a) * self.r * 0.85])
        self.ey = np.concatenate([self.ey, self.by + np.sin(a) * self.r * 0.85])
        self.evx = np.concatenate([self.evx, np.cos(a) * v])
        self.evy = np.concatenate([self.evy, np.sin(a) * v])
        self.er = np.concatenate([self.er, self.rng.uniform(5, 12, n)])
        #  Chaque bille garde la teinte de la balle éclatée ; seule la clarté
        #  varie un peu, sinon le nuage serait un aplat.
        self.eh = np.concatenate([self.eh, np.full(n, self.teinte)])
        self.el = np.concatenate([self.el, self.rng.uniform(48, 74, n)])
        self.notes.append((self.t, 4, 0.30, (self.bx - CX) / R))
        #  Nouvelle balle au centre, couleur avancée, taille de départ.
        self.teinte = (self.teinte + 47) % 360
        self.lancer(self.rng.uniform(0, TAU))

    def pas(self):
        if self.fini is not None:
            self.t += DT
            return
        self.t += DT
        self.bx += self.vx * DT
        self.by += self.vy * DT

        dx, dy = self.bx - CX, self.by - CY
        d = math.sqrt(dx * dx + dy * dy)
        if d > R - self.r:
            nx, ny = dx / d, dy / d
            if self.sur_une_pointe(math.atan2(-ny, nx)):
                self.eclater()
            else:
                #  On grossit d'abord, on repositionne ensuite : replacée à
                #  l'ancien rayon puis grossie, la balle mordrait encore le bord
                #  et déclencherait un second rebond au pas suivant.
                self.r += PAS_RAYON
                self.bx, self.by = CX + nx * (R - self.r), CY + ny * (R - self.r)
                p = 2 * (self.vx * nx + self.vy * ny)
                self.vx -= p * nx
                self.vy -= p * ny
                s = math.hypot(self.vx, self.vy) or 1e-9
                self.vx *= V0 / s
                self.vy *= V0 / s
                self.rebonds += 1
                self.t_palier = self.t
                if len(self.notes) < 3000:
                    self.notes.append((self.t, (self.rebonds % 5) * 2 + 12,
                                       0.14, (self.bx - CX) / R))
                if self.r >= R_MAX:
                    self.eclater()

        self.reste_billes += DT
        while self.reste_billes >= DT_BILLES:
            self.reste_billes -= DT_BILLES
            self.pas_billes()

        if self.ex.size >= MAX_ECLATS or (self.t > 8 and self.t - self.t_palier > PALIER):
            self.fini = self.t
            self.rempli = self.taux()

    def pas_billes(self):
        h = DT_BILLES
        n = self.ex.size
        if n == 0:
            return
        self.ex += self.evx * h
        self.ey += self.evy * h
        self.evx *= FROTTEMENT
        self.evy *= FROTTEMENT
        #  Plafond de vitesse, même raison : la résolution simultanée peut
        #  injecter de l'énergie quand les chevauchements sont multiples.
        s = np.hypot(self.evx, self.evy)
        trop = s > 2600
        if trop.any():
            self.evx[trop] *= 2600 / s[trop]
            self.evy[trop] *= 2600 / s[trop]

        # --- le bord du cercle ---------------------------------------------
        dx, dy = self.ex - CX, self.ey - CY
        d = np.hypot(dx, dy)
        d[d < 1e-9] = 1e-9
        k = np.flatnonzero(d > R - self.er)
        if k.size:
            nx, ny = dx[k] / d[k], dy[k] / d[k]
            self.ex[k] = CX + nx * (R - self.er[k])
            self.ey[k] = CY + ny * (R - self.er[k])
            p = (1 + REBOND_BORD) * (self.evx[k] * nx + self.evy[k] * ny)
            sort = p > 0
            self.evx[k[sort]] -= (p * nx)[sort]
            self.evy[k[sort]] -= (p * ny)[sort]

        # --- entre billes ---------------------------------------------------
        #  Deux mille billes en force brute feraient deux millions de tests par
        #  pas. Un arbre k-d rend la liste des paires qui se touchent en une
        #  milliseconde, et la résolution se fait ensuite d'un bloc.
        #
        #  Une différence avec la page, qu'il vaut mieux dire : la page résout
        #  les paires l'une après l'autre, ce script les résout toutes ensemble.
        #  Sur un tas de deux mille disques, cela suffit à faire diverger les
        #  deux — le tas n'est pas le même bille par bille. Les réglages, eux,
        #  sont identiques, et le remplissage final tombe au même endroit.
        paires = cKDTree(np.column_stack([self.ex, self.ey])).query_pairs(
            2 * float(self.er.max()), output_type="ndarray")
        if paires.size:
            i, j = paires[:, 0], paires[:, 1]
            mini = self.er[i] + self.er[j]
            #  Trois passes de relaxation sur la même liste de paires. Une seule
            #  passe ne sépare pas un tas dense : les chevauchements persistent,
            #  les billes s'interpénètrent, et la surface occupée dépasse cent
            #  pour cent — mesuré, 121 % au lieu des 70 % de la page. Trois
            #  passes suffisent à retrouver un empilement qui se tient.
            for passe in range(3):
                exd = self.ex[j] - self.ex[i]
                eyd = self.ey[j] - self.ey[i]
                dd = np.hypot(exd, eyd)
                k = (dd < mini) & (dd > 1e-9)
                if not k.any():
                    break
                ii, jj = i[k], j[k]
                nx, ny = exd[k] / dd[k], eyd[k] / dd[k]
                corr = np.minimum((mini[k] - dd[k]) / 2, 4.0)
                np.add.at(self.ex, ii, -nx * corr)
                np.add.at(self.ey, ii, -ny * corr)
                np.add.at(self.ex, jj, nx * corr)
                np.add.at(self.ey, jj, ny * corr)
                if passe:
                    continue
                #  L'impulsion ne s'applique qu'une fois : les passes suivantes
                #  ne font que défaire les chevauchements.
                vn = ((self.evx[jj] - self.evx[ii]) * nx
                      + (self.evy[jj] - self.evy[ii]) * ny)
                m = vn < 0
                pp = (1 + REBOND_BILLE) / 2 * vn[m]
                np.add.at(self.evx, ii[m], pp * nx[m])
                np.add.at(self.evy, ii[m], pp * ny[m])
                np.add.at(self.evx, jj[m], -pp * nx[m])
                np.add.at(self.evy, jj[m], -pp * ny[m])

        # --- la grosse balle et les billes ----------------------------------
        #  La balle pèse quarante billes : chaque contact projette la bille et ne
        #  la dévie qu'un peu. Mais elle est déviée — et c'est capital, c'est ce
        #  qui finit par l'emprisonner quand l'anneau de billes s'épaissit. Sans
        #  cette réaction, elle traverse le tas comme si de rien n'était,
        #  continue d'atteindre le bord et d'éclater : mesuré, le cercle montait
        #  à 121 % de sa surface, c'est-à-dire à un tas de billes qui se
        #  traversent.
        dx, dy = self.ex - self.bx, self.ey - self.by
        d = np.hypot(dx, dy)
        d[d < 1e-9] = 1e-9
        mini = self.r + self.er
        k = np.flatnonzero(d < mini)
        if k.size:
            nx, ny = dx[k] / d[k], dy[k] / d[k]
            self.ex[k] = self.bx + nx * mini[k]
            self.ey[k] = self.by + ny * mini[k]
            vn = (self.evx[k] - self.vx) * nx + (self.evy[k] - self.vy) * ny
            m = vn < 0
            if m.any():
                imp = -(1 + REBOND_BILLE) * vn[m] / (1 + 1 / MASSE_BALLE)
                self.evx[k[m]] += imp * nx[m]
                self.evy[k[m]] += imp * ny[m]
                self.vx -= float(np.sum(imp * nx[m])) / MASSE_BALLE
                self.vy -= float(np.sum(imp * ny[m])) / MASSE_BALLE
                s = math.hypot(self.vx, self.vy)
                if s > 1e-9:
                    self.vx *= V0 / s
                    self.vy *= V0 / s


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def dessiner(ctx, jeu, dt):
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    #  Le disque, et le liseré qui en fait le tour, teinté par la balle.
    ctx.new_path()
    ctx.arc(CX, CY, R, 0, TAU)
    ctx.save()
    ctx.clip_preserve()

    #  Les billes, par lots d'une même teinte : à deux mille disques, changer la
    #  source entre chaque coûte plus cher que le disque.
    if jeu.ex.size:
        lots = (jeu.eh / 24).astype(np.int32) * 100 + (jeu.el / 10).astype(np.int32)
        for cle in np.unique(lots):
            k = np.flatnonzero(lots == cle)
            ctx.new_path()
            for i in k:
                ctx.move_to(jeu.ex[i] + jeu.er[i], jeu.ey[i])
                ctx.arc(jeu.ex[i], jeu.ey[i], jeu.er[i], 0, TAU)
            ctx.set_source_rgb(*teinte((cle // 100) * 24 + 12, 1.0,
                                       ((cle % 100) * 10 + 5) / 100))
            ctx.fill()

    #  Les pointes : trois triangles qui tournent, pointe vers l'intérieur.
    for i in range(N_POINTES):
        a = ROTATION * jeu.t + i * TAU / N_POINTES
        ctx.new_path()
        ctx.move_to(CX + math.cos(-a) * (R - HAUT_POINTE),
                    CY + math.sin(-a) * (R - HAUT_POINTE))
        for s in (-1, 1):
            b = -(a + s * DEMI_POINTE)
            ctx.line_to(CX + math.cos(b) * R, CY + math.sin(b) * R)
        ctx.close_path()
        ctx.set_source_rgb(0.96, 0.98, 1.0)
        ctx.fill()

    #  La balle.
    deg = cairo.RadialGradient(jeu.bx - jeu.r * 0.3, jeu.by - jeu.r * 0.35,
                               jeu.r * 0.1, jeu.bx, jeu.by, jeu.r)
    deg.add_color_stop_rgb(0, 1, 1, 1)
    deg.add_color_stop_rgb(1, *teinte(jeu.teinte, 1.0, 0.55))
    ctx.set_source(deg)
    ctx.new_path()
    ctx.arc(jeu.bx, jeu.by, jeu.r, 0, TAU)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.7)
    ctx.set_line_width(3)
    ctx.stroke()
    ctx.restore()

    ctx.new_path()
    ctx.arc(CX, CY, R, 0, TAU)
    ctx.set_source_rgb(*teinte(jeu.teinte, 0.9, 0.55))
    ctx.set_line_width(4)
    ctx.stroke()

    # --- compteurs -------------------------------------------------------
    t = jeu.rempli if jeu.fini is not None else jeu.taux()
    texte(ctx, "remplir le cercle", CX, 250, 44, (0.94, 0.97, 0.99))
    larg, xg, yg = 2 * R * 0.78, CX - R * 0.78, H - 232
    ctx.set_source_rgba(1, 1, 1, 0.10)
    ctx.new_path(); ctx.rectangle(xg, yg, larg, 26); ctx.fill()
    ctx.set_source_rgb(*teinte(jeu.teinte, 1.0, 0.58))
    ctx.new_path()
    ctx.rectangle(xg, yg, max(26, larg * min(1, t / REMPLI_VISE)), 26)
    ctx.fill()
    texte(ctx, "%d %% du cercle" % round(100 * t), CX, H - 168, 38,
          (0.94, 0.97, 0.99))
    texte(ctx, "%d billes   ·   %d éclatements" % (jeu.ex.size, jeu.eclatements),
          CX, H - 118, 30, (0.75, 0.80, 0.82), gras=False)

    if jeu.fini is not None:
        v = min(1.0, (jeu.t - jeu.fini) / 0.5)
        ctx.set_source_rgba(0, 0, 0, 0.68 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "%d %%" % round(100 * jeu.rempli), CX, H / 2 + 10, 190,
              (0.95, 0.97, 0.99, v), cerne=0)
        texte(ctx, "%d billes dans le cercle" % jeu.ex.size, CX, H / 2 + 96, 44,
              (0.67, 0.75, 0.78, v), gras=False, cerne=0)


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


def rendre(graine=GRAINE, sortie="cercle_plein.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "cercle_plein-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "cercle_plein.wav")
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
