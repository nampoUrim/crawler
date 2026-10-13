
import requests
from bs4 import BeautifulSoup


def extraire_page(url):
    """Télécharge une page et extrait ses principales informations."""

    reponse = requests.get(url, timeout=15)
    reponse.raise_for_status()

    soupe = BeautifulSoup(reponse.text, "html.parser")

    titre = (
        soupe.title.get_text(" ", strip=True)
        if soupe.title
        else ""
    )

    titres = [
        element.get_text(" ", strip=True)
        for element in soupe.find_all("h1")
    ]

    paragraphes = [
        element.get_text(" ", strip=True)
        for element in soupe.find_all("p")
        if element.get_text(" ", strip=True)
    ]

    liens = []

    for lien in soupe.find_all("a", href=True):
        liens.append({
            "texte": lien.get_text(" ", strip=True),
            "url": lien["href"]
        })

    donnees = {
        "url_source": url,
        "titre": titre,
        "titres_h1": titres,
        "paragraphes": paragraphes,
        "liens": liens
    }

    return donnees


# Appel de la fonction
resultat = extraire_page("https://example.com")

print("Titre :", resultat["titre"])
print("Paragraphes :", resultat["paragraphes"])
print("Liens :", resultat["liens"])
