"""Crawler éducatif pour extraire une page web et l'enregistrer en JSON."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "ChronosCrawler/1.0 (crawler educatif; usage personnel)"
TIMEOUT = 20


def normaliser_url(url):
    """Retire le fragment (#...) et les espaces superflus d'une URL."""
    url = (url or "").strip()
    url, _fragment = urldefrag(url)
    return url


def extraire_page(url):
    """Télécharge une page HTTP(S) et renvoie ses données sous forme de dict.

    Renvoie None en cas d'erreur réseau ou si l'URL n'est pas HTTP(S).
    """
    url = normaliser_url(url)
    analyse_url = urlparse(url)
    if analyse_url.scheme not in {"http", "https"} or not analyse_url.netloc:
        print("Erreur : l'URL doit commencer par http:// ou https://.", file=sys.stderr)
        return None

    entetes = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "fr,en;q=0.8",
    }

    try:
        reponse = requests.get(url, headers=entetes, timeout=TIMEOUT)
        reponse.raise_for_status()
    except requests.exceptions.RequestException as erreur:
        print(f"Erreur lors du téléchargement : {erreur}", file=sys.stderr)
        return None

    soupe = BeautifulSoup(reponse.text, "html.parser")
    titre = soupe.title.get_text(" ", strip=True) if soupe.title else ""
    titres_h1 = [
        element.get_text(" ", strip=True)
        for element in soupe.find_all("h1")
        if element.get_text(" ", strip=True)
    ]

    # Sur Wikipédia, on limite l'extraction à l'article principal. Pour les
    # autres sites, on utilise le corps du document quand il existe.
    contenu = (
        soupe.select_one("main#content")
        or soupe.select_one("main")
        or soupe.select_one("article")
        or soupe.body
        or soupe
    )

    paragraphes = []
    for element in contenu.find_all("p"):
        texte = re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()
        if texte:
            paragraphes.append(texte)

    domaine_page = urlparse(reponse.url).netloc.lower()
    liens = []
    urls_vues = set()

    for element in contenu.find_all("a", href=True):
        href = element.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue

        url_lien = normaliser_url(urljoin(reponse.url, href))
        analyse_lien = urlparse(url_lien)
        if analyse_lien.scheme not in {"http", "https"} or not analyse_lien.netloc:
            continue

        cle_url = url_lien.lower()
        if cle_url in urls_vues:
            continue
        urls_vues.add(cle_url)

        texte_lien = re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()
        type_lien = "interne" if analyse_lien.netloc.lower() == domaine_page else "externe"
        liens.append({"texte": texte_lien, "url": url_lien, "type": type_lien})

    liens_internes = [lien for lien in liens if lien["type"] == "interne"]
    liens_externes = [lien for lien in liens if lien["type"] == "externe"]

    return {
        "version_schema": 1,
        "url_source": reponse.url,
        "date_extraction": datetime.now().astimezone().isoformat(timespec="seconds"),
        "titre": titre,
        "titres_h1": titres_h1,
        "paragraphes": paragraphes,
        "liens": liens,
        "liens_internes": liens_internes,
        "liens_externes": liens_externes,
        "nombre_paragraphes": len(paragraphes),
        "nombre_liens": len(liens),
        "nombre_liens_internes": len(liens_internes),
        "nombre_liens_externes": len(liens_externes),
    }


def nom_fichier_depuis_url(url):
    """Produit un nom de fichier simple à partir du dernier segment d'URL."""
    segment = urlparse(url).path.rstrip("/").split("/")[-1] or "page_web"
    segment = re.sub(r"[^a-zA-Z0-9_-]+", "_", segment).strip("_").lower()
    return f"{segment or 'page_web'}.json"


def main():
    parser = argparse.ArgumentParser(description="Extrait une page web vers un fichier JSON Chronos.")
    parser.add_argument("url", nargs="?", default="https://en.wikipedia.org/wiki/Mansa_Musa", help="URL HTTP(S) à extraire")
    parser.add_argument("-o", "--sortie", help="Chemin du fichier JSON de sortie")
    args = parser.parse_args()

    resultat = extraire_page(args.url)
    if resultat is None:
        raise SystemExit(1)

    chemin_sortie = Path(args.sortie) if args.sortie else Path(nom_fichier_depuis_url(resultat["url_source"]))
    try:
        chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
        with chemin_sortie.open("w", encoding="utf-8") as fichier:
            json.dump(resultat, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
    except OSError as erreur:
        raise SystemExit(f"Impossible d'enregistrer le JSON : {erreur}")

    print("===== RÉSUMÉ DU CRAWL =====")
    print("URL source :", resultat["url_source"])
    print("Titre :", resultat["titre"])
    print("Paragraphes :", resultat["nombre_paragraphes"])
    print("Liens :", resultat["nombre_liens"])
    print("Liens internes :", resultat["nombre_liens_internes"])
    print("Liens externes :", resultat["nombre_liens_externes"])
    print("Fichier JSON :", chemin_sortie.resolve())


if __name__ == "__main__":
    main()
