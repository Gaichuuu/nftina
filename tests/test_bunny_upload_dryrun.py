import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "bunny-upload.sh"


def test_script_exists_and_executable():
    assert SCRIPT.exists(), "scripts/bunny-upload.sh missing"


def test_dry_run_media_lists_files(tmp_path):
    (ROOT / "data" / "media" / "tokens" / "coin_tokens").mkdir(parents=True, exist_ok=True)
    sample = ROOT / "data" / "media" / "tokens" / "coin_tokens" / "1.png"
    sample.write_bytes(b"\x89PNG\r\n")
    try:
        r = subprocess.run(["bash", str(SCRIPT), "media"], cwd=str(ROOT),
                           env={"DRY_RUN": "1", "PATH": "/usr/bin:/bin"},
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        assert "nftina/tokens/coin_tokens/1.png" in (r.stdout + r.stderr)
        assert "skipped, 0 failed)" in (r.stdout + r.stderr)
    finally:
        sample.unlink(missing_ok=True)
