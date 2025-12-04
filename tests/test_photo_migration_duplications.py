import pandas as pd


# ---------------------------------------------------------
# Import différé du module testé
# ---------------------------------------------------------

def import_pm():
    import sirs_import.relocate as pm
    return pm


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _mk(cat):
    pm = import_pm()

    if cat == 1:
        # cat1 : même observation, plusieurs colonnes photo pointent vers la même image
        return pd.DataFrame([
            {
                pm.COL_TRONCONS: "T001",
                pm.COL_DESIGNATION: "D1",
                "obs1_pho1_chemin": "same.jpg",
                "obs1_pho2_chemin": "same.jpg",
            }
        ])

    if cat == 2:
        # cat2 : même désordre, deux observations différentes, même tronçon
        return pd.DataFrame([
            {
                pm.COL_TRONCONS: "T001",
                pm.COL_DESIGNATION: "D1",
                "obs1_pho1_chemin": "same.jpg",
            },
            {
                pm.COL_TRONCONS: "T001",
                pm.COL_DESIGNATION: "D1",
                "obs2_pho1_chemin": "same.jpg",
            }
        ])

    if cat == 3:
        # cat3 : même tronçon, désordres différents
        return pd.DataFrame([
            {
                pm.COL_TRONCONS: "T001",
                pm.COL_DESIGNATION: "D1",
                "obs1_pho1_chemin": "same.jpg",
            },
            {
                pm.COL_TRONCONS: "T001",
                pm.COL_DESIGNATION: "D2",
                "obs2_pho1_chemin": "same.jpg",
            }
        ])

    if cat == 4:
        # cat4 : tronçons différents, même image réutilisée
        return pd.DataFrame([
            {
                pm.COL_TRONCONS: "T001",
                pm.COL_DESIGNATION: "D1",
                "obs1_pho1_chemin": "same.jpg",
            },
            {
                pm.COL_TRONCONS: "T002",
                pm.COL_DESIGNATION: "D2",
                "obs2_pho1_chemin": "same.jpg",
            }
        ])

    raise ValueError("Invalid category")


# =========================================================
# cat1
# =========================================================

def test_duplication_cat1():
    pm = import_pm()
    gdf = _mk(1)

    refmap = pm.collect_photo_references(gdf)
    cat1, cat2, cat3, cat4 = pm._classify_duplications(refmap)

    assert len(cat1) == 1
    assert len(cat2) == 0
    assert len(cat3) == 0
    assert len(cat4) == 0


# =========================================================
# cat2
# =========================================================

def test_duplication_cat2():
    pm = import_pm()
    gdf = _mk(2)

    refmap = pm.collect_photo_references(gdf)
    cat1, cat2, cat3, cat4 = pm._classify_duplications(refmap)

    assert len(cat1) == 0
    assert len(cat2) == 1
    assert len(cat3) == 0
    assert len(cat4) == 0


# =========================================================
# cat3
# =========================================================

def test_duplication_cat3():
    pm = import_pm()
    gdf = _mk(3)

    refmap = pm.collect_photo_references(gdf)
    cat1, cat2, cat3, cat4 = pm._classify_duplications(refmap)

    assert len(cat1) == 0
    assert len(cat2) == 0
    assert len(cat3) == 1
    assert len(cat4) == 0


# =========================================================
# cat4
# =========================================================

def test_duplication_cat4():
    pm = import_pm()
    gdf = _mk(4)

    refmap = pm.collect_photo_references(gdf)
    cat1, cat2, cat3, cat4 = pm._classify_duplications(refmap)

    assert len(cat1) == 0
    assert len(cat2) == 0
    assert len(cat3) == 0
    assert len(cat4) == 1

