import os
import pandas as pd
import pytest


# ---------------------------------------------------------
# Import différé du module testé
# ---------------------------------------------------------

def import_pm():
    import sirs_import.relocate as pm
    return pm


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def make_nonconform_gdf(project_dir):
    pm = import_pm()

    """Crée un GDF dont les chemins ne respectent PAS <troncon>/<filename>."""
    img1 = os.path.join(project_dir, "rawA.jpg")
    img2 = os.path.join(project_dir, "rawB.jpg")

    return pd.DataFrame([
        {
            pm.COL_TRONCONS: "T001",
            "obs1_pho1_chemin": "rawA.jpg",
            "obs1_pho1_date": pd.Timestamp("2023-01-10"),
            "obs1_date": pd.Timestamp("2023-01-09"),
        },
        {
            pm.COL_TRONCONS: "T001",
            "obs1_pho2_chemin": "rawB.jpg",
            "obs1_pho2_date": None,
            "obs1_date": pd.Timestamp("2023-01-09"),
        },
    ])


# ============================================================================
# Test intégration : migration KEEP (pas de collisions)
# ============================================================================

def test_integration_keep_no_collision(tmp_path, monkeypatch):
    pm = import_pm()

    # Fake PROJECT_DIR
    monkeypatch.setattr(pm, "PROJECT_DIR", tmp_path)

    # Fake digue name
    monkeypatch.setattr(pm, "DIGUE_NAME", "FAKE")

    # Créer deux photos dummy dans le répertoire racine
    (tmp_path / "rawA.jpg").write_text("AAA")
    (tmp_path / "rawB.jpg").write_text("BBB")

    gdf = make_nonconform_gdf(tmp_path)

    # Simuler que l'utilisateur choisit migration puis continue KEEP
    inputs = iter(["1", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    out = pm.process_photo_migration(gdf.copy())

    # Vérifier que les fichiers ont été déplacés dans /T001
    assert (tmp_path / "T001").exists()

    newA = tmp_path / "T001" / "rawA.jpg"
    newB = tmp_path / "T001" / "rawB.jpg"

    assert newA.exists()
    assert newB.exists()

    assert out.loc[0, "obs1_pho1_chemin"].endswith("T001/rawA.jpg")


# ============================================================================
# Test intégration : collisions → prefix_date
# ============================================================================

def test_integration_prefix_date_collision(tmp_path, monkeypatch):
    pm = import_pm()

    monkeypatch.setattr(pm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pm, "DIGUE_NAME", "FAKE")

    # Deux photos identiques pour collision
    raw = tmp_path / "dup.jpg"
    raw.write_text("DUP")

    gdf = pd.DataFrame([
        {
            pm.COL_TRONCONS: "T001",
            "obs_pho1_chemin": "dup.jpg",
            "obs_pho1_date": pd.Timestamp("2023-05-01"),
            "obs_date": pd.Timestamp("2023-05-01"),
        },
        {
            pm.COL_TRONCONS: "T001",
            "obs_pho2_chemin": "dup.jpg",
            "obs_pho2_date": pd.Timestamp("2023-06-01"),
            "obs_date": pd.Timestamp("2023-06-01"),
        }
    ])

    # simulate: migration → "prefix_date seulement collisions"
    inputs = iter(["1", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    out = pm.process_photo_migration(gdf.copy())

    tdir = tmp_path / "T001"
    assert tdir.exists()

    files = [x.name for x in tdir.iterdir()]
    assert any(f.startswith("20230501_") for f in files)
    assert any(f.startswith("20230601_") for f in files)


# ============================================================================
# Test intégration : collisions → uuid
# ============================================================================

def test_integration_uuid_collision(tmp_path, monkeypatch):
    pm = import_pm()

    monkeypatch.setattr(pm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pm, "DIGUE_NAME", "FAKE")

    # collision
    (tmp_path / "dup.jpg").write_text("DUP")

    gdf = pd.DataFrame([
        {
            pm.COL_TRONCONS: "T001",
            "obs_pho1_chemin": "dup.jpg",
            "obs_pho1_date": None,
            "obs_date": pd.Timestamp("2023-05-10"),
        },
        {
            pm.COL_TRONCONS: "T001",
            "obs_pho2_chemin": "dup.jpg",
            "obs_pho2_date": None,
            "obs_date": pd.Timestamp("2023-05-10"),
        }
    ])

    # simulate: migration → UUID collisions
    inputs = iter(["1", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    out = pm.process_photo_migration(gdf.copy())

    tdir = tmp_path / "T001"
    assert tdir.exists()

    files = [x.name for x in tdir.iterdir()]
    assert len(files) == 2

    for f in files:
        name = f.split(".")[0]
        assert len(name) == 32  # UUID HEX


# ============================================================================
# Test intégration : status conform
# ============================================================================

def test_integration_conform(tmp_path, monkeypatch):
    pm = import_pm()

    monkeypatch.setattr(pm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pm, "DIGUE_NAME", "FAKE")

    # répertoire déjà conforme
    tdir = tmp_path / "T001"
    tdir.mkdir()
    (tdir / "photo.jpg").write_text("OK")

    gdf = pd.DataFrame([
        {
            pm.COL_TRONCONS: "T001",
            "obs_pho1_chemin": "T001/photo.jpg",
            "obs_pho1_date": None,
            "obs_date": None,
        }
    ])

    monkeypatch.setattr(pm, "_diagnose_paths", lambda g: {"status": "conform", "missing": []})

    out = pm.process_photo_migration(gdf.copy())

    assert out is gdf

