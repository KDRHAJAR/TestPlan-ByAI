"""Générateur de scénarios de test : un assistant en 6 pages qui construit un prompt
structuré (rôle, contexte, instructions, données d'entrée, contraintes, format)
et l'envoie à Gemini."""

import os
import re

import streamlit as st
from google import genai
from google.genai import errors, types

MODELE = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_TOKENS = 8000
TEMPERATURE = 0.2

DOMAINES = [
    "Jeux de loterie FastPlay",
    "Configuration des jeux (KBO)",
    "Vente en point de vente (POSA)",
    "Paiement",
    "Gestion des tickets",
    "Autre",
]
ETAPES = ["Domaine", "Application", "Données d'entrée", "Exemples", "Format", "Génération"]
FORMAT_PAR_DEFAUT = (
    "Un tableau avec les colonnes : ID | Titre | Objectif | Préconditions | Étapes | "
    "Résultat attendu | Critères couverts | Criticité (Haute, Moyenne, Basse)."
)
TYPES_IMAGES = ["png", "jpg", "jpeg", "webp", "gif"]
CHAMPS = ["domaine", "domaine_autre", "explication", "user_story", "exemples", "format_sortie"]

PROMPT_SYSTEME = """Tu es un testeur fonctionnel expérimenté, certifié ISTQB.
Tu conçois des scénarios de test à partir de la base de test qu'on te fournit.

Règles à respecter :
- Base-toi uniquement sur les informations fournies. N'invente aucune règle métier.
- Si une information manque ou est ambiguë, ajoute-la à une section « Questions pour le PO ».
- Si la User Story et la maquette se contredisent, signale l'écart dans une section « Écarts constatés ».
- Couvre les cas passants et non passants.
- Chaque scénario indique les critères d'acceptation qu'il couvre, et chaque critère est couvert au moins une fois.
- Réponds en français."""


def construire_prompt_utilisateur(domaine, explication, user_story, exemples, format_sortie):
    sections = [
        f"[CONTEXTE]\nDomaine métier : {domaine}\nApplication : {explication.strip()}",
        "[INSTRUCTIONS]\nAnalyse la base de test ci-dessous (User Story et maquettes jointes, s'il y en a), "
        "puis génère les scénarios de test fonctionnels.",
        f"[DONNÉES D'ENTRÉE]\n{user_story.strip() or 'Voir les maquettes jointes.'}",
    ]
    if exemples.strip():
        sections.append(
            "[EXEMPLES]\nVoici des exemples du résultat attendu. Respecte le même style et le même niveau de détail :\n"
            + exemples.strip()
        )
    sections.append(f"[FORMAT DE SORTIE]\n{format_sortie.strip() or FORMAT_PAR_DEFAUT}")
    return "\n\n".join(sections)


def construire_contenu(texte, images):
    """Les images (maquettes) d'abord, puis le texte : chaque élément est une « part » typée."""
    parts = [types.Part.from_bytes(data=donnees, mime_type=media_type) for _nom, media_type, donnees in images]
    parts.append(types.Part.from_text(text=texte))
    return parts


def generer(contenu, client=None):
    """Renvoie (texte généré, réponse coupée par la limite de tokens ?)."""
    client = client or genai.Client()
    reponse = client.models.generate_content(
        model=MODELE,
        contents=contenu,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_SYSTEME,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
        ),
    )
    coupe = bool(reponse.candidates) and reponse.candidates[0].finish_reason == types.FinishReason.MAX_TOKENS
    return reponse.text or "", coupe


BALISE_BR_NEUTRALISEE = re.compile(r"&lt;br\s*/?>", re.IGNORECASE)
CELLULE_CRITICITE = re.compile(r"\|\s*\**\s*(Haute|Moyenne|Basse)\s*\**\s*(?=\|)", re.IGNORECASE)


def preparer_affichage(texte):
    """Neutralise le HTML écrit par l'IA (sauf les retours à la ligne <br>),
    puis transforme la criticité des tableaux en pastilles."""
    texte = BALISE_BR_NEUTRALISEE.sub("<br>", texte.replace("<", "&lt;"))
    return CELLULE_CRITICITE.sub(
        lambda m: f'| <span class="crit crit-{m.group(1).lower()}">{m.group(1).capitalize()}</span> ', texte
    )


def message_erreur(erreur):
    if erreur.code == 429:
        return ("Quota gratuit de Gemini atteint (trop d'appels sur une courte période ou limite du jour). "
                "Attends quelques minutes, puis réessaie.")
    return f"L'appel à Gemini a échoué : {erreur}"


