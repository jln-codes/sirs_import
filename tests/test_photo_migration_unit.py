import os
import pandas as pd
import pytest
import uuid


# ---------------------------------------------------------
# Fonction utilitaire : importer pm APRÈS conftest.py
# ---------------------------------------------------------

def import_pm():
    import sirs_import.relocate as pm
    return pm


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def make_gdf():
    pm = import_pm()
    return pd.DataFrame([
        {
            pm.COL_TRONCONS: "T001",
            "obs1_pho1_chemin": "img/photoA.jpg",
            "obs1_pho1_date": pd.Timestamp("2023-02-01"),
            "obs1_date": pd.Timestamp("2023-01-20"),
        },
        {
            pm.COL_TRONCONS: "T001",
            "obs1_pho2_chemin": "img/photoA.jpg",
            "obs1_pho2_date": None,
            "obs1_date": pd.Timestamp("2023-01-20"),
        },
    ])


# =========================================================
# _get_effective_photo_date
# =========================================================

def test_get_effective_photo_date_primary():
    pm = import_pm()
    gdf = make_gdf()
    row = gdf.iloc[0]
    d = pm._get_effective_photo_date(row, "obs1_pho1_chemin", pd)
    assert d == pd.Timestamp("2023-02-01")


def test_get_effective_photo_date_fallback_enabled(monkeypatch):
    pm = import_pm()
    gdf = make_gdf()
    row = gdf.iloc[1]

    monkeypatch.setattr(pm, "PHO_FALLBACK_OBS_DATE", True)

    d = pm._get_effective_photo_date(row, "obs1_pho2_chemin", pd)
    assert d == pd.Timestamp("2023-01-20")


def test_get_effective_photo_date_none(monkeypatch):
    pm = import_pm()
    gdf = make_gdf()
    row = gdf.iloc[1]

    monkeypatch.setattr(pm, "PHO_FALLBACK_OBS_DATE", False)

    d = pm._get_effective_photo_date(row, "obs1_pho2_chemin", pd)
    assert d is None


# =========================================================
# _build_target_filename
# =========================================================

def test_build_target_filename_keep():
    pm = import_pm()
    gdf = make_gdf()
    base = "photoA.JPG"

    fname = pm._build_target_filename(
        base, gdf.iloc[0], "obs1_pho1_chemin", "keep", pd
    )

    assert fname.lower().endswith(".jpg")


def test_build_target_filename_prefix_date(monkeypatch):
    pm = import_pm()
    gdf = make_gdf()
    monkeypatch.setattr(pm, "PHO_FALLBACK_OBS_DATE", True)

    fname = pm._build_target_filename(
        "photoA.JPG", gdf.iloc[1], "obs1_pho2_chemin", "prefix_date", pd
    )
    assert fname.startswith("20230120_")


def test_build_target_filename_uuid():
    pm = import_pm()
    gdf = make_gdf()

    fname = pm._build_target_filename(
        "photoA.jpg", gdf.iloc[0], "obs1_pho1_chemin", "uuid", pd
    )

    assert fname.endswith(".jpg")
    assert len(fname.split(".")[0]) == 32  # UUID hex


# =========================================================
# _simulate_relocation
# =========================================================

def test_simulate_relocation_prefix_date():
    pm = import_pm()
    gdf = make_gdf()

    mapping, collisions = pm._simulate_relocation(gdf, "prefix_date")

    assert len(mapping) == 1      # même fichier source
    assert len(collisions) == 1   # collision détectée


# =========================================================
# _generate_target_mapping
# =========================================================

def test_generate_target_mapping_coherence():
    pm = import_pm()
    gdf = make_gdf()

    sim_mapping, sim_collisions = pm._simulate_relocation(gdf, "prefix_date")

    mapping2 = pm._generate_target_mapping(
        gdf,
        sim_collisions,
        strategy_for_collisions="prefix_date",
        strategy_other="keep",
    )

    for _, dests in mapping2.items():
        for d in dests:
            assert ("2023" in d) or ("00000000" in d)


# =========================================================
# _update_gdf
# =========================================================

def test_update_gdf(monkeypatch):
    pm = import_pm()
    gdf = make_gdf()

    monkeypatch.setattr(pm, "PROJECT_DIR", "/tmp/FAKE")

    mapping = {
        os.path.abspath("img/photoA.jpg"): [
            os.path.abspath("/tmp/FAKE/T001/newA.jpg")
        ]
    }

    gdf2 = pm._update_gdf(gdf.copy(), mapping)

    assert gdf2.loc[0, "obs1_pho1_chemin"].endswith("T001/newA.jpg")


# =========================================================
# _apply_relocation
# =========================================================

def test_apply_relocation(tmp_path):
    pm = import_pm()

    src = tmp_path / "photoX.jpg"
    src.write_text("dummy-image-content")

    dst = tmp_path / "T001" / "final.jpg"

    mapping = {str(src): [str(dst)]}

    pm._apply_relocation(mapping)

    assert dst.exists()
    assert not src.exists()


# =========================================================
# process_photo_migration – cas conform
# =========================================================

def test_process_photo_migration_conform(monkeypatch):
    pm = import_pm()
    gdf = make_gdf()

    monkeypatch.setattr(pm, "_diagnose_paths", lambda g: {"status": "conform", "missing": []})

    out = pm.process_photo_migration(gdf)

    assert out is gdf

