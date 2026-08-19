"""
La spirale rongée — rendu vidéo, format vertical.

Une spirale qui remplit tout le cadre, et deux balles lâchées dans la
petite cavité du centre. Chaque rebond ronge le morceau touché : la cavité
grandit, les balles gagnent de la place, et la spirale disparaît de l'intérieur.
Une minute au compteur ; celle qui a donné le plus de coups l'emporte.

Reproduction d'une vidéo existante, refaite de zéro.

Rendu :
    python spirale_rongee.py                 # écrit spirale_rongee.mp4 en 1080 x 1920, 60 im/s
    python spirale_rongee.py --graines       # essaie des tirages et donne ce qu'ils valent

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
CX, CY = 540.0, 1000.0
R0 = 118.0                  # rayon de la cavité de départ
PAS = 21.0                  # écart entre deux tours de la spirale
N_TOURS = 54                # de quoi couvrir le cadre en entier
EP = 6.0
ARC = 46.0                  # longueur visée d'un tronçon, en px
#  La morsure s'élargit avec le temps. Sans cela l'érosion s'essouffle : plus la
#  cavité grandit, plus les balles mettent de temps à revenir toucher un bras, et
#  le nombre de coups par seconde s'effondre — mesuré, un quart de la spirale
#  rongée en une minute, contre la quasi-totalité dans la vidéo d'origine.
MORSURE0 = 62.0
MORSURE_ACCEL = 3.4         # px par seconde

R_BALLE = 27.0
G = 900.0
REBOND = 1.0                # les balles ne s'essoufflent pas
V_MIN, V_MAX = 900.0, 2000.0
DUREE = 60.0                # s — le compte à rebours du bas
DT = 1 / 480

NOMS = ("ORANGE", "VERT")
TEINTES = (26.0, 138.0)

GRAINE = 0


def rayon_de(k, a):
    """Rayon de la spirale au tour k, à l'angle a.

    C'est une spirale d'Archimède : un tour complet fait gagner exactement un
    PAS, si bien qu'un point du plan appartient à un seul bras, celui d'indice
    (r - R0) / PAS - a / 2π arrondi. C'est ce qui rend la détection des chocs
    immédiate, au lieu de parcourir trois mille tronçons à chaque pas.
    """
    return R0 + PAS * (k + a / TAU)


def n_seg(k):
    return max(24, round(TAU * rayon_de(k, 0) / ARC))


class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        self.mur = [np.ones(n_seg(k), dtype=np.uint8) for k in range(N_TOURS)]
        self.total = sum(m.size for m in self.mur)
        self.ronges = 0
        self.b = []
        for i in range(2):
            a = math.pi / 3 + i * math.pi / 3 + self.rng.uniform(0, 0.6)
            self.b.append({"i": i, "score": 0,
                           "x": CX + (34 if i else -34), "y": CY - 10,
                           "vx": math.cos(a) * V_MIN * (1 if i else -1),
                           "vy": math.sin(a) * V_MIN})
        self.t = 0.0
        self.fini = None
        self.vainqueur = -1
        self.notes = []

    def bilan(self):
        return "%d contre %d, %d %% rongé" % (
            self.b[0]["score"], self.b[1]["score"],
            round(100 * self.ronges / self.total))

    def seg_de(self, k, a):
        n = self.mur[k].size
        u = a / TAU
        u -= math.floor(u)
        return min(n - 1, int(u * n))

    def ronger(self, x, y):
        """Ronge tout ce qui est à portée du point touché.

        Un tronçon par choc laisserait une dentelle invisible : c'est la morsure
        large qui creuse la cavité qu'on regarde grandir.
        """
        dx, dy = x - CX, y - CY
        r = math.hypot(dx, dy)
        a = math.atan2(dy, dx)
        k0 = round((r - R0) / PAS - a / TAU)
        morsure = MORSURE0 + MORSURE_ACCEL * self.t
        dk = math.ceil(morsure / PAS)
        for k in range(max(0, k0 - dk), min(N_TOURS - 1, k0 + dk) + 1):
            m = self.mur[k]
            n = m.size
            da = min(math.pi, morsure / max(40.0, rayon_de(k, a)))
            j0 = self.seg_de(k, a - da)
            j1 = self.seg_de(k, a + da)
            d = 0
            while d <= n:
                j = (j0 + d) % n
                if m[j]:
                    aj = (j + 0.5) / n * TAU
                    rj = rayon_de(k, aj)
                    if math.hypot(CX + math.cos(aj) * rj - x,
                                  CY + math.sin(aj) * rj - y) < morsure:
                        m[j] = 0
                        self.ronges += 1
                if j == j1:
                    break
                d += 1

    def pas(self):
        if self.fini is not None:
            self.t += DT
            return
        self.t += DT

        for b in self.b:
            b["vy"] += G * DT
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT

            dx, dy = b["x"] - CX, b["y"] - CY
            r = math.hypot(dx, dy) or 1e-9
            a = math.atan2(dy, dx)
            u = (r - R0) / PAS - a / TAU
            k = round(u)
            if 0 <= k < N_TOURS:
                d = (u - k) * PAS
                if abs(d) < EP + R_BALLE and self.mur[k][self.seg_de(k, a)]:
                    #  La normale d'une spirale serrée est, à un degré près,
                    #  radiale.
                    nx, ny = dx / r, dy / r
                    sens = 1.0 if d >= 0 else -1.0
                    cible = r + (sens * (EP + R_BALLE) - d)
                    b["x"], b["y"] = CX + nx * cible, CY + ny * cible
                    p = (1 + REBOND) * (b["vx"] * nx + b["vy"] * ny)
                    b["vx"] -= p * nx
                    b["vy"] -= p * ny
                    b["score"] += 1
                    self.ronger(b["x"] - nx * sens * R_BALLE,
                                b["y"] - ny * sens * R_BALLE)
                    if len(self.notes) < 4000:
                        self.notes.append(
                            (self.t, (b["score"] % 5) * 2 + (7 if b["i"] else 0),
                             0.16, (b["x"] - W / 2) / (W / 2)))

            #  Bord extérieur infranchissable, au dernier tour. Sans lui, une
            #  balle qui traverse une zone entièrement rongée continue tout droit
            #  et ne rencontre plus jamais rien : mesuré, l'érosion s'arrêtait
            #  net à 77 % et les scores se figeaient vingt secondes avant la fin.
            #  Ce bord est hors du cadre, on ne le voit pas.
            rlim = rayon_de(N_TOURS - 1, a) - R_BALLE
            if r > rlim:
                nx, ny = dx / r, dy / r
                b["x"], b["y"] = CX + nx * rlim, CY + ny * rlim
                p = 2 * (b["vx"] * nx + b["vy"] * ny)
                if p > 0:
                    b["vx"] -= p * nx
                    b["vy"] -= p * ny

            #  Vitesse tenue entre deux bornes : trop lente, la balle s'endort
            #  dans un creux ; trop rapide, elle traverse la spirale.
            s = math.hypot(b["vx"], b["vy"]) or 1e-9
            if s < V_MIN:
                b["vx"] *= V_MIN / s; b["vy"] *= V_MIN / s
            if s > V_MAX:
                b["vx"] *= V_MAX / s; b["vy"] *= V_MAX / s

        a, b = self.b
        ex, ey = b["x"] - a["x"], b["y"] - a["y"]
        dd = math.hypot(ex, ey)
        if 1e-9 < dd < 2 * R_BALLE:
            nx, ny = ex / dd, ey / dd
            corr = (2 * R_BALLE - dd) / 2
            a["x"] -= nx * corr; a["y"] -= ny * corr
            b["x"] += nx * corr; b["y"] += ny * corr
            vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
            if vn < 0:
                a["vx"] += vn * nx; a["vy"] += vn * ny
                b["vx"] -= vn * nx; b["vy"] -= vn * ny

        if self.t >= DUREE:
            self.fini = self.t
            self.vainqueur = 0 if self.b[0]["score"] >= self.b[1]["score"] else 1


# --------------------------------------------------------------------------
#  Rendu
# --------------------------------------------------------------------------
def dessiner(ctx, jeu, dt):
    #  Fond bleu nuit plutôt que noir : c'est la cavité, et elle doit se
    #  distinguer franchement de la spirale.
    ctx.set_source_rgb(0.102, 0.133, 0.267)
    ctx.paint()

    #  Un seul chemin pour toute la spirale : les tronçons rongés sont
    #  simplement omis, et les suites intactes tracées d'un trait.
    ctx.new_path()
    for k in range(N_TOURS):
        m = jeu.mur[k]
        n = m.size
        pas = TAU / n
        j = 0
        while j < n:
            if not m[j]:
                j += 1
                continue
            fin = j
            while fin + 1 < n and m[fin + 1]:
                fin += 1
            for q in range(j, fin + 2):
                aq = q * pas
                rq = rayon_de(k, aq)
                x, y = CX + math.cos(aq) * rq, CY + math.sin(aq) * rq
                if q == j:
                    ctx.move_to(x, y)
                else:
                    ctx.line_to(x, y)
            j = fin + 1
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgb(0.184, 0.388, 0.949)
    ctx.set_line_width(2 * EP)
    ctx.stroke()

    for b in jeu.b:
        r, v, bl = teinte(TEINTES[b["i"]], 0.95, 0.52)
        deg = cairo.RadialGradient(b["x"] - 9, b["y"] - 10, 3,
                                   b["x"], b["y"], R_BALLE)
        deg.add_color_stop_rgb(0, 1, 1, 1)
        deg.add_color_stop_rgb(1, r, v, bl)
        ctx.set_source(deg)
        ctx.new_path()
        ctx.arc(b["x"], b["y"], R_BALLE, 0, TAU)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.55)
        ctx.set_line_width(2.5)
        ctx.stroke()

    for b in jeu.b:
        x = W / 2 + (200 if b["i"] else -200)
        texte(ctx, NOMS[b["i"]], x, 300, 46, teinte(TEINTES[b["i"]], 1.0, 0.62))
        texte(ctx, str(b["score"]), x, 358, 44, teinte(TEINTES[b["i"]], 1.0, 0.62))
    texte(ctx, str(max(0, math.ceil(DUREE - jeu.t))), W / 2, H - 60, 56,
          (0.94, 0.965, 0.988))

    if jeu.fini is not None:
        v = min(1.0, (jeu.t - jeu.fini) / 0.4)
        g = jeu.vainqueur
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.7 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "vainqueur", W / 2, H / 2 - 120, 44, (0.78, 0.84, 0.86, v),
              gras=False, cerne=0)
        texte(ctx, NOMS[g], W / 2, H / 2 + 10, 118,
              teinte(TEINTES[g], 1.0, 0.62) + (v,), cerne=0)
        texte(ctx, "%d contre %d" % (jeu.b[g]["score"], jeu.b[1 - g]["score"]),
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


def rendre(graine=GRAINE, sortie="spirale_rongee.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "spirale_rongee-muet.mp4"
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
    son = bande_son(jeu.notes, jeu.fini or duree, duree, "spirale_rongee.wav")
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
