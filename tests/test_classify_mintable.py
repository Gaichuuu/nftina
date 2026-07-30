from scripts.classify_mintable import is_mzg, cryptid_of, summarize_counts

def test_is_mzg_prefix_rules():
    assert is_mzg("MZG Mothman") is True
    assert is_mzg("mzg squonk") is True          # case-insensitive
    assert is_mzg(" MZG Hodag") is True          # leading space tolerated
    assert is_mzg("Squonk Baby") is False
    assert is_mzg("MZGX Fake") is False          # must be the word MZG, not a prefix of one
    assert is_mzg(None) is False
    assert is_mzg("") is False

def test_cryptid_of_strips_prefix_and_numbering():
    assert cryptid_of("MZG Mothman") == "Mothman"
    assert cryptid_of("MZG Sewer Gator #12") == "Sewer Gator"
    assert cryptid_of("Squonk Baby") is None     # non-MZG → no cryptid
    assert cryptid_of(None) is None

def test_summarize_counts_mzg_only():
    tokens = {
        "1": {"name": "MZG Mothman", "mzg": True},
        "2": {"name": "MZG Mothman", "mzg": True},
        "3": {"name": "MZG Hodag", "mzg": True},
        "4": {"name": "Squonk Baby", "mzg": False},
    }
    assert summarize_counts(tokens) == {"Mothman": 2, "Hodag": 1}
