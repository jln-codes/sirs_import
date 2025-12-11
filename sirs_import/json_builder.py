# -*- coding: utf-8 -*-
import os
import json
from .config_loader import CONFIG, PROJECT_DIR
GPKG_LAYER                 = CONFIG["GPKG_LAYER"]
COL_AUTHOR                 = CONFIG["COL_AUTHOR"]
COL_DESIGNATION            = CONFIG["COL_DESIGNATION"]
COL_LIBELLE                = CONFIG["COL_LIBELLE"]
COL_COMMENTAIRE            = CONFIG["COL_COMMENTAIRE"]
IS_VALID                   = CONFIG["IS_VALID"]
COL_DATE_DEBUT             = CONFIG["COL_DATE_DEBUT"]
COL_DATE_FIN               = CONFIG["COL_DATE_FIN"]
COL_LINEAR_ID              = CONFIG["COL_LINEAR_ID"]
COL_SOURCE_ID              = CONFIG["COL_SOURCE_ID"]
COL_LIEUDIT                = CONFIG["COL_LIEUDIT"]
COL_COTE_ID                = CONFIG["COL_COTE_ID"]
COL_POSITION_ID            = CONFIG["COL_POSITION_ID"]
COL_TYPE_DESORDRE_ID       = CONFIG["COL_TYPE_DESORDRE_ID"]
COL_CATEGORIE_DESORDRE_ID  = CONFIG["COL_CATEGORIE_DESORDRE_ID"]
OBS_FALLBACK_OBSERVATEUR_ID = CONFIG["OBS_FALLBACK_OBSERVATEUR_ID"]
PHO_FALLBACK_PHOTOGRAPH_ID  = CONFIG["PHO_FALLBACK_PHOTOGRAPH_ID"]
PHO_FALLBACK_OBS_DATE       = CONFIG["PHO_FALLBACK_OBS_DATE"]
PHO_FALLBACK_DES_GEOM       = CONFIG["PHO_FALLBACK_DES_GEOM"]
OBS_FALLBACK_URGENCE        = CONFIG["OBS_FALLBACK_URGENCE"]
OBS_FALLBACK_SUITE          = CONFIG["OBS_FALLBACK_SUITE"]
OBS_FALLBACK_NB_DESORDRES   = CONFIG["OBS_FALLBACK_NB_DESORDRES"]

from .helpers import (
    is_empty,
    is_valid_uuid,
    normalize_for_json,
    normalize_date_strict,
    normalize_cote,
    normalize_position,
    normalize_source,
    normalize_type_desordre,
    normalize_categorie_desordre,
    normalize_urgence,
    normalize_suite_apporter,
    normalize_orientation_photo,
)

PHOTO_SUFFIXES = {
    "chemin",
    "photographeId",
    "date",
    "designation",
    "libelle",
    "orientationPhoto",
    "coteId",
}

DIGUE_NAME = os.path.basename(PROJECT_DIR)

def _safe_str(v):
    if v is None:
        return None
    return str(v).strip()

def _extract_author_from_row(row, gdf_columns):
    if COL_AUTHOR in gdf_columns and not is_empty(row[COL_AUTHOR]):
        return _safe_str(row[COL_AUTHOR])
    else:
        sval = (COL_AUTHOR or "").strip()
        return sval if is_valid_uuid(sval) else None

def _positions_from_geometry(geom):
    if geom is None or geom.is_empty:
        return None, None

    gtype = getattr(geom, "geom_type", None)

    if gtype == "Point":
        try:
            x = geom.x
            y = geom.y
            pt = f"POINT ({x} {y})"
            return pt, pt
        except Exception:
            return None, None

    if gtype == "LineString":
        try:
            coords = list(geom.coords)
        except Exception:
            return None, None

        if len(coords) < 2:
            return None, None

        x0, y0 = coords[0]
        x1, y1 = coords[-1]

        return f"POINT ({x0} {y0})", f"POINT ({x1} {y1})"

    return None, None