# ---------------------------------------------------------------- interface

STYLE = """
<style>
.block-container { max-width: 1100px; padding-top: 3rem; }
h1 { font-size: 3rem !important; line-height: 1.05 !important; letter-spacing: 0.005em; }
.intro { color: #7A6559; font-weight: 300; font-size: 1.05rem; margin: -0.4rem 0 2.2rem; }

.etapes { display: flex; gap: 0.5rem; margin: 0 0 2.4rem; flex-wrap: wrap; }
.etape {
    flex: 1 1 0; min-width: 96px; padding: 0.6rem 0.2rem 0.4rem;
    border-top: 2px solid #E3D2C8; color: #A8948A; font-size: 0.8rem; text-align: center;
}
.etape .num { display: block; font-family: "Cormorant Garamond", Georgia, serif; font-size: 1.35rem; line-height: 1.2; }
.etape.faite { border-top-color: #C9A99A; color: #7A6559; }
.etape.active { border-top-color: #9C7B6B; color: #3D2E27; font-weight: 500; }

[data-testid="stVerticalBlockBorderWrapper"] { background: #FBF6F3; }

.stMarkdown table {
    display: block; overflow-x: auto; max-width: 100%;
    border-collapse: collapse; font-size: 0.86rem; line-height: 1.45; margin: 0.6rem 0 1.4rem;
}
.stMarkdown thead th {
    background: #EBD9D0; color: #3D2E27; font-weight: 600; text-align: left;
    border: none; border-bottom: 1px solid #D9C2B5; padding: 0.65rem 0.8rem; white-space: nowrap;
}
.stMarkdown tbody td {
    vertical-align: top; border: none; border-bottom: 1px solid #EADBD2;
    padding: 0.65rem 0.8rem; min-width: 110px;
}
.stMarkdown tbody td:first-child { white-space: nowrap; font-weight: 500; min-width: 0; }
.stMarkdown tbody tr:nth-child(even) { background: #F8F0EB; }

.crit {
    display: inline-block; padding: 0.15rem 0.65rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 500; white-space: nowrap;
}
.crit-haute { background: #E9C4B5; color: #6B2E1F; }
.crit-moyenne { background: #EEDDB8; color: #5E4714; }
.crit-basse { background: #D3DFCC; color: #33482A; }
</style>
"""


def initialiser_etat():
    st.session_state.setdefault("etape", 0)
    st.session_state.setdefault("images", [])
    st.session_state.setdefault("resultat", None)
    for champ in CHAMPS:
        st.session_state.setdefault(champ, "")
        # Réassigner la clé empêche Streamlit d'effacer le champ quand on change de page.
        st.session_state[champ] = st.session_state[champ]
    if not st.session_state.domaine:
        st.session_state.domaine = DOMAINES[0]


def domaine_choisi():
    s = st.session_state
    return s.domaine_autre.strip() if s.domaine == "Autre" else s.domaine


def afficher_etapes():
    blocs = []
    for i, nom in enumerate(ETAPES):
        classe = "active" if i == st.session_state.etape else "faite" if i < st.session_state.etape else ""
        blocs.append(f'<div class="etape {classe}"><span class="num">{i + 1}</span>{nom}</div>')
    st.markdown(f'<div class="etapes">{"".join(blocs)}</div>', unsafe_allow_html=True)


def manque_pour_continuer():
    s = st.session_state
    if s.etape == 0 and s.domaine == "Autre" and not s.domaine_autre.strip():
        return "Indique le nom de ton domaine métier."
    if s.etape == 1 and not s.explication.strip():
        return "Décris l'application en quelques phrases."
    if s.etape == 2 and not s.user_story.strip() and not s.images:
        return "Ajoute le texte de la User Story ou au moins une maquette."
    return None


def page_domaine():
    st.subheader("Dans quel domaine métier travailles-tu ?")
    st.selectbox("Domaine", DOMAINES, key="domaine")
    if st.session_state.domaine == "Autre":
        st.text_input("Nom du domaine", key="domaine_autre", placeholder="Ex. : Fidélité client")


def page_application():
    st.subheader("Que fait l'application ?")
    st.text_area(
        "Explication",
        key="explication",
        height=200,
        placeholder="Ex. : FastPlay comprend deux applications. KBO sert à créer et configurer les jeux "
        "et leurs icônes. POSA vend les tickets aux joueurs et les imprime.",
    )


