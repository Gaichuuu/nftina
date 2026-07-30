import json
import pathlib
from scripts.fetch_token_media import infer_missing_genesis

def test_infer_missing_from_contiguous_neighbor_runs():
    manifest = {str(i): {"name": "MZG Hodag", "file": "h.gif"} for i in range(1, 6)}
    manifest.update({str(i): {"name": "MZG Piasa Bird", "file": "p.gif"} for i in range(7, 11)})
    del manifest["4"]
    out = infer_missing_genesis(manifest, total=10)
    assert out == {"4": "MZG Hodag"}

def test_evidence_mapping_well_formed():
    data = json.loads(pathlib.Path("data/evidence/genesis_article_assets.json").read_text())
    assert data["source"]["id"] == "article-38"
    cryptids = data["cryptids"]
    assert len(cryptids) == 17
    assert sum(c["minted"] for c in cryptids) == 875
    manifest_names = {c["manifest_name"] for c in cryptids if c["manifest_name"]}
    assert manifest_names == {"MZG Sinkhole Sam", "MZG River Dino", "MZG Piasa Bird",
                              "MZG Hodag", "MZG Bigfoot", "MZG Chupacabra"}
