"""
La prison — rendu vidéo, format vertical.

Une balle au centre, quarante murs concentriques autour d'elle, aucune porte.
Chaque choc pulvérise le morceau de mur touché ; les débris tombent et
s'entassent en bas. Le compteur dit combien de briques tiennent encore.

Rendu :
    python prison.py                 # écrit prison.mp4 en 1080 x 1920, 60 im/s
    python prison.py --graines       # essaie des tirages et donne durée et reste

Pourquoi pas Manim, comme les autres animations du dépôt
--------------------------------------------------------
Manim est fait pour des scènes : des objets nommés, peu nombreux, qu'on anime.
Il reconstruit ses objets vectoriels à chaque image, ce qui est parfait pour une
démonstration et ruineux ici. Mesuré sur exactement ce contenu — deux mille arcs
et deux mille grains en 1080 x 1920 :

    Manim   33 s par seconde de film   (~16 min pour 30 s)
    Cairo   1,4 s par seconde de film  (~42 s pour 30 s)

Vingt-quatre fois plus rapide, pour un résultat identique. Cairo est un moteur
de rasterisation : on lui donne des chemins, il remplit des pixels, et rien ne
survit d'une image à l'autre — ce qui tombe bien, puisque tout change.

Les images brutes sont envoyées directement dans ffmpeg par un tube, sans passer
par des milliers de PNG sur le disque. Le son est fabriqué à part, puis collé.
"""

import math
import subprocess
import sys
import wave

import cairo
import numpy as np

TAU = 2 * math.pi

# --------------------------------------------------------------------------
#  Réglages, identiques à la page voisine
# --------------------------------------------------------------------------
W, H = 1080, 1920
CX, CY = 540, 980
R0 = 100                    # rayon du premier anneau
PAS = 20                    # écart entre deux anneaux
N_ANNEAUX = 40
ARC_CIBLE = 70              # longueur visée d'une brique, en px
R_MAX = R0 + (N_ANNEAUX - 1) * PAS
EVASION = R_MAX + 60

R_BALLE = 15
V0 = 2900.0                 # px/s — pas de gravité pour la balle
DT = 1 / 480
MORSURE0 = 13.0
MORSURE_ACCEL = 0.9
#  Déviation tirée au sort à chaque rebond. Sans elle, la normale d'un anneau
#  étant radiale, le rebond conserve le moment angulaire : la balle reste
#  prisonnière d'une couronne étroite et n'abat qu'un cinquième des briques.
DEVIATION = 0.28

G_POUSSIERE = 900.0
REBOND_TAS = 0.12
LARG_COL = 6
N_COL = math.ceil(W / LARG_COL)

FPS = 60
APRES = 3.5                 # s de bandeau après l'évasion

#  Les anneaux alternent le rouge et le vert, comme la vidéo de référence.
ROUGE = (0.88, 0.16, 0.16)
VERT = (0.16, 0.82, 0.32)

#  Graine 4 : 35,7 s et 34 briques debout à la fin — le tirage le plus proche
#  de la vidéo de référence, qui dure 38 s et en laisse neuf.
GRAINE = 4

#  Un anneau de rayon r est découpé en briques d'environ ARC_CIBLE pixels, donc
#  les anneaux extérieurs en comptent davantage : les briques gardent la même
#  taille apparente d'un bout à l'autre du dessin.
RAYONS = [R0 + k * PAS for k in range(N_ANNEAUX)]
NOMBRES = [max(8, round(TAU * r / ARC_CIBLE)) for r in RAYONS]
TOTAL = sum(NOMBRES)


def morsure(t):
    return MORSURE0 + MORSURE_ACCEL * t


