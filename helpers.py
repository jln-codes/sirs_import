# -*- coding: utf-8 -*-
import re
import sys
import datetime
import importlib
import subprocess
import unicodedata
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    TYPE_CHECKING,
)

from .exceptions import GpkgReadError, DataValidationError
from .config_loader import CONFIG
GPKG_FILE                   = CONFIG["GPKG_FILE"]
COL_AUTHOR                  = CONFIG["COL_AUTHOR"]
OBS_FALLBACK_OBSERVATEUR_ID = CONFIG["OBS_FALLBACK_OBSERVATEUR_ID"]
PHO_FALLBACK_PHOTOGRAPH_ID  = CONFIG["PHO_FALLBACK_PHOTOGRAPH_ID"]
OBS_FALLBACK_NB_DESORDRES   = CONFIG["OBS_FALLBACK_NB_DESORDRES"]
OBS_FALLBACK_URGENCE        = CONFIG["OBS_FALLBACK_URGENCE"]
OBS_FALLBACK_SUITE          = CONFIG["OBS_FALLBACK_SUITE"]
PHO_FALLBACK_ORIENTATION    = CONFIG["PHO_FALLBACK_ORIENTATION"]
PHO_FALLBACK_COTE           = CONFIG["PHO_FALLBACK_COTE"]
COL_POSITION_ID             = CONFIG["COL_POSITION_ID"]
COL_COTE_ID                 = CONFIG["COL_COTE_ID"]
COL_SOURCE_ID               = CONFIG["COL_SOURCE_ID"]
COL_CATEGORIE_DESORDRE_ID   = CONFIG["COL_CATEGORIE_DESORDRE_ID"]
COL_TYPE_DESORDRE_ID        = CONFIG["COL_TYPE_DESORDRE_ID"]

if TYPE_CHECKING:
    import pandas as pd
    import geopandas as gpd


# ============================================================
#  ANSI COLOR UTILS
# ============================================================

ESC = "\033["

def red(text: str) -> str:
    return f"\033[41m\033[1m{text} \033[0m"

def yellow(text: str) -> str:
    return f"{ESC}33m{text}{ESC}0m"

def bold(text: str) -> str:
    return f"{ESC}1m{text}{ESC}0m"


# ============================================================
#  CONSTANTES & REGEX
# ============================================================

UUID_ANY_PATTERN = re.compile(
    r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-"
    r"[0-9a-fA-F]{12})$"
)

VALID_SOURCE_VALUES: Set[str] = {"0", "1", "2", "3", "4", "99"}
VALID_COTE_VALUES: Set[str] = {str(i) for i in range(1, 9)} | {"99"}
VALID_POSITION_VALUES: Set[str] = {str(i) for i in range(3, 16)} | {"99"}
VALID_TYPE_DESORDRE_VALUES: Set[str] = {str(i) for i in range(1, 74)} | {"99"}
VALID_CATEGORIE_DESORDRE_VALUES: Set[str] = {str(i) for i in range(1, 8)}
VALID_SUITE_VALUES: Set[str] = {str(i) for i in range(1, 9)}
VALID_URGENCE_VALUES: Set[str] = {"1", "2", "3", "4", "99"}
VALID_ORIENTATION_VALUES: Set[str] = {str(i) for i in range(1, 10)} | {"99"}

# ============================================================
#  VALIDATION GÉNÉRIQUE
# ============================================================

def is_valid_iso_date(s: str) -> bool:
    try:
        y, m, d = s.split("-")
        datetime.date(int(y), int(m), int(d))
        return True
    except Exception:
        return False


def exists(colname: str, cols: Iterable[str]) -> bool:
    return bool(colname) and colname in cols


def safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def is_nonempty_scalar(v: Any) -> bool:
    return isinstance(v, (int, float, str)) and str(v).strip() != ""


def validate_int32_positive(
    series: "pd.Series",
) -> Tuple[bool, Optional[str]]:
    import pandas as pd
    nonnull = series.dropna()
    bad: List[Any] = []
    for v in nonnull:
        try:
            f = float(v)
            i = int(f)
            if f != i or i < 0:
                bad.append(v)
        except Exception:
            bad.append(v)

    if bad:
        sample = ", ".join(str(x) for x in bad[:3]) + (
            "..." if len(bad) > 3 else ""
        )
        return False, f"valeurs invalides : {sample}"

    return True, None