def _extract_photos_from_row(row, obs_key, photos_patterns, obs_date_value, pos_deb_parent, pos_fin_parent):
    photos = []

    for (obs_ref, photo_key), suffixes in photos_patterns.items():
        if obs_ref != obs_key:
            continue

        photo_data = {
            "@class": "fr.sirs.core.model.Photo",
            "valid": IS_VALID,
        }

        # ---- AUTHOR INSERTION ----
        author_val = _extract_author_from_row(row, row.index)
        if author_val:
            photo_data["author"] = author_val
        # ---------------------------

        raw_chemin = None
        raw_photo_date = None
        raw_photographe = None
        raw_designation = None
        raw_libelle = None
        raw_orientation = None
        raw_cote = None

        for s in suffixes:
            if s not in PHOTO_SUFFIXES:
                continue

            field = f"{obs_key}_{photo_key}_{s}"
            if field not in row.index:
                continue

            val = row[field]
            if is_empty(val):
                continue

            if s == "chemin":
                raw_chemin = val
            elif s == "photographeId":
                raw_photographe = val
            elif s == "date":
                raw_photo_date = val
            elif s == "designation":
                raw_designation = val
            elif s == "libelle":
                raw_libelle = val
            elif s == "orientationPhoto":
                raw_orientation = val
            elif s == "coteId":
                raw_cote = val

        if is_empty(raw_chemin):
            continue

        photo_data["chemin"] = f"{DIGUE_NAME}/{_safe_str(raw_chemin)}"

        # photographeId
        if not is_empty(raw_photographe):
            photo_data["photographeId"] = _safe_str(raw_photographe)
        else:
            fb = _safe_str(PHO_FALLBACK_PHOTOGRAPH_ID)
            if fb:
                photo_data["photographeId"] = fb

        # date
        if not is_empty(raw_photo_date):
            photo_data["date"] = normalize_date_strict(raw_photo_date)
        else:
            if PHO_FALLBACK_OBS_DATE and not is_empty(obs_date_value):
                photo_data["date"] = normalize_date_strict(obs_date_value)

        if not is_empty(raw_designation):
            photo_data["designation"] = _safe_str(raw_designation)

        if not is_empty(raw_libelle):
            photo_data["libelle"] = _safe_str(raw_libelle)

        # orientationPhoto
        if not is_empty(raw_orientation):
            norm_orient = normalize_orientation_photo(raw_orientation)
            if norm_orient:
                photo_data["orientationPhoto"] = norm_orient

        # coteId
        if not is_empty(raw_cote):
            norm_cote = normalize_cote(raw_cote)
            if norm_cote:
                photo_data["coteId"] = norm_cote

        # fallback position depuis le désordre
        if PHO_FALLBACK_DES_GEOM:
            if pos_deb_parent:
                photo_data["positionDebut"] = pos_deb_parent
            if pos_fin_parent:
                photo_data["positionFin"] = pos_fin_parent

        photos.append(photo_data)

    return photos


def _extract_observations_from_row(row, patterns, pos_deb_parent, pos_fin_parent):
    observations = []

    obs_patterns = patterns.get("observations", {})
    photos_patterns = patterns.get("photos", {})

    for obs_key, suffixes in obs_patterns.items():

        date_field = f"{obs_key}_date"
        if date_field not in row.index:
            continue

        date_val = row[date_field]
        if is_empty(date_val):
            continue

        obs_data = {
            "@class": "fr.sirs.core.model.Observation",
            "valid": IS_VALID,
            "date": normalize_date_strict(date_val),
        }

        # ---- AUTHOR INSERTION ----
        author_val = _extract_author_from_row(row, row.index)
        if author_val:
            obs_data["author"] = author_val
        # ---------------------------

        for s in suffixes:
            if s == "date":
                continue

            field = f"{obs_key}_{s}"
            if field not in row.index:
                continue

            val = row[field]
            if is_empty(val):
                continue

            # nombreDesordres → entier natif
            if s == "nombreDesordres":
                try:
                    f = float(val)
                    n = int(f)
                    if f == n:
                        obs_data[s] = n
                        continue
                except Exception:
                    pass
                continue

            # urgenceId → RefUrgence:X
            if s == "urgenceId":
                norm = normalize_urgence(val)
                if norm:
                    obs_data[s] = norm
                continue

            # suiteApporterId → RefSuiteApporter:X
            if s == "suiteApporterId":
                norm = normalize_suite_apporter(val)
                if norm:
                    obs_data[s] = norm
                continue

            # autres champs (observateurId, designation, evolution, etc.)
            obs_data[s] = _safe_str(val)

        # fallback observateur
        if "observateurId" not in obs_data or is_empty(obs_data.get("observateurId")):
            fb = _safe_str(OBS_FALLBACK_OBSERVATEUR_ID)
            if fb:
                obs_data["observateurId"] = fb

        # fallback urgence (normalisé)
        if "urgenceId" not in obs_data or is_empty(obs_data.get("urgenceId")):
            norm = normalize_urgence(OBS_FALLBACK_URGENCE)
            if norm:
                obs_data["urgenceId"] = norm

        # fallback suite (normalisé)
        if "suiteApporterId" not in obs_data or is_empty(obs_data.get("suiteApporterId")):
            norm = normalize_suite_apporter(OBS_FALLBACK_SUITE)
            if norm:
                obs_data["suiteApporterId"] = norm

        # fallback nombreDesordres
        if "nombreDesordres" not in obs_data or is_empty(obs_data.get("nombreDesordres")):
            if OBS_FALLBACK_NB_DESORDRES not in (None, ""):
                obs_data["nombreDesordres"] = int(OBS_FALLBACK_NB_DESORDRES)

        photos = _extract_photos_from_row(
            row,
            obs_key,
            photos_patterns,
            date_val,
            pos_deb_parent,
            pos_fin_parent,
        )

        if photos:
            obs_data["photos"] = photos

        observations.append(obs_data)

    return observations