# --------------------------------------------------------------------------
#  Simulation et rendu, en une seule passe
#
#  Les images sont dessinées au fil de la simulation plutôt que stockées : à
#  deux mille briques et deux mille grains, garder un instantané par image
#  coûterait des centaines de mégaoctets pour rien.
# --------------------------------------------------------------------------
class Partie:
    def __init__(self, graine):
        self.rng = np.random.default_rng(graine)
        self.vivants = [np.ones(n, dtype=bool) for n in NOMBRES]
        self.restants = TOTAL
        self.t = 0.0
        self.fini = None                       # instant de l'évasion
        self.chocs = []                        # (instant, anneau, pan)
        self.tas = np.full(N_COL, float(H))
        #  Poussière : trois tableaux parallèles plutôt qu'une liste d'objets.
        self.px = np.zeros(TOTAL)
        self.py = np.zeros(TOTAL)
        self.pvx = np.zeros(TOTAL)
        self.pvy = np.zeros(TOTAL)
        self.protons = np.zeros(TOTAL, dtype=bool)   # posé au sol
        self.pcoul = np.zeros(TOTAL, dtype=np.uint8)
        self.n_poussiere = 0

        #  Départ décalé du centre, et de biais. Partie du centre exact, la
        #  balle n'a aucun moment angulaire — et le rebond radial le conserve :
        #  elle fait l'aller-retour dans un couloir pour l'éternité.
        ou = self.rng.uniform(0, TAU)
        biais = self.rng.choice([-1, 1]) * self.rng.uniform(0.9, 1.4)
        self.bx = CX + math.cos(ou) * 55
        self.by = CY + math.sin(ou) * 55
        self.vx = math.cos(ou + biais) * V0
        self.vy = math.sin(ou + biais) * V0

    # -- une brique tombe ---------------------------------------------------
    def semer(self, k, j):
        n = self.n_poussiere
        if n >= TOTAL:
            return
        pas_a = TAU / NOMBRES[k]
        th = (j + 0.5) * pas_a
        r = RAYONS[k]
        self.px[n] = CX + math.cos(th) * r
        self.py[n] = CY - math.sin(th) * r
        v = self.rng.uniform(40, 160)
        self.pvx[n] = math.cos(th) * v + self.rng.uniform(-45, 45)
        self.pvy[n] = -math.sin(th) * v - self.rng.uniform(0, 160)
        self.pcoul[n] = k % 2
        self.n_poussiere = n + 1

    def ronger(self, k, angle):
        """Abat les briques de l'anneau k autour de cet angle."""
        r = RAYONS[k]
        n = NOMBRES[k]
        #  Demi-angle occupé par la balle sur cet anneau, multiplié par la
        #  morsure. Sur un anneau intérieur elle couvre un large secteur, sur un
        #  anneau lointain presque rien : la prison s'ouvre en éventail.
        demi = math.asin(min(0.9, R_BALLE / r)) * morsure(self.t) + 0.02
        pas_a = TAU / n
        vivants = self.vivants[k]
        pris = 0
        for i in range(math.floor((angle - demi) / pas_a),
                       math.ceil((angle + demi) / pas_a) + 1):
            j = i % n
            if not vivants[j]:
                continue
            vivants[j] = False
            self.restants -= 1
            self.semer(k, j)
            pris += 1
        return pris

    # -- un pas de simulation ------------------------------------------------
    def pas(self):
        #  Une fois l'évasion prononcée, plus rien ne bouge : sans cette sortie,
        #  chaque pas suivant retrouve la balle hors du cercle et repousse
        #  l'instant de fin, si bien que le bandeau n'arrive jamais et que le
        #  film tourne jusqu'au garde-fou.
        if self.fini is not None:
            return
        self.t += DT
        self.bx += self.vx * DT
        self.by += self.vy * DT
        dx, dy = self.bx - CX, self.by - CY
        d = math.sqrt(dx * dx + dy * dy)

        if d > EVASION or self.restants <= 0:
            self.fini = self.t
            return

        #  Un seul anneau peut être en contact : celui dont le rayon est le plus
        #  proche. Inutile de parcourir les quarante.
        k = round((d - R0) / PAS)
        if not (0 <= k < N_ANNEAUX):
            return
        r = RAYONS[k]
        ecart = d - r
        if abs(ecart) >= R_BALLE + 3:
            return

        angle = math.atan2(-dy, dx)
        n = NOMBRES[k]
        pas_a = TAU / n
        #  On regarde toutes les briques que la balle chevauche, pas seulement
        #  celle qui est sous son centre : sinon une seule brique abattue suffit
        #  à la laisser passer et elle perce un tunnel radial.
        demi_b = math.asin(min(0.95, (R_BALLE + 2) / r))
        vivants = self.vivants[k]
        bloque = any(vivants[i % n]
                     for i in range(math.floor((angle - demi_b) / pas_a),
                                    math.ceil((angle + demi_b) / pas_a) + 1))
        if not bloque:
            return

        nx, ny = dx / (d or 1), dy / (d or 1)
        sens = -1 if ecart < 0 else 1
        self.bx = CX + nx * (r + sens * (R_BALLE + 3))
        self.by = CY + ny * (r + sens * (R_BALLE + 3))
        p = 2 * (self.vx * nx + self.vy * ny)
        vx, vy = self.vx - p * nx, self.vy - p * ny
        dev = self.rng.uniform(-DEVIATION, DEVIATION)
        cd, sd = math.cos(dev), math.sin(dev)
        wx, wy = vx * cd - vy * sd, vx * sd + vy * cd
        s = math.sqrt(wx * wx + wy * wy)
        self.vx, self.vy = wx * V0 / s, wy * V0 / s

        if self.ronger(k, angle):
            self.chocs.append((self.t, k, (self.bx - CX) / R_MAX))

    # -- la poussière, à la cadence de l'image -------------------------------
    def pas_poussiere(self, h):
        n = self.n_poussiere
        if n == 0:
            return
        libre = ~self.protons[:n]
        if not libre.any():
            return
        self.pvy[:n][libre] += G_POUSSIERE * h
        self.px[:n][libre] += self.pvx[:n][libre] * h
        self.py[:n][libre] += self.pvy[:n][libre] * h
        np.clip(self.px[:n], 2, W - 2, out=self.px[:n])

        cols = np.clip((self.px[:n] / LARG_COL).astype(int), 0, N_COL - 1)
        sol = self.tas[cols] - 2
        touche = libre & (self.py[:n] >= sol)
        for i in np.nonzero(touche)[0]:
            c = cols[i]
            self.py[i] = self.tas[c] - 2
            if abs(self.pvy[i]) > 130:
                self.pvy[i] = -abs(self.pvy[i]) * REBOND_TAS
                self.pvx[i] *= 0.6
            else:
                self.protons[i] = True
                #  La colonne monte, et un peu ses voisines : le tas s'étale au
                #  lieu de faire des tours.
                self.tas[c] -= 3.0
                if c > 0:
                    self.tas[c - 1] -= 1.0
                if c < N_COL - 1:
                    self.tas[c + 1] -= 1.0


