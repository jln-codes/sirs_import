import pytest
import pandas as pd
from shapely.geometry import Point, LineString


def import_diag():
    import sirs_import.diag_des as dm
    return dm


def _rows_dict(rows):
    return {r[0]: r for r in rows}


# =====================================================================
# TEXT COLUMNS
# =====================================================================

def test_diag_text_columns_all_present(monkeypatch):
    dm = import_diag()

    # config des colonnes texte
    monkeypatch.setattr(dm, "COL_DESIGNATION", "designation")
    monkeypatch.setattr(dm, "COL_LIBELLE", "libelle")
    monkeypatch.setattr(dm, "COL_COMMENTAIRE", "commentaire")
    monkeypatch.setattr(dm, "COL_LIEUDIT", "lieuDit")

    # neutralisation du bruit
    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "designation": ["aaa"],
        "libelle": ["bbb"],
        "commentaire": ["ccc"],
        "lieuDit": ["ddd"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    R = _rows_dict(rows)

    assert R["designation"][2] == "colonne GPKG"
    assert R["libelle"][2] == "colonne GPKG"
    assert R["commentaire"][2] == "colonne GPKG"
    assert R["lieuDit"][2] == "colonne GPKG"
    assert errors == []


def test_diag_text_columns_missing(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_DESIGNATION", "")
    monkeypatch.setattr(dm, "COL_LIBELLE", "")
    monkeypatch.setattr(dm, "COL_COMMENTAIRE", "")
    monkeypatch.setattr(dm, "COL_LIEUDIT", "")

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({"geometry": [Point(0, 0)]})

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    R = _rows_dict(rows)

    assert R["designation"][2] == "non défini"
    assert R["libelle"][2] == "non défini"
    assert R["commentaire"][2] == "non défini"
    assert R["lieuDit"][2] == "non défini"
    assert errors == []


# =====================================================================
# LINEAR ID
# =====================================================================

def test_linear_id_valid_column(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        dm.COL_LINEAR_ID: ["11111111-1111-1111-1111-111111111111"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    R = _rows_dict(rows)
    assert R["linearId"][4] == "oui"
    assert errors == []


def test_linear_id_invalid_uuid(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        dm.COL_LINEAR_ID: ["INVALID"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    assert len(errors) == 1


def test_linear_id_fallback_uuid(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_LINEAR_ID", "22222222-2222-2222-2222-222222222222")
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({"geometry": [Point(1, 1)]})

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=["geometry"],
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    R = _rows_dict(rows)
    assert R["linearId"][4] == "oui"
    assert errors == []


# =====================================================================
# AUTHOR
# =====================================================================

def test_author_from_column(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_AUTHOR", "author_col")
    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "author_col": ["11111111-1111-1111-1111-111111111111"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=["11111111-1111-1111-1111-111111111111"],
    )

    R = _rows_dict(rows)
    assert R["author"][4] == "oui"
    assert errors == []


def test_author_invalid_sirs(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_AUTHOR", "author_col")
    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "author_col": ["11111111-1111-1111-1111-111111111111"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],  # inconnu
    )

    assert len(errors) == 1


# =====================================================================
# SOURCE
# =====================================================================

def test_source_column_valid(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_SOURCE_ID", "src")
    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "src": ["RefSource:2"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    R = _rows_dict(rows)
    assert R["sourceId"][4] == "oui"
    assert errors == []


def test_source_invalid(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_SOURCE_ID", "src")
    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "src": ["BAD_CODE"],
        "geometry": [Point(0, 0)],
    })

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    assert len(errors) == 1


# =====================================================================
# GEOMETRY
# =====================================================================

def test_geometry_point(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({"geometry": [Point(0, 0)]})

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=["geometry"],
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[],
    )

    R = _rows_dict(rows)

    assert "positionDebut" in R
    assert "positionFin" in R
    assert errors == []


def test_geometry_linestring_accept(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({"geometry": [LineString([(0, 0), (1, 1), (2, 2)])]})

    monkeypatch.setattr("builtins.input", lambda _: "1")

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=["geometry"],
        gdf=gdf,
        gpkg_schema={"geometry": "LINESTRING"},
        user_ids=[],
    )

    R = _rows_dict(rows)
    assert "positionDebut" in R
    assert "positionFin" in R
    assert errors == []


def test_geometry_linestring_cancel(monkeypatch):
    dm = import_diag()
    from sirs_import.exceptions import UserCancelled

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)

    gdf = pd.DataFrame({"geometry": [LineString([(0, 0), (1, 1), (2, 2)])]})

    monkeypatch.setattr("builtins.input", lambda _: "2")

    with pytest.raises(UserCancelled):
        dm.diagnose_mapping(
            available_cols=["geometry"],
            gdf=gdf,
            gpkg_schema={"geometry": "LINESTRING"},
            user_ids=[],
        )


# =====================================================================
# DATES
# =====================================================================

def test_dates_valid(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_DATE_DEBUT", "date_debut")
    monkeypatch.setattr(dm, "COL_DATE_FIN", "date_fin")

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "date_debut": [pd.Timestamp("2023-01-01")],
        "date_fin": [pd.Timestamp("2023-01-10")],
        "geometry": [Point(0, 0)],
    })

    schema = {"date_debut": "date", "date_fin": "date", "geometry": "POINT"}

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema=schema,
        user_ids=[]
    )

    assert errors == []


def test_dates_inconsistent(monkeypatch):
    dm = import_diag()

    monkeypatch.setattr(dm, "COL_DATE_DEBUT", "date_debut")
    monkeypatch.setattr(dm, "COL_DATE_FIN", "date_fin")

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_text_columns", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "date_debut": [pd.Timestamp("2023-01-10")],
        "date_fin": [pd.Timestamp("2023-01-01")],
        "geometry": [Point(0, 0)],
    })

    schema = {"date_debut": "date", "date_fin": "date", "geometry": "POINT"}

    rows, errors, warnings = dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema=schema,
        user_ids=[]
    )

    assert len(errors) >= 1
    assert any("date_fin" in err or "< date_debut" in err for err in errors)


# =====================================================================
# USED COLUMNS
# =====================================================================

def test_used_columns_tracking(monkeypatch):
    dm = import_diag()

    dm.USED_COLUMNS.clear()

    monkeypatch.setattr(dm, "COL_DESIGNATION", "designation_col")
    monkeypatch.setattr(dm, "COL_LIBELLE", "")
    monkeypatch.setattr(dm, "COL_COMMENTAIRE", "")
    monkeypatch.setattr(dm, "COL_LIEUDIT", "")

    monkeypatch.setattr(dm, "_diag_linear_id", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_dates", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_author", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_type_desordre", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_categorie_desordre", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_position", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_source", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_cote", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_diag_geometry", lambda *a, **k: None)

    gdf = pd.DataFrame({
        "designation_col": ["x"],
        "geometry": [Point(0, 0)],
    })

    dm.diagnose_mapping(
        available_cols=list(gdf.columns),
        gdf=gdf,
        gpkg_schema={"geometry": "POINT"},
        user_ids=[]
    )

    assert "designation_col" in dm.USED_COLUMNS