def summarize_bad_values(bad_values: Iterable[Any]) -> str:
    uniques = [str(x) for x in bad_values]
    uniques = sorted(set(uniques))
    if len(uniques) == 1:
        return f"valeur '{uniques[0]}'"
    if len(uniques) <= 3:
        return "valeurs (ex: " + ", ".join(f"'{v}'" for v in uniques) + ")"
    return (
        "valeurs (ex: "
        + ", ".join(f"'{v}'" for v in uniques[:3])
        + f" … {len(uniques) - 3} autres)"
    )


def validate_mixed_sirs_column(
    series: "pd.Series",
    ctype: str,
    validator_fn: Callable[[Any], bool],
    prefix: str,
    label: str,
) -> Tuple[bool, Optional[str]]:
    import pandas as pd
    vals = series.dropna()

    text_types = ("string", "str", "text")
    int_types = ("int", "integer", "int32")

    is_text = ctype in text_types
    is_int32 = ctype in int_types

    if not is_text and not is_int32:
        return (
            False,
            f"colonne '{label}' : type GPKG = {ctype} invalide "
            "(TEXT ou INTEGER32 requis)",
        )

    bad: List[Any] = []

    for v in vals:
        if isinstance(v, float) and v.is_integer():
            v = int(v)

        if is_int32:
            if not isinstance(v, int):
                bad.append(v)
            elif not validator_fn(v):
                bad.append(v)
            continue

        if isinstance(v, int):
            if not validator_fn(v):
                bad.append(v)
            continue

        if isinstance(v, str):
            s = v.strip()
            if not s.startswith(prefix):
                bad.append(v)
                continue
            if not validator_fn(s):
                bad.append(v)
            continue

        bad.append(v)

    if bad:
        summary = summarize_bad_values(bad)
        return False, summary

    return True, None


def apply_normalization_after_validation(
    gdf: "gpd.GeoDataFrame",
) -> "gpd.GeoDataFrame":
    if COL_POSITION_ID in gdf.columns:
        gdf[COL_POSITION_ID] = gdf[COL_POSITION_ID].apply(normalize_position)

    if COL_COTE_ID in gdf.columns:
        gdf[COL_COTE_ID] = gdf[COL_COTE_ID].apply(normalize_cote)

    if COL_SOURCE_ID in gdf.columns:
        gdf[COL_SOURCE_ID] = gdf[COL_SOURCE_ID].apply(normalize_source)

    if COL_CATEGORIE_DESORDRE_ID in gdf.columns:
        gdf[COL_CATEGORIE_DESORDRE_ID] = gdf[COL_CATEGORIE_DESORDRE_ID].apply(
            normalize_categorie_desordre
        )

    if COL_TYPE_DESORDRE_ID in gdf.columns:
        gdf[COL_TYPE_DESORDRE_ID] = gdf[COL_TYPE_DESORDRE_ID].apply(
            normalize_type_desordre
        )

    return gdf


def is_gpkg_int32(path: str, layer: str, col: str) -> bool:
    import fiona
    with fiona.open(path, layer=layer) as src:
        props = src.schema.get("properties", {})
        t = props.get(col)
        return t in ("int", "integer", "int32")


def check_no_empty_columns(gdf: "pd.DataFrame") -> None:
    import pandas as pd
    errors: List[str] = []
    for col in gdf.columns:
        if col == "geometry":
            continue
        s = gdf[col]
        empty_mask = s.isna() | s.astype(str).str.strip().isin(
            ["", "nan", "None"]
        )
        if empty_mask.all():
            errors.append(col)

    if errors:
        msg: List[str] = [
            "⛔ Les colonnes vides ne sont pas acceptées. Enlever ou renseigner un minimum les colonnes:",
            *errors,
        ]
        raise DataValidationError(msg)


def is_empty(value: Any) -> bool:
    import pandas as pd
    if value is pd.NA:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass

    if isinstance(value, str):
        s = value.strip().upper()
        empty_strings = {
            "",
            "NAN",
            "NAT",
            "NULL",
            "NONE",
            "UNDEFINED",
            "NA",
            "INF",
            "INFINITY",
        }
        if s in empty_strings:
            return True
    return False


