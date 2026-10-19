"""Le contrat interface/API figé dans web/src/test/contrat.json est à jour."""
import json

from tests.api.contrat_web import CHEMIN_CONTRAT, generer


def test_contrat_web_a_jour():
    assert CHEMIN_CONTRAT.exists(), "régénère avec : python -m tests.api.contrat_web --ecrire"
    attendu = json.loads(CHEMIN_CONTRAT.read_text(encoding="utf-8"))
    obtenu = generer()
    assert obtenu == attendu, "le contrat a changé : régénère avec `python -m tests.api.contrat_web --ecrire`"


def test_contrat_couvre_la_cloche_et_le_menu():
    c = generer()
    assert set(c["GET /api/notifications"]) == {"notifications", "non_lues"}
    assert c["GET /api/notifications#rempli"]["non_lues"] == 1
    assert c["GET /api/menu#rempli"]["badges"] == {"lots": 3, "bibliotheque": 2, "generateurs": 1}
    assert c["GET /api/menu#rempli"]["credits"]["utilises"] == 60
    assert "secret" not in json.dumps(c)