# --------------------------------------------------------------------------
#  Dessin d'une image
# --------------------------------------------------------------------------
def texte(ctx, s, x, y, taille, couleur, gras=True):
    """Texte centré, cerné de noir.

    Le titre et le compteur se posent sur les anneaux ; sans ce cerne ils s'y
    perdent dès que la brèche s'ouvre de leur côté.
    """
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if gras else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(taille)
    ext = ctx.text_extents(s)
    ctx.new_path()
    ctx.move_to(x - (ext.width / 2 + ext.x_bearing), y)
    ctx.text_path(s)
    ctx.set_source_rgba(0.016, 0.024, 0.039, 0.92)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(9)
    ctx.stroke_preserve()
    ctx.set_source_rgba(*couleur)
    ctx.fill()


def dessiner(ctx, jeu):
    ctx.set_source_rgb(0.016, 0.024, 0.039)
    ctx.paint()

    # --- les murs ---------------------------------------------------------
    #  Un tracé par couleur, et non un par brique : c'est ce qui tient le rendu
    #  à quelques dizaines de millisecondes l'image.
    ctx.set_line_width(7)
    for teinte, coul in ((0, ROUGE), (1, VERT)):
        ctx.new_path()
        for k in range(N_ANNEAUX):
            if k % 2 != teinte:
                continue
            vivants = jeu.vivants[k]
            if not vivants.any():
                continue
            r = RAYONS[k]
            n = NOMBRES[k]
            pas_a = TAU / n
            #  Un cheveu de jeu entre deux briques : trois pixels, donc un angle
            #  qui décroît avec le rayon. Un jeu angulaire constant rendrait
            #  l'arc négatif sur les anneaux extérieurs, et ses extrémités
            #  s'inverseraient — l'anneau paraîtrait intact quoi qu'il arrive.
            jeu_a = min(0.30 * pas_a, 3 / r)
            for j in np.nonzero(vivants)[0]:
                a0 = j * pas_a + jeu_a
                a1 = (j + 1) * pas_a - jeu_a
                ctx.new_sub_path()
                ctx.arc_negative(CX, CY, r, -a0, -a1)
        ctx.set_source_rgb(*coul)
        ctx.stroke()

    # --- la poussière -----------------------------------------------------
    n = jeu.n_poussiere
    if n:
        for teinte, coul in ((0, ROUGE), (1, VERT)):
            k = jeu.pcoul[:n] == teinte
            if not k.any():
                continue
            ctx.new_path()
            for x, y in zip(jeu.px[:n][k], jeu.py[:n][k]):
                ctx.rectangle(x - 2.5, y - 2.5, 5, 5)
            ctx.set_source_rgb(coul[0] * 0.8, coul[1] * 0.8, coul[2] * 0.8)
            ctx.fill()

    # --- la balle ---------------------------------------------------------
    for f, a in ((4.0, 0.08), (2.4, 0.20)):
        ctx.set_source_rgba(1.0, 0.96, 0.80, a)
        ctx.new_path()
        ctx.arc(jeu.bx, jeu.by, R_BALLE * f, 0, TAU)
        ctx.fill()
    grad = cairo.RadialGradient(jeu.bx - 5, jeu.by - 6, 2,
                                jeu.bx, jeu.by, R_BALLE)
    grad.add_color_stop_rgb(0, 1, 1, 1)
    grad.add_color_stop_rgb(1, 1.0, 0.82, 0.34)
    ctx.set_source(grad)
    ctx.new_path()
    ctx.arc(jeu.bx, jeu.by, R_BALLE, 0, TAU)
    ctx.fill()

    # --- textes -----------------------------------------------------------
    texte(ctx, "la balle peut-elle s'évader ?", W / 2, 108, 44,
          (0.94, 0.97, 0.99, 1))
    texte(ctx, str(jeu.restants), CX, CY + 20, 66, (0.97, 0.98, 0.99, 1))
    texte(ctx, "briques encore debout   ·   %d au départ" % TOTAL,
          CX, CY + 74, 28, (0.59, 0.66, 0.70, 1), gras=False)

    if jeu.fini is not None:
        v = min(1.0, (jeu.t - jeu.fini) / 0.4)
        ctx.set_source_rgba(0.016, 0.024, 0.039, 0.86 * v)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        texte(ctx, "ÉVADÉE", W / 2, H / 2, 118, (1.0, 0.80, 0.20, v))
        texte(ctx, ("%d briques abattues en %.1f s"
                    % (TOTAL - jeu.restants, jeu.fini)).replace(".", ","),
              W / 2, H / 2 + 80, 40, (0.71, 0.77, 0.81, v), gras=False)


