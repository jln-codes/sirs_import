# -*- coding: utf-8 -*-
import re

from .helpers import (
    validate_mixed_sirs_column,
    validate_int32_positive,
    is_valid_suite_apporter,
    is_valid_urgence,
    is_valid_uuid,
    summarize_bad_values,
)

from .config_loader import CONFIG
OBS_FALLBACK_OBSERVATEUR_ID = CONFIG["OBS_FALLBACK_OBSERVATEUR_ID"]
OBS_FALLBACK_URGENCE        = CONFIG["OBS_FALLBACK_URGENCE"]
OBS_FALLBACK_SUITE          = CONFIG["OBS_FALLBACK_SUITE"]
OBS_FALLBACK_NB_DESORDRES   = CONFIG["OBS_FALLBACK_NB_DESORDRES"]


ALLOWED_OBSERVATION_SUFFIXES = {
    "evolution",
    "suite",
    "designation",
    "observateurId",
    "suiteApporterId",
    "nombreDesordres",
    "urgenceId",
    "date",
}

SKIP_COLUMNS = {"date_debut", "date_fin"}
ALNUM = re.compile(r"^[A-Za-z0-9]+$")


def detect_observation_patterns(columns):
    observations = {}
    for col in columns:
        if col in SKIP_COLUMNS:
            continue
        parts = col.split("_")
        if len(parts) != 2:
            continue

        obs_key, suffix = parts
        if not ALNUM.match(obs_key):
            continue

        observations.setdefault(obs_key, []).append(suffix)

    return {k: sorted(v) for k, v in observations.items()}


def validate_observation_structure(columns, gdf, gpkg_schema):
    errors = []
    used_columns = set()
    invalid_obs_columns = []
    fallback_observateur = {}
    fallback_urgence = {}
    fallback_suite = {}
    fallback_nb_desordres = {}

    observations = detect_observation_patterns(columns)

    if not observations:
        return {
            "patterns": {"observations": observations},
            "errors": [],
            "used_columns": used_columns,
            "invalid_obs_columns": invalid_obs_columns,
            "fallback_observateur": fallback_observateur,
        }

    for obs_key, suffixes in observations.items():

        date_col = f"{obs_key}_date"

        raw_cols_for_obs = [
            c for c in columns
            if c.startswith(f"{obs_key}_")
            and c != date_col
            and len(c.split("_")) == 2
        ]

        authorized_suffixes_present = [
            col for col in raw_cols_for_obs
            if col.split("_",1)[1].split("_")[0] in ALLOWED_OBSERVATION_SUFFIXES
        ]

        # suffixes invalides
        for col in raw_cols_for_obs:
            root = col.split("_",1)[1].split("_")[0].strip()
            if root not in ALLOWED_OBSERVATION_SUFFIXES:
                invalid_obs_columns.append(col)
                errors.append(f"[GPKG] {col} — suffixe non autorisé")

        # date obligatoire
        if date_col not in columns:
            if authorized_suffixes_present:
                flist = ", ".join(authorized_suffixes_present)
                errors.append(f"[GPKG] {date_col} — requis car {flist} existe")
        else:
            used_columns.add(date_col)
            ctype = gpkg_schema.get(date_col)
            if ctype != "date":
                errors.append(f"[GPKG] {date_col} — type {ctype}, attendu 'date'")

        # FALLBACKS

        # observateurId
        obs_observ_col = f"{obs_key}_observateurId"
        col_missing = obs_observ_col not in columns
        fallback_observateur[obs_key] = col_missing
        if col_missing:
            v = OBS_FALLBACK_OBSERVATEUR_ID
            if not is_valid_uuid(str(v)):
                errors.append(f"[FALLBACK] OBS_FALLBACK_OBSERVATEUR_ID — valeur '{v}' : attendu UUID valide")

        # urgenceId
        obs_urgence_col = f"{obs_key}_urgenceId"
        col_missing = obs_urgence_col not in columns
        fallback_urgence[obs_key] = col_missing
        if col_missing:
            v = OBS_FALLBACK_URGENCE
            if not is_valid_urgence(v):
                errors.append(f"[FALLBACK] OBS_FALLBACK_URGENCE — valeur '{v}' : attendu entier {{1,2,3,4,99}} ou 'RefUrgence:X'")

        # suiteApporterId
        obs_suite_col = f"{obs_key}_suiteApporterId"
        col_missing = obs_suite_col not in columns
        fallback_suite[obs_key] = col_missing
        if col_missing:
            v = OBS_FALLBACK_SUITE
            if not is_valid_suite_apporter(v):
                errors.append(f"[FALLBACK] OBS_FALLBACK_SUITE — valeur '{v}' : attendu entier {{1..8}} ou 'RefSuiteApporter:X'")

        # nombreDesordres
        obs_nb_col = f"{obs_key}_nombreDesordres"
        col_missing = obs_nb_col not in columns
        fallback_nb_desordres[obs_key] = col_missing
        if col_missing:
            v = OBS_FALLBACK_NB_DESORDRES
            if not isinstance(v, int) or v < 0:
                errors.append(f"[FALLBACK] OBS_FALLBACK_NB_DESORDRES — valeur '{v}' : attendu entier natif ≥ 0")

        # VALIDATION DES COLONNES GPKG

        for col in raw_cols_for_obs:
            root = col.split("_",1)[1].split("_")[0].strip()
            if col not in columns:
                continue

            used_columns.add(col)
            series = gdf[col]
            nonnull = series.dropna()

            if root == "observateurId":
                bad = [v for v in nonnull.astype(str) if not is_valid_uuid(v)]
                if bad:
                    summary = summarize_bad_values(bad)
                    errors.append(f"[GPKG] {col} — {summary} : attendu UUID valide")

            elif root == "urgenceId":
                ctype = gpkg_schema.get(col)
                ok, msg = validate_mixed_sirs_column(
                    series, ctype, is_valid_urgence, "RefUrgence:", "urgenceId"
                )
                if not ok:
                    errors.append(
                        f"[GPKG] {col} — {msg} : attendu entier {{1,2,3,4,99}} ou 'RefUrgence:X'"
                    )

            elif root == "nombreDesordres":
                ctype = gpkg_schema.get(col)
                if ctype not in ("int", "integer", "int32"):
                    errors.append(f"[GPKG] {col} — type {ctype}, attendu int32")
                ok, msg = validate_int32_positive(series)
                if not ok:
                    errors.append(f"[GPKG] {col} — {msg}")

            elif root == "suiteApporterId":
                ctype = gpkg_schema.get(col)
                ok, msg = validate_mixed_sirs_column(
                    series, ctype, is_valid_suite_apporter, "RefSuiteApporter:", "suiteApporterId"
                )
                if not ok:
                    errors.append(
                        f"[GPKG] {col} — {msg} : attendu entier {{1..8}} ou 'RefSuiteApporter:X'"
                    )

    return {
        "patterns": {"observations": observations},
        "errors": errors,
        "used_columns": used_columns,
        "invalid_obs_columns": invalid_obs_columns,
        "fallback_observateur": fallback_observateur,
        "fallback_urgence": fallback_urgence,
        "fallback_suite": fallback_suite,
        "fallback_nb_desordres": fallback_nb_desordres,
    }