def page_donnees():
    st.subheader("Base de test")
    st.text_area(
        "User Story et critères d'acceptation",
        key="user_story",
        height=220,
        placeholder="Colle ici le texte de la User Story. Le texte est lu plus fidèlement qu'une capture d'écran.",
    )
    fichiers = st.file_uploader(
        "Maquettes (export PNG ou JPG depuis Figma)",
        type=TYPES_IMAGES,
        accept_multiple_files=True,
        key="televersement",
    )
    if fichiers:
        st.session_state.images = [(f.name, f.type, f.getvalue()) for f in fichiers]
    if st.session_state.images:
        st.caption(f"{len(st.session_state.images)} maquette(s) jointe(s)")
        st.image([donnees for _n, _t, donnees in st.session_state.images], width=160)
        if st.button("Retirer les maquettes"):
            st.session_state.images = []
            st.rerun()


def page_exemples():
    st.subheader("Exemples de résultat (facultatif)")
    st.write("Montre un ou deux scénarios déjà écrits dans ton style : le résultat les imitera.")
    st.text_area(
        "Exemples",
        key="exemples",
        height=220,
        placeholder="Ex. : POSA-TC-01 | Vente d'un ticket standard | Objectif : vérifier qu'un vendeur "
        "peut vendre et imprimer un ticket valide | Criticité : Haute",
    )


def page_format():
    st.subheader("Sous quelle forme veux-tu le résultat ?")
    st.text_area(
        "Format de sortie",
        key="format_sortie",
        height=160,
        placeholder=FORMAT_PAR_DEFAUT,
        help="Laisse vide pour utiliser le format proposé.",
    )


def page_generation():
    s = st.session_state
    st.subheader("Récapitulatif")
    st.markdown(
        f"**Domaine** : {domaine_choisi()}  \n"
        f"**Maquettes** : {len(s.images)}  \n"
        f"**Exemples** : {'oui' if s.exemples.strip() else 'non'}  \n"
        f"**Format** : {s.format_sortie.strip() or 'format proposé par défaut'}"
    )
    prompt = construire_prompt_utilisateur(
        domaine_choisi(), s.explication, s.user_story, s.exemples, s.format_sortie
    )
    with st.expander("Voir le prompt envoyé"):
        st.code(f"[PROMPT SYSTÈME]\n{PROMPT_SYSTEME}\n\n[PROMPT UTILISATEUR]\n{prompt}", language=None)

    if st.button("Générer les scénarios de test", type="primary"):
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            st.error("Clé API introuvable. Définis la variable d'environnement GEMINI_API_KEY, puis relance l'application.")
            return
        with st.spinner("Génération des scénarios en cours…"):
            try:
                s.resultat = generer(construire_contenu(prompt, s.images))
            except errors.APIError as erreur:
                st.error(message_erreur(erreur))
                return

    if s.resultat:
        texte, coupe = s.resultat
        if not texte:
            st.warning("Gemini n'a renvoyé aucun texte. Relance la génération ou réduis la taille des entrées.")
        if coupe:
            st.warning("La réponse a été coupée (limite max_tokens atteinte). Réduis le périmètre ou augmente MAX_TOKENS.")
        with st.container(border=True):
            st.markdown(preparer_affichage(texte), unsafe_allow_html=True)
        st.caption("Vérifie chaque scénario avant de l'utiliser : l'IA peut se tromper ou inventer.")


PAGES = [page_domaine, page_application, page_donnees, page_exemples, page_format, page_generation]


def main():
    st.set_page_config(page_title="Générateur de scénarios de test", page_icon="🧾", layout="centered")
    st.markdown(STYLE, unsafe_allow_html=True)
    initialiser_etat()

    st.title("Générateur de scénarios de test")
    st.markdown(
        '<p class="intro">Décris ton contexte en six étapes, puis laisse Gemini rédiger les scénarios.</p>',
        unsafe_allow_html=True,
    )
    afficher_etapes()
    PAGES[st.session_state.etape]()

    st.write("")
    precedent, _, suivant = st.columns([1, 2, 1])
    if st.session_state.etape > 0 and precedent.button("Précédent", use_container_width=True):
        st.session_state.etape -= 1
        st.rerun()
    if st.session_state.etape < len(ETAPES) - 1 and suivant.button("Suivant", type="primary", use_container_width=True):
        message = manque_pour_continuer()
        if message:
            st.warning(message)
        else:
            st.session_state.etape += 1
            st.rerun()


if __name__ == "__main__":
    main()