def _build_desordre_from_row(row, gdf_columns, patterns):

    designation_val = _safe_str(row[COL_DESIGNATION]) if COL_DESIGNATION in gdf_columns and not is_empty(row[COL_DESIGNATION]) else None
    libelle_val = _safe_str(row[COL_LIBELLE]) if COL_LIBELLE in gdf_columns and not is_empty(row[COL_LIBELLE]) else None
    commentaire_val = _safe_str(row[COL_COMMENTAIRE]) if COL_COMMENTAIRE in gdf_columns and not is_empty(row[COL_COMMENTAIRE]) else None

    # author
    author_val = _extract_author_from_row(row, gdf_columns)

    # dates
    if COL_DATE_DEBUT in gdf_columns and not is_empty(row[COL_DATE_DEBUT]):
        date_debut_val = normalize_date_strict(row[COL_DATE_DEBUT])
    else:
        date_debut_val = normalize_date_strict(_safe_str(COL_DATE_DEBUT))

    if COL_DATE_FIN in gdf_columns and not is_empty(row[COL_DATE_FIN]):
        date_fin_val = normalize_date_strict(row[COL_DATE_FIN])
    else:
        date_fin_val = None

    # géométrie → positions
    geom = getattr(row, "geometry", None)
    pos_deb, pos_fin = _positions_from_geometry(geom)

    # linearId (UUID brut)
    if COL_LINEAR_ID in gdf_columns:
        linear_id_val = _safe_str(row[COL_LINEAR_ID])
    else:
        linear_id_val = _safe_str(COL_LINEAR_ID)

    # sourceId (normalisation, gère int / float / 'RefSource:X')
    if COL_SOURCE_ID in gdf_columns and not is_empty(row[COL_SOURCE_ID]):
        source_id_val = normalize_source(row[COL_SOURCE_ID])
    else:
        source_id_val = normalize_source(COL_SOURCE_ID)

    # typeDesordreId
    if COL_TYPE_DESORDRE_ID in gdf_columns and not is_empty(row[COL_TYPE_DESORDRE_ID]):
        type_desordre_val = normalize_type_desordre(row[COL_TYPE_DESORDRE_ID])
    else:
        type_desordre_val = normalize_type_desordre(COL_TYPE_DESORDRE_ID)

    # categorieDesordreId
    if COL_CATEGORIE_DESORDRE_ID in gdf_columns and not is_empty(row[COL_CATEGORIE_DESORDRE_ID]):
        categorie_desordre_val = normalize_categorie_desordre(row[COL_CATEGORIE_DESORDRE_ID])
    else:
        categorie_desordre_val = normalize_categorie_desordre(COL_CATEGORIE_DESORDRE_ID)

    # coteId
    if COL_COTE_ID in gdf_columns and not is_empty(row[COL_COTE_ID]):
        cote_id_val = normalize_cote(row[COL_COTE_ID])
    else:
        cote_id_val = normalize_cote(COL_COTE_ID)

    # positionId
    if COL_POSITION_ID in gdf_columns and not is_empty(row[COL_POSITION_ID]):
        position_id_val = normalize_position(row[COL_POSITION_ID])
    else:
        position_id_val = normalize_position(COL_POSITION_ID)

    # lieuDit
    lieu_dit_val = _safe_str(row[COL_LIEUDIT]) if COL_LIEUDIT in gdf_columns and not is_empty(row[COL_LIEUDIT]) else None

    # observations
    observations_val = None
    if patterns:
        obs_list = _extract_observations_from_row(row, patterns, pos_deb, pos_fin)
        if obs_list:
            observations_val = obs_list

    des = {
        "@class": "fr.sirs.core.model.Desordre",
        "valid": IS_VALID,
    }

    if designation_val:
        des["designation"] = designation_val
    if libelle_val:
        des["libelle"] = libelle_val
    if commentaire_val:
        des["commentaire"] = commentaire_val
    if linear_id_val:
        des["linearId"] = linear_id_val
    if author_val:
        des["author"] = author_val
    if lieu_dit_val:
        des["lieuDit"] = lieu_dit_val
    if cote_id_val:
        des["coteId"] = cote_id_val
    if position_id_val:
        des["positionId"] = position_id_val
    if source_id_val:
        des["sourceId"] = source_id_val
    if type_desordre_val:
        des["typeDesordreId"] = type_desordre_val
    if categorie_desordre_val:
        des["categorieDesordreId"] = categorie_desordre_val
    if pos_deb:
        des["positionDebut"] = pos_deb
    if pos_fin:
        des["positionFin"] = pos_fin
    if date_debut_val:
        des["date_debut"] = date_debut_val
    if date_fin_val:
        des["date_fin"] = date_fin_val
    if observations_val:
        des["observations"] = observations_val

    return des


def generate_json(gdf, patterns, output=None):
    if output is None:
        output = f"{GPKG_LAYER}.json"

    output_path = os.path.join(PROJECT_DIR, output)
    results = []
    cols = list(gdf.columns)

    for i, (idx, row) in enumerate(gdf.iterrows(), start=1):
        des = _build_desordre_from_row(row, cols, patterns)
        results.append(des)

    data = normalize_for_json(results)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "output": output_path,
        "written": len(results),
        "documents": data,
    }