# --------------------------------------------------------------------------
#  Bande son : une note par choc, plus aiguë à mesure que la balle gagne du
#  terrain, et un accord à l'évasion. Écrite ici, rien d'emprunté.
# --------------------------------------------------------------------------
def bande_son(chocs, fin, duree, chemin, sr=44100):
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

    #  Une note sur trois : à une trentaine de chocs par seconde, tout sonner
    #  ferait un mur de bruit au lieu d'un rythme.
    for i, (instant, anneau, pan) in enumerate(chocs):
        if i % 3:
            continue
        poser(instant, cloche(round(24 * anneau / N_ANNEAUX), 0.20), pan)

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
        canal += 0.35 * reverbe(canal, ir / np.abs(ir).sum() * 6.0)

    stereo = np.stack([np.tanh(gauche * 1.1), np.tanh(droite * 1.1)], axis=1)
    pcm = (stereo / max(1e-9, np.abs(stereo).max()) * 0.92 * 32767).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return chemin


# --------------------------------------------------------------------------
def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def rendre(graine=GRAINE, sortie="prison.mp4"):
    jeu = Partie(graine)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    muet = "prison-muet.mp4"
    proc = subprocess.Popen(
        [ffmpeg(), "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "%dx%d" % (W, H),
         "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "21",
         "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", muet],
        stdin=subprocess.PIPE)

    images = 0
    reste_sim = 0.0
    while True:
        #  On avance la simulation d'une image, puis on dessine.
        reste_sim += 1 / FPS
        while reste_sim >= DT:
            reste_sim -= DT
            jeu.pas()
            if jeu.fini is not None:
                break
        jeu.pas_poussiere(1 / FPS)
        if jeu.fini is not None:
            jeu.t += 1 / FPS          # le temps continue pour le fondu
        dessiner(ctx, jeu)
        surf.flush()
        proc.stdin.write(bytes(surf.get_data()))
        images += 1
        if jeu.fini is not None and jeu.t - jeu.fini > APRES:
            break
        if images > FPS * 180:        # garde-fou
            break

    proc.stdin.close()
    proc.wait()

    duree = images / FPS
    son = bande_son(jeu.chocs, jeu.fini or duree, duree, "prison.wav")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", muet,
                    "-i", son, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", sortie], check=True)
    print("%s : %.1f s, %d images, %d briques abattues sur %d"
          % (sortie, duree, images, TOTAL - jeu.restants, TOTAL))
    return duree


if __name__ == "__main__":
    if "--graines" in sys.argv:
        #  De quoi choisir une évasion ni trop courte ni interminable.
        print("graine   durée  briques restantes")
        for g in range(8):
            jeu = Partie(g)
            while jeu.fini is None and jeu.t < 150:
                jeu.pas()
            print("%5d %7.1f %12d" % (g, jeu.t, jeu.restants))
    else:
        rendre()
