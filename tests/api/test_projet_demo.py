"""Le jeu de démonstration produit ce que l'écran Validation lit : de vrais objets, un net, un à regarder, un pas prêt."""
from tests.outils.projet_demo import semer_validation


def test_le_projet_de_demonstration_est_lisible_par_la_validation(client, conn):
    ids = semer_validation(conn)
    v = client.get(f"/api/lots/{ids['lot_id']}/validation").json()
    assert v["resume"] == {"total": 3, "a_valider": 2, "gardes": 0, "jetes": 0, "pas_prets": 1}
    amphore, caisse, lanterne = v["objets"]
    assert (amphore["etat"], caisse["etat"], lanterne["etat"]) == ("a_valider", "a_valider", "en_fabrication")
    assert amphore["verdict"]["etat"] == "ok" and caisse["verdict"]["etat"] == "attention"
    assert amphore["modele"] and [x["nom"] for x in amphore["vues"]] == ["face", "dos", "profil", "trois_quarts", "dessus"]
    assert client.get(amphore["modele"]).status_code == 200 and client.get(amphore["reference"]).status_code == 200


def test_deux_projets_de_demonstration_ne_se_marchent_pas_dessus(client, conn):
    a, b = semer_validation(conn, "Un"), semer_validation(conn, "Deux")
    assert a["lot_id"] != b["lot_id"]
    assert len(client.get(f"/api/lots/{b['lot_id']}/validation").json()["objets"]) == 3
