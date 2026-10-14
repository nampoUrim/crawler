"""Affiche le résumé d'un fichier JSON produit par crawler.py."""

import argparse
import json
from pathlib import Path


def charger_json(chemin):
    chemin = Path(chemin)
    if not chemin.is_file():
        raise SystemExit(f"Fichier introuvable : {chemin}")
    try:
        with chemin.open("r", encoding="utf-8") as fichier:
            donnees = json.load(fichier)
    except (OSError, json.JSONDecodeError) as erreur:
        raise SystemExit(f"Lecture du JSON impossible : {erreur}")

    champs_requis = ("url_source", "date_extraction", "titre", "paragraphes", "liens")
    manquants = [champ for champ in champs_requis if champ not in donnees]
    if manquants:
        raise SystemExit("JSON incomplet. Champs manquants : " + ", ".join(manquants))
    if not isinstance(donnees["paragraphes"], list) or not isinstance(donnees["liens"], list):
        raise SystemExit("JSON invalide : 'paragraphes' et 'liens' doivent être des listes.")
    return donnees


def main():
    parser = argparse.ArgumentParser(description="Consulte hors ligne un export JSON du crawler Chronos.")
    parser.add_argument("fichier", nargs="?", default="mansa_musa.json", help="Chemin du JSON")
    parser.add_argument("--paragraphes", type=int, default=5, help="Nombre de paragraphes à afficher (défaut : 5)")
    parser.add_argument("--liens", type=int, default=5, help="Nombre de liens à afficher (défaut : 5)")
    args = parser.parse_args()
    donnees = charger_json(args.fichier)

    liens = donnees["liens"]
    internes = donnees.get("liens_internes", [l for l in liens if l.get("type") == "interne"])
    externes = donnees.get("liens_externes", [l for l in liens if l.get("type") == "externe"])

    print("===== CONSULTATION HORS LIGNE =====")
    print("Fichier :", Path(args.fichier).resolve())
    print("Titre :", donnees.get("titre") or "(sans titre)")
    print("URL source :", donnees.get("url_source", ""))
    print("Date d'extraction :", donnees.get("date_extraction", "inconnue"))
    print("Nombre de paragraphes :", len(donnees["paragraphes"]))
    print("Nombre total de liens :", len(liens))
    print("Liens internes :", len(internes))
    print("Liens externes :", len(externes))

    print("\n===== TITRES H1 =====")
    for titre in donnees.get("titres_h1", []):
        print("-", titre)

    print(f"\n===== {max(0, args.paragraphes)} PREMIERS PARAGRAPHES =====")
    for numero, paragraphe in enumerate(donnees["paragraphes"][:max(0, args.paragraphes)], start=1):
        print(f"\nParagraphe {numero} :\n{paragraphe}")

    print(f"\n===== {max(0, args.liens)} PREMIERS LIENS =====")
    for lien in liens[:max(0, args.liens)]:
        print(f"- [{lien.get('type', 'inconnu')}] {lien.get('texte') or '(sans texte)'} : {lien.get('url', '')}")


if __name__ == "__main__":
    main()
