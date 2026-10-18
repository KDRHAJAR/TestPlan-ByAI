# Générateur de scénarios de test

Une application web en Python (Streamlit) qui génère des scénarios de test avec Gemini (Google).
Un assistant en six étapes recueille le contexte, puis construit un prompt structuré :

| Étape | Ce que tu saisis | Composant du prompt |
|---|---|---|
| 1. Domaine | Le domaine métier (liste déroulante, ou « Autre ») | Contexte |
| 2. Application | L'explication de l'application | Contexte |
| 3. Données d'entrée | Le texte de la User Story + les maquettes (PNG, JPG, WEBP, GIF) | Données d'entrée |
| 4. Exemples | Facultatif : des scénarios déjà écrits, à imiter (few-shot) | Données d'entrée |
| 5. Format | La forme du résultat (vide = format par défaut) | Format de sortie |
| 6. Génération | Récapitulatif, prompt envoyé, résultat | — |

Le rôle et les contraintes (ne rien inventer, questions pour le PO, traçabilité vers les
critères d'acceptation) sont dans le prompt système, défini dans `app.py`.

## Installation

Python 3.10 ou plus récent.

```bash
pip install -r requirements.txt
```

## Clé API

1. Va sur https://aistudio.google.com et connecte-toi avec un compte Google.
2. Clique sur « Get API key », puis « Create API key ». La clé commence par `AIza`.
3. Définis-la dans le terminal où tu lances l'application :

```bash
# macOS / Linux
export GEMINI_API_KEY="AIza..."
# Windows (PowerShell)
$env:GEMINI_API_KEY="AIza..."
```

Variable facultative : `GEMINI_MODEL` (par défaut `gemini-2.5-flash`, compatible avec le niveau gratuit).

Le niveau gratuit limite le nombre d'appels : en cas de dépassement, l'application affiche
« Quota gratuit de Gemini atteint ». Les données envoyées avec le niveau gratuit peuvent être
consultées par Google : n'y envoie pas de vraies User Stories ni de maquettes confidentielles.

## Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre sur http://localhost:8501.

## Réglages

Dans `app.py` :

- `TEMPERATURE = 0.2` : une valeur basse donne des résultats plus stables.
- `MAX_TOKENS = 8000` : la longueur maximale de la réponse (`max_output_tokens`). Si elle est atteinte, l'application affiche un avertissement.
- `DOMAINES` : la liste des domaines métier proposés.

## Tests

```bash
python -m pytest -q
```

Les tests vérifient la construction du prompt, l'ordre des blocs image et texte, l'appel à
l'API (avec un faux client, sans clé) et le parcours des six pages.
