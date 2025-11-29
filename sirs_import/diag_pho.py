# -*- coding: utf-8 -*-
import re

from .config_loader import CONFIG
PHO_FALLBACK_PHOTOGRAPH_ID = CONFIG["PHO_FALLBACK_PHOTOGRAPH_ID"]
PHO_FALLBACK_DES_GEOM      = CONFIG["PHO_FALLBACK_DES_GEOM"]


from .helpers import (
    is_valid_uuid,
    is_valid_iso_date,
    is_valid_cote,
    is_valid_orientation_photo,
    validate_mixed_sirs_column,
    summarize_bad_values,
)

SKIP_COLUMNS = {"date_debut", "date_fin"}
ALNUM = re.compile(r"^[A-Za-z0-9]+$")

ALLOWED_PHOTO_SUFFIXES = {
    "chemin",
    "photographeId",
    "date",
    "designation",
    "libelle",
    "orientationPhoto",
    "coteId",
}


def detect_photo_patterns(columns):
    photos = {}

    for col in columns:
        if col in SKIP_COLUMNS:
            continue

        parts = col.split("_")
        if len(parts) != 3:
            continue

        obs_key, pho_key, suffix = parts

        if not ALNUM.match(obs_key):
            continue
        if not ALNUM.match(pho_key):
            continue

        photos.setdefault((obs_key, pho_key), []).append(suffix)

    return {k: sorted(v) for k, v in photos.items()}


def validate_photo_structure(photo_patterns, columns, gdf, observation_dates, gpkg_schema):
    errors = []
    used_columns = set()
    invalid_photo_columns = []
    fallback_photograph = {}
    fallback_photo_date = {}
    fallback_photo_geom = {}

    for (obs_key, pho_key), suffixes in photo_patterns.items():

        full_cols = {
            suf: f"{obs_key}_{pho_key}_{suf}"
            for suf in suffixes
            if f"{obs_key}_{pho_key}_{suf}" in columns
        }

        authorized_suffixes_present = [
            col
            for suf, col in full_cols.items()
            if suf.split("_")[0] in ALLOWED_PHOTO_SUFFIXES
        ]

        # =============================================================
        # COLONNES NON AUTORISÉES
        # =============================================================

        for suf, col in full_cols.items():
            root = suf.split("_")[0]
            if root not in ALLOWED_PHOTO_SUFFIXES:
                errors.append(
                    f"[GPKG] {obs_key}/{pho_key} — suffixe non autorisé '{col}'"
                )
                invalid_photo_columns.append(col)

        if not authorized_suffixes_present:
            continue

        # =============================================================
        # chemin obligatoire
        # =============================================================
        chemin_col = f"{obs_key}_{pho_key}_chemin"
        if chemin_col not in columns:
            flist = ", ".join(f"'{c}'" for c in authorized_suffixes_present)
            errors.append(
                f"[GPKG] {obs_key}/{pho_key}.chemin — requis car {flist} existe"
            )
        else:
            used_columns.add(chemin_col)

        # =============================================================
        # FALLBACKS
        # =============================================================

        # ---- photographeId ----
        photo_phot_col = f"{obs_key}_{pho_key}_photographeId"
        col_missing = photo_phot_col not in columns
        fallback_photograph[(obs_key, pho_key)] = col_missing
        if col_missing:
            val = PHO_FALLBACK_PHOTOGRAPH_ID
            if not is_valid_uuid(str(val)):
                errors.append(
                    f"[FALLBACK] {obs_key}/{pho_key}.photographeId — valeur {val!r} "
                    f"(type {type(val).__name__}) : attendu UUID valide"
                )

        # ---- date (CAS PARTICULIER) ----
        photo_date_col = f"{obs_key}_{pho_key}_date"
        col_missing = photo_date_col not in columns
        fallback_photo_date[(obs_key, pho_key)] = col_missing

        # ---- geometry fallback indicator ----
        fallback_photo_geom[(obs_key, pho_key)] = bool(PHO_FALLBACK_DES_GEOM)

        # =============================================================
        # vérification : photo dépend de obs.date
        # =============================================================
        obs_date_col = f"{obs_key}_date"
        if obs_date_col not in columns:
            errors.append(
                f"[GPKG] {obs_key}/{pho_key}.date — dépend de '{obs_key}_date' inexistant"
            )
        else:
            used_columns.add(obs_date_col)
            raw_vals = gdf[obs_date_col].dropna().astype(str)
            bad = [v for v in raw_vals if not is_valid_iso_date(v)]
            if bad:
                sample = ", ".join(bad[:3]) + ("..." if len(bad) > 3 else "")
                errors.append(
                    f"[GPKG] {obs_key}.date — valeurs non ISO dans '{obs_date_col}' (ex: {sample})"
                )

        # =============================================================
        # VALIDATION DES VALEURS DES COLONNES GPKG
        # =============================================================

        for suf in suffixes:
            fullcol = f"{obs_key}_{pho_key}_{suf}"
            root = suf.split("_")[0]

            if root not in ALLOWED_PHOTO_SUFFIXES:
                continue
            if fullcol not in columns:
                continue

            used_columns.add(fullcol)

            if root == "date":
                raw_vals = gdf[fullcol].dropna().astype(str)
                bad = [v for v in raw_vals if not is_valid_iso_date(v)]
                if bad:
                    sample = ", ".join(bad[:3]) + ("..." if len(bad) > 3 else "")
                    errors.append(
                        f"[GPKG] {obs_key}/{pho_key}.date — valeurs ISO invalides (ex: {sample})"
                    )

            elif root == "orientationPhoto":
                ctype = gpkg_schema.get(fullcol)
                ok, msg = validate_mixed_sirs_column(
                    gdf[fullcol],
                    ctype,
                    is_valid_orientation_photo,
                    "RefOrientationPhoto:",
                    "orientationPhoto",
                )
                if not ok:
                    errors.append(f"[GPKG] {obs_key}/{pho_key}.orientationPhoto — {msg}")

            elif root == "coteId":
                ctype = gpkg_schema.get(fullcol)
                ok, msg = validate_mixed_sirs_column(
                    gdf[fullcol],
                    ctype,
                    is_valid_cote,
                    "RefCote:",
                    "coteId",
                )
                if not ok:
                    errors.append(f"[GPKG] {obs_key}/{pho_key}.coteId — {msg}")

            elif root == "photographeId":
                raw_vals = gdf[fullcol].dropna().astype(str)
                bad = [v for v in raw_vals if not is_valid_uuid(v)]
                if bad:
                    sample = ", ".join(bad[:3]) + ("..." if len(bad) > 3 else "")
                    errors.append(
                        f"[GPKG] {obs_key}/{pho_key}.photographeId — UUID invalides (ex: {sample})"
                    )

    return {
        "errors": errors,
        "used_columns": used_columns,
        "invalid_photo_columns": invalid_photo_columns,
        "fallback_photograph": fallback_photograph,
        "fallback_photo_date": fallback_photo_date,
        "fallback_photo_geom": fallback_photo_geom,
    }

