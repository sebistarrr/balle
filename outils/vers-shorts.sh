#!/usr/bin/env bash
#
# Convertit les vidéos rendues par Manim au format vertical des applications
# (YouTube Shorts, TikTok, Reels) : 1080x1920, 60 fps, H.264 + AAC.
#
# Les animations n'ont pas toutes le même rapport d'image — deux sont carrées,
# une est en 720:1244. On met donc l'image à l'échelle sans la déformer, puis
# on complète en noir jusqu'au cadre 9:16. Le fond des animations étant noir,
# le raccord ne se voit pas.
#
# Usage :  ./outils/vers-shorts.sh
# Prérequis : avoir rendu les scènes (voir la section « Rendre les vidéos »
# du README), puis lancer ce script depuis la racine du dépôt.

set -euo pipefail

CIBLE_L=1080
CIBLE_H=1920

convertir() {
  local dossier="$1" scene="$2" duree="$3"
  local source

  # Manim range ses sorties dans media/videos/<script>/<hauteur>p<fps>/. Il peut
  # y en avoir plusieurs (rendus d'essai en basse définition). On retient la
  # plus haute définition — et surtout pas le dernier par ordre alphabétique,
  # « 480p24 » passant avant « 1920p60 ».
  # « || true » n'est pas décoratif : sous set -e et pipefail, un find sur un
  # media/ absent — dossier jamais rendu, ou nettoyé — ferait sortir le script
  # au premier dossier venu, sans convertir les suivants.
  source="$( { find "$dossier/media/videos" -name "$scene.mp4" \
                 -not -path '*partial*' 2>/dev/null || true; } |
            while read -r f; do
              h="$(basename "$(dirname "$f")")"
              printf '%s\t%s\n' "${h%%p*}" "$f"
            done | sort -n | tail -1 | cut -f2)"

  if [ -z "$source" ]; then
    echo "  ! $dossier : rendu introuvable, scène $scene — passer" >&2
    return
  fi

  # -crf 21 : très bonne qualité. Ces images sont des traits fins sur du noir,
  # elles compressent bien ; inutile de conserver le débit énorme de Manim.
  # Manim allonge la vidéo à la longueur de la piste sonore, qui garde une
  # traîne de deux à trois secondes : sans coupe, le film se termine sur une
  # image figée. On coupe à la durée de l'animation, plus une demi-seconde pour
  # laisser respirer la dernière note.
  ffmpeg -y -loglevel error -i "$source" -t "$duree" \
    -vf "scale=${CIBLE_L}:${CIBLE_H}:force_original_aspect_ratio=decrease,\
pad=${CIBLE_L}:${CIBLE_H}:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p" \
    -c:v libx264 -preset slow -crf 21 -profile:v high -level 4.2 \
    -c:a aac -b:a 192k -movflags +faststart \
    "$dossier/shorts.mp4"

  printf '  %-32s %s\n' "$dossier" \
    "$(du -h "$dossier/shorts.mp4" | cut -f1)"
}

echo "Conversion au format 1080x1920 :"
#            dossier                       scène                durée + 0,5 s
convertir 1-vagues-de-pendule-intense   PendulumWaveIntense  24.5
convertir 2-billard-en-boucle           BilliardLoop         24.5
convertir 3-balle-qui-grossit           GrowingBall          23.7
convertir 4-rayons-de-rebond            BounceRays           55.7
convertir 5-balle-et-pointes            BalleEtPointes       30.0
#            les duels
convertir 6-cinq-vies                   CinqVies             24.5
convertir 7-course-en-spirale           CourseSpirale        14.5
convertir 8-sol-qui-s-effrite           SolEffrite           23.2
convertir 9-grand-plongeon              GrandPlongeon        17.3
convertir 10-guerre-de-territoire       GuerreTerritoire     21.4
convertir 11-pointes-qui-poussent       PointesPoussent      17.3
convertir 12-sumo                       Sumo                 21.1
convertir 13-les-portes                 LesPortes            25.1
convertir 15-le-mur-qui-pousse          MurQuiPousse         24.4
#            les courses à cinq
convertir 17-le-parcours                LeParcours           37.9
convertir 18-les-deux-epreuves          DeuxEpreuves         45.2
#            le plus gros mange le plus petit
convertir 14-le-dernier-debout          DernierDebout        25.3
convertir 20-les-gloutons               LesGloutons          35.5
#            les conquêtes
convertir 19-quatre-royaumes            QuatreRoyaumes       35.6
echo "Terminé."
