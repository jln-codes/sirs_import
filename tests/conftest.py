import pytest
import types


@pytest.fixture(autouse=True)
def fake_config_loader(monkeypatch):
    """
    Charge un faux module sirs_import.config_loader contenant
    TOUTES les clés du DEFAULTS original, pour éviter tout KeyError
    dans helpers.py, relocate.py, ou d'autres modules.
    """

    fake = types.ModuleType("sirs_import.config_loader")

    # Reprise exacte des DEFAULTS originaux
    CONFIG = {
        "COUCH_URL": "",
        "COUCH_DB": "",
        "COUCH_USER": "",
        "COUCH_PW": "",

        "GPKG_FILE": "",
        "GPKG_LAYER": "",
        "COL_TRONCONS": "troncon",        # requis par tests migration
        "COL_LINEAR_ID": "",
        "COL_AUTHOR": "",
        "COL_DATE_DEBUT": "",
        "COL_DATE_FIN": "",
        "COL_DESIGNATION": "designation",
        "COL_LIBELLE": "libelle",
        "COL_COMMENTAIRE": "",
        "COL_LIEUDIT": "",
        "COL_POSITION_ID": "",
        "COL_COTE_ID": "",
        "COL_SOURCE_ID": "",
        "COL_CATEGORIE_DESORDRE_ID": "",
        "COL_TYPE_DESORDRE_ID": "",

        "IS_VALID": False,

        "OBS_FALLBACK_OBSERVATEUR_ID": "",
        "OBS_FALLBACK_NB_DESORDRES": "",
        "OBS_FALLBACK_URGENCE": "",
        "OBS_FALLBACK_SUITE": "",

        "PHO_FALLBACK_PHOTOGRAPH_ID": "",
        "PHO_FALLBACK_OBS_DATE": True,    # utile aux tests
        "PHO_FALLBACK_DES_GEOM": False,
        "PHO_FALLBACK_ORIENTATION": "",
        "PHO_FALLBACK_COTE": "",

        "VERBOSE": False,

        "GPKG_PATH": None,
    }

    fake.CONFIG = CONFIG

    # Valeurs simulées nécessaires au comportement de relocate.py
    fake.PROJECT_DIR = "/tmp"
    fake.DIGUE_NAME = "FAKE"

    # Simuler load_config
    fake.load_config = lambda: ("/tmp/config.toml", CONFIG)

    # Évite les sys.exit
    fake.sys = types.SimpleNamespace(exit=lambda code: None)

    # Injection dans sys.modules
    monkeypatch.setitem(
        __import__("sys").modules,
        "sirs_import.config_loader",
        fake
    )

    yield

