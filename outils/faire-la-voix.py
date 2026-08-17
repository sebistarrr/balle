#!/usr/bin/env python3
"""
Synthétise la voix off de l'animation 9, une phrase par fichier.

La voix donne le tempo : l'animation lit ensuite la durée réelle de chaque
fichier pour caler ses étapes dessus. Une phrase par fichier, et non un seul
long enregistrement, précisément pour cela.

    pip install piper-tts
    python3 -m piper.download_voices fr_FR-siwis-medium
    python3 outils/faire-la-voix.py

Le modèle et les fichiers produits ne sont pas dans le dépôt par défaut : ce
script les régénère à l'identique.
"""

import pathlib
import subprocess
import sys

SORTIE = pathlib.Path(__file__).resolve().parent.parent / "9-tables-expliquees" / "voix"
MODELE = "fr_FR-siwis-medium"

#  Phrases courtes, une idée chacune : c'est ce qui permet de couper le montage
#  au bon endroit, et de reprendre une phrase sans tout refaire.
PHRASES = [
    "Un cercle. Dix nombres, de zéro à neuf.",
    "Relie chaque nombre à son double.",
    "Un donne deux. Deux donne quatre. Trois donne six.",
    "Cinq fois deux : dix. Mais il n'y a pas de dix. Alors on repart de zéro.",
    "On continue. Et voilà la table de deux.",
    "Maintenant, beaucoup plus de nombres.",
    "Quarante. Cent vingt. Deux cent quarante.",
    "Un cœur, dessiné par une table de multiplication.",
    "Change de table, et la figure change.",
    "Trois : deux pointes. Quatre : trois pointes. Toujours une de moins.",
    "Une seule règle. Et tout ça était caché dedans.",
]


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    for i, phrase in enumerate(PHRASES, 1):
        cible = SORTIE / f"ligne-{i:02d}.wav"
        subprocess.run(
            [sys.executable, "-m", "piper", "--model", MODELE,
             "--output-file", str(cible)],
            input=phrase, text=True, check=True,
        )
        print(f"{cible.name}  {phrase}")


if __name__ == "__main__":
    main()