# ============================================================
#  FORMATAGE / LOG
# ============================================================

def _as_int_if_integer(v: Any) -> Optional[int]:
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return None

def q(col: Optional[str]) -> str:
    return f"'{col}'" if col else "???"


def print_unused_columns(
    all_cols: Iterable[str],
    used_des: Set[str],
    used_obs_pho: Set[str],
    _invalid_obs_pho: Set[str],
) -> None:
    all_cols_list = [c for c in all_cols if c != "geometry"]
    used = used_des | used_obs_pho
    unused = [c for c in all_cols_list if c not in used]

    if unused:
        print(bold(yellow("⚠️  Colonnes non utilisées :")))
        print(yellow("   " + ", ".join(unused)))
    else:
        print(green("✅ Toutes les colonnes présentes ont été utilisées."))


def print_mapping_verbose(rows, errors, warnings):
    headers = ["Champ", "Valeur", "Source", "Remarque", "Accepté"]

    def visible_len(s):
        from wcwidth import wcswidth
        return wcswidth(str(s))

    col_widths = [
        max(visible_len(r[i]) for r in ([headers] + rows))
        for i in range(len(headers))
    ]

    def fmt(line):
        out = []
        for i, col in enumerate(line):
            col_str = str(col)
            pad = col_widths[i] - visible_len(col_str)
            out.append(col_str + " " * pad)
        return " | ".join(out)

    sep = "─" * (sum(col_widths) + 3 * (len(headers) - 1))

    print(sep)
    print(fmt(headers))
    print(sep)
    for r in rows:
        print(fmt(r))
    print(sep)


def visual_len(s: str) -> int:
    length = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            length += 2
        else:
            length += 1
    return length


def print_error_block(
    title: str,
    items: Union[str, Sequence[Any]],
    color_func: Callable[[str], str],
) -> None:
    if isinstance(items, str):
        items = [items]

    if not items:
        print(color_func(title))
        return

    MAX_ITEMS = 10
    display_items = items[:MAX_ITEMS]
    remaining = len(items) - MAX_ITEMS

    lines = [title]

    for it in display_items:
        if isinstance(it, dict) and "raw" in it:
            lines.append(it["raw"])
        else:
            lines.append(f"   - {it}")

    if remaining > 0:
        lines.append(f"   … {remaining} autres erreurs similaires")

    max_vis = max(visual_len(line) for line in lines)

    for line in lines:
        vis = visual_len(line)
        padding = max_vis - vis + 1
        print(color_func(line + " " * padding))


# ============================================================
#  VALIDATION : valeurs directes
# ============================================================

def is_valid_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return UUID_ANY_PATTERN.match(value.strip()) is not None


def is_valid_source(value: Any) -> bool:
    if value in [None, ""]:
        return True
    if isinstance(value, int):
        return str(value) in VALID_SOURCE_VALUES
    if isinstance(value, str) and value.startswith("RefSource:"):
        return value.split(":", 1)[1] in VALID_SOURCE_VALUES
    return False


