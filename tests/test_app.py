import os
import sys
import tempfile

os.environ["ANNOTATION_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402

from annotation import quantum  # noqa: E402
from annotation.metrics import cohen_kappa  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_tem_contatos_e_abas(client):
    html = client.get("/").get_data(as_text=True)
    for txt in ["inforpop.com", "wa.me/5521999618643", "inforpop@hotmail.com",
                "pedro-paulo-ribeiro-pcd-1451498", "Computação Clássica",
                "Computação Quântica", "anexo.png"]:
        assert txt in html


def test_fluxo_de_anotacao(client):
    for domain in ("classical", "quantum"):
        nxt = client.get(f"/api/{domain}/next?annotator=t").get_json()
        item = nxt["item"]
        r = client.post(f"/api/{domain}/annotate",
                        json={"item_id": item["id"], "label": item["suggestion"],
                              "annotator": "t", "seconds": 2})
        assert r.status_code == 200 and r.get_json()["saved"]
        stats = client.get(f"/api/{domain}/stats?annotator=t").get_json()
        assert stats["annotations"] == 1
        assert client.get(f"/api/{domain}/export.csv").status_code == 200


def test_label_invalido(client):
    r = client.post("/api/classical/annotate", json={"item_id": "c01", "label": "xpto"})
    assert r.status_code == 400


def test_estados_quanticos():
    assert quantum.ITEMS["q01"]["gold"] == "emaranhado"     # Bell
    assert quantum.ITEMS["q04"]["gold"] == "superposição"   # H no alvo
    assert quantum.ITEMS["q09"]["gold"] == "base"           # HH = I
    assert abs(sum(quantum.ITEMS["q07"]["probs"].values()) - 1) < 1e-3


def test_kappa():
    assert cohen_kappa(list("aabb"), list("aabb"), ["a", "b"]) == 1.0
    assert cohen_kappa(list("abab"), list("baba"), ["a", "b"]) == -1.0
