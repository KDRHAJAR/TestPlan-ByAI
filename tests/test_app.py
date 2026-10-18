from pathlib import Path
from types import SimpleNamespace

from google.genai import errors, types
from streamlit.testing.v1 import AppTest

import app

CHEMIN_APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_prompt_contient_les_composants_et_les_donnees():
    prompt = app.construire_prompt_utilisateur(
        "Gestion des tickets", "POSA vend des tickets.", "US-55 : vendre un ticket", "", "Liste simple"
    )
    for section in ["[CONTEXTE]", "[INSTRUCTIONS]", "[DONNÉES D'ENTRÉE]", "[FORMAT DE SORTIE]"]:
        assert section in prompt
    assert "Gestion des tickets" in prompt
    assert "US-55 : vendre un ticket" in prompt
    assert "Liste simple" in prompt
    assert "[EXEMPLES]" not in prompt


def test_prompt_ajoute_les_exemples_et_le_format_par_defaut():
    prompt = app.construire_prompt_utilisateur("Paiement", "App", "US", "TC-01 | Exemple", "  ")
    assert "[EXEMPLES]" in prompt and "TC-01 | Exemple" in prompt
    assert app.FORMAT_PAR_DEFAUT in prompt


def test_prompt_sans_texte_renvoie_aux_maquettes():
    prompt = app.construire_prompt_utilisateur("Paiement", "App", "", "", "")
    assert "Voir les maquettes jointes." in prompt


def test_contenu_place_les_images_avant_le_texte():
    contenu = app.construire_contenu("mon prompt", [("maquette.png", "image/png", b"abc")])
    assert contenu[0].inline_data.data == b"abc"
    assert contenu[0].inline_data.mime_type == "image/png"
    assert contenu[-1].text == "mon prompt"


class FauxClient:
    def __init__(self, finish_reason=types.FinishReason.STOP):
        self.appel = None
        self.models = self
        self.finish_reason = finish_reason

    def generate_content(self, **kwargs):
        self.appel = kwargs
        return SimpleNamespace(
            text="| ID | Titre |",
            candidates=[SimpleNamespace(finish_reason=self.finish_reason)],
        )


def test_generer_envoie_prompt_systeme_et_temperature():
    client = FauxClient()
    texte, coupe = app.generer(["x"], client=client)
    assert texte == "| ID | Titre |"
    assert coupe is False
    config = client.appel["config"]
    assert config.system_instruction == app.PROMPT_SYSTEME
    assert config.temperature == app.TEMPERATURE
    assert config.max_output_tokens == app.MAX_TOKENS
    assert client.appel["model"] == app.MODELE


def test_generer_signale_une_reponse_coupee():
    _texte, coupe = app.generer(["x"], client=FauxClient(types.FinishReason.MAX_TOKENS))
    assert coupe is True


def test_message_erreur_quota_gratuit():
    erreur = errors.APIError(429, {"error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}})
    assert "Quota gratuit" in app.message_erreur(erreur)


def test_message_erreur_autre():
    erreur = errors.APIError(400, {"error": {"code": 400, "message": "Bad request", "status": "INVALID_ARGUMENT"}})
    assert app.message_erreur(erreur).startswith("L'appel à Gemini a échoué")


def test_parcours_complet_des_pages():
    at = AppTest.from_file(CHEMIN_APP).run()
    assert not at.exception
    assert at.title[0].value == "Générateur de scénarios de test"

    suivant = [b for b in at.button if b.label == "Suivant"][0]
    suivant.click().run()
    assert at.session_state.etape == 1

    # Bloqué tant que l'application n'est pas décrite
    [b for b in at.button if b.label == "Suivant"][0].click().run()
    assert at.session_state.etape == 1
    assert "Décris l'application" in at.warning[0].value

    at.text_area(key="explication").input("POSA vend des tickets.").run()
    [b for b in at.button if b.label == "Suivant"][0].click().run()
    at.text_area(key="user_story").input("US-55").run()
    for _ in range(3):
        [b for b in at.button if b.label == "Suivant"][0].click().run()
    assert at.session_state.etape == 5
    assert at.session_state.explication == "POSA vend des tickets."  # conservé entre les pages
    assert any(b.label == "Générer les scénarios de test" for b in at.button)