def is_valid_type_desordre(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_TYPE_DESORDRE_VALUES
    if isinstance(value, str) and value.startswith("RefTypeDesordre:"):
        return value.split(":", 1)[1] in VALID_TYPE_DESORDRE_VALUES
    return False


def is_valid_categorie_desordre(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_CATEGORIE_DESORDRE_VALUES
    if isinstance(value, str) and value.startswith("RefCategorieDesordre:"):
        return value.split(":", 1)[1] in VALID_CATEGORIE_DESORDRE_VALUES
    return False


def is_valid_cote(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_COTE_VALUES
    if isinstance(value, str) and value.startswith("RefCote:"):
        return value.split(":", 1)[1] in VALID_COTE_VALUES
    return False


def is_valid_position(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_POSITION_VALUES
    if isinstance(value, str) and value.startswith("RefPosition:"):
        return value.split(":", 1)[1] in VALID_POSITION_VALUES
    return False


def is_valid_suite_apporter(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_SUITE_VALUES
    if isinstance(value, str) and value.startswith("RefSuiteApporter:"):
        return value.split(":", 1)[1] in VALID_SUITE_VALUES
    return False


def is_valid_urgence(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_URGENCE_VALUES
    if isinstance(value, str) and value.startswith("RefUrgence:"):
        return value.split(":", 1)[1] in VALID_URGENCE_VALUES
    return False


def is_valid_orientation_photo(value: Any) -> bool:
    if isinstance(value, int):
        return str(value) in VALID_ORIENTATION_VALUES
    if isinstance(value, str) and value.startswith("RefOrientationPhoto:"):
        return value.split(":", 1)[1] in VALID_ORIENTATION_VALUES
    return False


# ============================================================
#  VALIDATION DES FALLBACKS CONFIG
# ============================================================

def validate_fallbacks(contacts: Sequence[Dict[str, Any]]) -> None:
    errors: List[str] = []
    contact_ids: Set[str] = {str(c["contactId"]) for c in contacts}

    if OBS_FALLBACK_NB_DESORDRES not in (None, ""):
        if not isinstance(OBS_FALLBACK_NB_DESORDRES, int):
            errors.append(
                "[FALLBACK] nombreDesordres — valeur "
                f"{OBS_FALLBACK_NB_DESORDRES!r} (type {type(OBS_FALLBACK_NB_DESORDRES).__name__}) "
                ": entier natif ≥ 0 attendu"
            )
        elif OBS_FALLBACK_NB_DESORDRES < 0:
            errors.append(
                "[FALLBACK] nombreDesordres — valeur "
                f"{OBS_FALLBACK_NB_DESORDRES!r} : entier natif ≥ 0 attendu"
            )

    if OBS_FALLBACK_URGENCE not in (None, ""):
        if not is_valid_urgence(OBS_FALLBACK_URGENCE):
            errors.append(
                "[FALLBACK] urgenceId — valeur "
                f"{OBS_FALLBACK_URGENCE!r} (type {type(OBS_FALLBACK_URGENCE).__name__}) : "
                "attendu entier parmi {1,2,3,4,99} ou chaîne 'RefUrgence:X'"
            )

    if OBS_FALLBACK_SUITE not in (None, ""):
        if not is_valid_suite_apporter(OBS_FALLBACK_SUITE):
            errors.append(
                "[FALLBACK] suiteApporterId — valeur "
                f"{OBS_FALLBACK_SUITE!r} (type {type(OBS_FALLBACK_SUITE).__name__}) : "
                "attendu entier parmi {1..8} ou chaîne 'RefSuiteApporter:X'"
            )

    if OBS_FALLBACK_OBSERVATEUR_ID not in (None, ""):
        cid = str(OBS_FALLBACK_OBSERVATEUR_ID).strip()
        if not is_valid_uuid(cid):
            errors.append(
                "[FALLBACK] observateurId — valeur "
                f"{OBS_FALLBACK_OBSERVATEUR_ID!r} : UUID valide attendu"
            )
        elif cid not in contact_ids:
            errors.append(
                "[FALLBACK] observateurId — valeur "
                f"{OBS_FALLBACK_OBSERVATEUR_ID!r} : cet observateur n’existe pas dans CouchDB"
            )

    if PHO_FALLBACK_ORIENTATION not in (None, ""):
        if not is_valid_orientation_photo(PHO_FALLBACK_ORIENTATION):
            errors.append(
                "[FALLBACK] orientationPhoto — valeur "
                f"{PHO_FALLBACK_ORIENTATION!r} (type {type(PHO_FALLBACK_ORIENTATION).__name__}) : "
                "attendu entier parmi {1..9,99} ou chaîne 'RefOrientationPhoto:X'"
            )

    if PHO_FALLBACK_COTE not in (None, ""):
        if not is_valid_cote(PHO_FALLBACK_COTE):
            errors.append(
                "[FALLBACK] coteId — valeur "
                f"{PHO_FALLBACK_COTE!r} (type {type(PHO_FALLBACK_COTE).__name__}) : "
                "attendu entier parmi {1..8,99} ou chaîne 'RefCote:X'"
            )

    if PHO_FALLBACK_PHOTOGRAPH_ID not in (None, ""):
        pid = str(PHO_FALLBACK_PHOTOGRAPH_ID).strip()
        if not is_valid_uuid(pid):
            errors.append(
                "[FALLBACK] photographeId — valeur "
                f"{PHO_FALLBACK_PHOTOGRAPH_ID!r} : UUID valide attendu"
            )
        elif pid not in contact_ids:
            errors.append(
                "[FALLBACK] photographeId — valeur "
                f"{PHO_FALLBACK_PHOTOGRAPH_ID!r} : ce photographe n’existe pas dans CouchDB"
            )


    if COL_AUTHOR not in (None, ""):
        author_val = str(COL_AUTHOR).strip()
        if not author_val in contact_ids:
            if is_valid_uuid(author_val):
                errors.append(
                    "[FALLBACK] author — valeur "
                    f"{COL_AUTHOR!r} : cet auteur n’existe pas dans CouchDB"
                )

    if errors:
        raise DataValidationError(
            ["⛔ Certaines valeurs définies comme fallback sont invalides :"] + errors
        )


# ============================================================
#  NORMALISATION
# ============================================================

def normalize_cote(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_COTE_VALUES:
        return f"RefCote:{n}"
    s = str(v).strip()
    if s.startswith("RefCote:") and is_valid_cote(s):
        return s
    return None


def normalize_position(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_POSITION_VALUES:
        return f"RefPosition:{n}"
    s = str(v).strip()
    if s.startswith("RefPosition:") and is_valid_position(s):
        return s
    return None


def normalize_source(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_SOURCE_VALUES:
        return f"RefSource:{n}"
    s = str(v).strip()
    if s.startswith("RefSource:") and is_valid_source(s):
        return s
    return None


def normalize_type_desordre(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_TYPE_DESORDRE_VALUES:
        return f"RefTypeDesordre:{n}"
    s = str(v).strip()
    if s.startswith("RefTypeDesordre:") and is_valid_type_desordre(s):
        return s
    return None


def normalize_suite_apporter(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_SUITE_VALUES:
        return f"RefSuiteApporter:{n}"
    s = str(v).strip()
    if s.startswith("RefSuiteApporter:") and is_valid_suite_apporter(s):
        return s
    return None


def normalize_urgence(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_URGENCE_VALUES:
        return f"RefUrgence:{n}"
    s = str(v).strip()
    if s.startswith("RefUrgence:") and is_valid_urgence(s):
        return s
    return None


def normalize_orientation_photo(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_ORIENTATION_VALUES:
        return f"RefOrientationPhoto:{n}"
    s = str(v).strip()
    if s.startswith("RefOrientationPhoto:") and is_valid_orientation_photo(s):
        return s
    return None


def normalize_categorie_desordre(v: Any) -> Optional[str]:
    n = _as_int_if_integer(v)
    if n is not None and str(n) in VALID_CATEGORIE_DESORDRE_VALUES:
        return f"RefCategorieDesordre:{n}"
    s = str(v).strip()
    if s.startswith("RefCategorieDesordre:") and is_valid_categorie_desordre(s):
        return s
    return None


def normalize_for_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: normalize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [normalize_for_json(v) for v in obj]

    if str(obj) == "NaT":
        return None

    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.strftime("%Y-%m-%d")

    return obj


def normalize_date_strict(value: Any) -> Optional[str]:
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    if re.match(r"^\d{4}-\d{2}-\d{2} ", s):
        return s[:10]

    if re.match(r"^\d{4}-\d{2}-\d{2}T", s):
        return s[:10]

    try:
        dt = datetime.datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    return s

# ============================================================
#  LECTURE/ECRITURE GPKG
# ============================================================

def read_gpkg_columns(
    path: str,
    layer: str,
    return_gdf: bool = False,
) -> Union[List[str], Tuple[List[str], "gpd.GeoDataFrame"]]:
    try:
        import geopandas as gpd
        gdf = gpd.read_file(path, layer=layer)
        cols = list(gdf.columns)
        return (cols, gdf) if return_gdf else cols
    except Exception as e:
        raise GpkgReadError(f"Impossible de lire {GPKG_FILE} : {e}")


