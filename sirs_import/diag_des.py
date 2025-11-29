# -*- coding: utf-8 -*-
import datetime
from typing import List, Tuple
from .helpers import (
    exists, q, is_valid_iso_date, is_valid_cote, is_valid_position,
    is_valid_source, normalize_cote, normalize_position,
    normalize_source, is_nonempty_scalar, is_valid_uuid,
    is_valid_type_desordre, is_valid_categorie_desordre,
    normalize_type_desordre, normalize_categorie_desordre,
    is_empty
)

from .config_loader import CONFIG
COL_AUTHOR             = CONFIG["COL_AUTHOR"]
COL_COMMENTAIRE        = CONFIG["COL_COMMENTAIRE"]
COL_DATE_DEBUT         = CONFIG["COL_DATE_DEBUT"]
COL_DATE_FIN           = CONFIG["COL_DATE_FIN"]
IS_VALID               = CONFIG["IS_VALID"]
COL_LINEAR_ID          = CONFIG["COL_LINEAR_ID"]
COL_LIEUDIT            = CONFIG["COL_LIEUDIT"]
COL_SOURCE_ID          = CONFIG["COL_SOURCE_ID"]
COL_DESIGNATION        = CONFIG["COL_DESIGNATION"]
COL_LIBELLE            = CONFIG["COL_LIBELLE"]
COL_COTE_ID            = CONFIG["COL_COTE_ID"]
COL_POSITION_ID        = CONFIG["COL_POSITION_ID"]
COL_TYPE_DESORDRE_ID   = CONFIG["COL_TYPE_DESORDRE_ID"]
COL_CATEGORIE_DESORDRE_ID = CONFIG["COL_CATEGORIE_DESORDRE_ID"]


USED_COLUMNS = set()

# ======================================================================
#  UTILITAIRES
# ======================================================================
def _mark(colname):
    if isinstance(colname, str) and colname.strip():
        USED_COLUMNS.add(colname.strip())


def _diag_base_metadata(rows, errors, warnings):
    src = "entête du script"
    if isinstance(IS_VALID, bool):
        flag = IS_VALID
    else:
        flag = False
        src = "correction auto"
        warnings.append("valid : entête du script — valeur non reconnue, redéfini automatiquement sur False")
    rows.append(["valid", flag, src, "désordres validés avant import" if flag else "désordres seront validés dans SIRS", "oui"])


# ======================================================================
#  FONCTIONS DE DIAGNOSTIC
# ======================================================================
def _diag_text_field(label, col_cfg, cols, gdf, rows, errors):
    if not isinstance(col_cfg, str) or not col_cfg.strip():
        rows.append([label, "---", "non défini", "facultatif", "oui"])
        return
    if not exists(col_cfg, cols):
        rows.append([label, q(col_cfg), "manquante", "", "non"])
        errors.append(f"{label} : colonne {q(col_cfg)} — introuvable dans le GPKG")
        return
    _mark(col_cfg)
    rows.append([label, q(col_cfg), "colonne GPKG", "", "oui"])


def _diag_text_columns(cols, gdf, rows, errors):
    _diag_text_field("designation", COL_DESIGNATION, cols, gdf, rows, errors)
    _diag_text_field("libelle", COL_LIBELLE, cols, gdf, rows, errors)
    _diag_text_field("commentaire", COL_COMMENTAIRE, cols, gdf, rows, errors)
    _diag_text_field("lieuDit", COL_LIEUDIT, cols, gdf, rows, errors)


def _diag_linear_id(cols, gdf, rows, errors):
    val = COL_LINEAR_ID
    if val in cols:
        _mark(val)
        series = gdf[val]

        # unified detection of empty values (None, "", " ", "nan", "NULL", "None", etc.)
        empty_values = [v for v in series if is_empty(v)]
        if empty_values:
            rows.append(["linearId", q(val), "colonne GPKG", "valeurs vides détectées", "non"])
            errors.append(f"linearId : colonne '{val}' — contient des valeurs vides")
            return

        invalid = [s for s in series.astype(str) if not is_valid_uuid(s)]
        if invalid:
            sample = ", ".join(invalid[:3]) + ("..." if len(invalid) > 3 else "")
            rows.append(["linearId", q(val), "colonne GPKG", "UUID invalides", "non"])
            errors.append(f"linearId : colonne '{val}' — valeurs non conformes UUID (ex: {sample})")
        else:
            rows.append(["linearId", q(val), "colonne GPKG", "UUID valides sans NULL", "oui"])
        return

    sval = (val or "").strip()
    if not sval:
        rows.append(["linearId", "???", "non défini", "obligatoire!", "non"])
        errors.append("linearId : fallback statique — valeur vide ou non définie (UUID obligatoire)")
    elif is_valid_uuid(sval):
        rows.append(["linearId", sval, "entête du script", "UUID unique pour tous les désordres", "oui"])
    else:
        rows.append(["linearId", sval, "entête du script", "UUID invalide", "non"])
        errors.append(f"linearId : fallback statique — UUID invalide (valeur fournie : {sval})")


def _norm_for_validation(v):
    """
    Normalisation locale pour la validation :
    - 2.0, 3.0, etc. (float) -> int 2, 3
    - sinon valeur inchangée
    """
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _diag_generic_code(
    rows, errors, warnings,
    cols, gdf,
    colname,
    label,
    validator,
    normalizer,
    msg_invalid_col,
    msg_invalid_fallback,
    msg_valid_col,
    msg_valid_fallback,
    msg_fallback_missing,
    msg_relationship=None,
    experimental=False
):
    if exists(colname, cols):
        if experimental and msg_relationship and warnings is not None:
            warnings.append(msg_relationship)
        _mark(colname)

        invalids = []
        # IMPORTANT : on ne fait plus dropna().astype(str)
        # - on ignore explicitement les valeurs "vides" (is_empty)
        # - on corrige le cas float 2.0 -> int 2 avant validation
        for v in gdf[colname]:
            if is_empty(v):
                continue
            v2 = _norm_for_validation(v)
            if not validator(v2):
                invalids.append(v)

        if invalids:
            sample = ", ".join(str(x) for x in invalids[:3]) + ("..." if len(invalids) > 3 else "")
            rows.append([label, q(colname), "colonne GPKG", msg_invalid_col.format(sample), "non"])
            errors.append(f"{label} : colonne '{colname}' — {msg_invalid_col.format(sample)}")
        else:
            rows.append([label, q(colname), "colonne GPKG", msg_valid_col, "oui"])

    elif is_nonempty_scalar(colname):
        val = colname
        norm = normalizer(val)
        if norm:
            rows.append([label, norm, "entête du script", msg_valid_fallback, "oui"])
        else:
            rows.append([label, val, "entête du script", "format invalide", "non"])
            # ⬇️ Ici on passe la valeur ET son type à la chaîne de formatage
            errors.append(msg_invalid_fallback.format(val, type(val).__name__))
    else:
        rows.append([label, "---", "non défini", msg_fallback_missing, "oui"])


def _diag_author(cols, gdf, rows, errors, contact_ids):
    val = COL_AUTHOR

    # cas 1 — config vide => autorisé
    if not isinstance(val, str) or not val.strip():
        rows.append(["author", "---", "non défini", "facultatif", "oui"])
        return

    # cas 2 — valeur correspond à une colonne du GPKG
    if val in cols:
        _mark(val)
        series = gdf[val]

        # valeurs non-null mais invalides (syntaxe UUID)
        invalid_syntax = [
            s for s in series.astype(str)
            if not is_empty(s) and not is_valid_uuid(s)
        ]

        if invalid_syntax:
            msgsample = ", ".join(invalid_syntax[:3]) + ("..." if len(invalid_syntax) > 3 else "")
            rows.append(["author", q(val), "colonne GPKG", "UUID invalides détectés", "non"])
            errors.append(
                f"author : colonne '{val}' — UUID au format invalide (ex: {msgsample})"
            )
            return

        # valeurs existantes mais inconnues dans CouchDB
        invalid_contact = [
            s for s in series.astype(str)
            if not is_empty(s) and s not in contact_ids
        ]

        if invalid_contact:
            msgsample = ", ".join(invalid_contact[:3]) + ("..." if len(invalid_contact) > 3 else "")
            rows.append(["author", q(val), "colonne GPKG", "UUID inconnus dans SIRS", "non"])
            errors.append(
                f"author : colonne '{val}' — UUID inconnus dans CouchDB/SIRS (ex: {msgsample})"
            )
        else:
            rows.append(["author", q(val), "colonne GPKG", "UUID valides et connus dans SIRS", "oui"])

        return

    # cas 3 — valeur dans config => fallback statique
    sval = val.strip()

    if is_valid_uuid(sval):
        # le fallback statique a déjà été validé dans validate_fallbacks()
        rows.append(["author", sval, "entête du script", "UUID unique pour tous les désordres", "oui"])
    else:
        rows.append(["author", sval, "entête du script", "UUID invalide", "non"])
        errors.append(f"author : fallback statique — UUID invalide (valeur fournie : {sval})")



def _diag_cote(cols, gdf, rows, errors):
    _diag_generic_code(
        rows, errors, None,
        cols, gdf,
        COL_COTE_ID,
        "coteId",
        is_valid_cote,
        normalize_cote,
        msg_invalid_col="valeurs invalides (ex: {})",
        msg_invalid_fallback="coteId : fallback statique — valeur {0!r} invalide (type {1}, attendu: entier natif ou 'RefCote:X')",
        msg_valid_col="",
        msg_valid_fallback="valeur unique pour tous les désordres",
        msg_fallback_missing="facultatif",
    )


def _diag_position(cols, gdf, rows, errors):
    _diag_generic_code(
        rows, errors, None,
        cols, gdf,
        COL_POSITION_ID,
        "positionId",
        is_valid_position,
        normalize_position,
        msg_invalid_col="valeurs invalides (ex: {})",
        msg_invalid_fallback="positionId : fallback statique — valeur {0!r} invalide (type {1}, attendu: entier natif ou 'RefPosition:X')",
        msg_valid_col="",
        msg_valid_fallback="valeur unique pour tous les désordres",
        msg_fallback_missing="facultatif",
    )


def _diag_source(cols, gdf, rows, errors):
    _diag_generic_code(
        rows, errors, None,
        cols, gdf,
        COL_SOURCE_ID,
        "sourceId",
        is_valid_source,
        normalize_source,
        msg_invalid_col="valeurs invalides (ex: {})",
        msg_invalid_fallback="sourceId : fallback statique — valeur {0!r} invalide (type {1}, attendu: entier natif ou 'RefSource:X')",
        msg_valid_col="",
        msg_valid_fallback="valeur unique pour tous les désordres",
        msg_fallback_missing="facultatif",
    )


def _diag_type_desordre(cols, gdf, rows, errors, warnings):
    _diag_generic_code(
        rows, errors, warnings,
        cols, gdf,
        COL_TYPE_DESORDRE_ID,
        "typeDesordreId",
        is_valid_type_desordre,
        normalize_type_desordre,
        msg_invalid_col="valeurs invalides détectées",
        msg_invalid_fallback="typeDesordreId : fallback statique — valeur {0!r} invalide (type {1}, attendu: entier natif ou 'RefTypeDesordre:X')",
        msg_valid_col="vérifier categorieDesordreId",
        msg_valid_fallback="vérifier categorieDesordreId",
        msg_fallback_missing="facultatif",
        msg_relationship="- typeDesordreId: encodage expérimental: vérifier la compatibilité avec categorieDesordreId.",
        experimental=True,
    )


def _diag_categorie_desordre(cols, gdf, rows, errors, warnings):
    _diag_generic_code(
        rows, errors, warnings,
        cols, gdf,
        COL_CATEGORIE_DESORDRE_ID,
        "categorieDesordreId",
        is_valid_categorie_desordre,
        normalize_categorie_desordre,
        msg_invalid_col="valeurs invalides détectées",
        msg_invalid_fallback="categorieDesordreId : fallback statique — valeur {0!r} invalide (type {1}, attendu: entier natif ou 'RefCategorieDesordre:X')",
        msg_valid_col="vérifier typeDesordreId",
        msg_valid_fallback="vérifier typeDesordreId",
        msg_fallback_missing="facultatif",
        msg_relationship="- categorieDesordreId: encodage expérimental: vérifier la compatibilité avec typeDesordreId.",
        experimental=True,
    )


def _diag_positions(cols, gdf, rows, errors):
    try:
        geom = gdf.geometry.dropna().iloc[0] if hasattr(gdf, "geometry") and gdf.geometry.notna().any() else None
        geom_type = geom.geom_type if geom else None
    except Exception:
        geom_type = None

    if geom_type == "Point":
        rows.append(["positionDebut", "POINT (x_debut, y_debut)", "inféré du GPKG", "tous les désordres sont des points", "oui"])
        rows.append(["positionFin", "positionDebut", "inféré du GPKG", "tous les désordres sont des points", "oui"])

    elif geom_type == "LineString":
        rows.append(["positionDebut", "POINT (x_debut, y_debut)", "inféré du GPKG", "tous les désordres sont des lignes", "oui"])
        rows.append(["positionFin", "POINT (x_fin, y_fin)", "inféré du GPKG", "tous les désordres sont des lignes", "oui"])

    else:
        errors.append("geometryMode : colonne 'geometry' — géométrie non prise en charge (POINT ou LINESTRING attendu)")
        rows.append(["positionDebut", "???", "géométrie non prise en charge", "erreur", "non"])
        rows.append(["positionFin", "???", "géométrie non prise en charge", "erreur", "non"])


def _diag_dates(cols, gdf, rows, errors, gpkg_schema):
    df_row = None  # ligne consolidée pour date_fin

    # date_debut
    ctype = gpkg_schema.get(COL_DATE_DEBUT, None)
    have_dd = False
    have_df = False
    dd_val = None
    df_val = None

    if exists(COL_DATE_DEBUT, cols):
        _mark(COL_DATE_DEBUT)
        if ctype != "date":
            rows.append(["date_debut", q(COL_DATE_DEBUT), "colonne GPKG", f"type GPKG incorrect: {ctype}", "non"])
            errors.append(f"date_debut : colonne '{COL_DATE_DEBUT}' — type GPKG incorrect (date attendu)")
        else:
            if gdf[COL_DATE_DEBUT].isna().any():
                rows.append(["date_debut", q(COL_DATE_DEBUT), "colonne GPKG", "NULL détecté", "non"])
                errors.append(f"date_debut : colonne '{COL_DATE_DEBUT}' — contient des valeurs NULL")
            else:
                rows.append(["date_debut", q(COL_DATE_DEBUT), "colonne GPKG", "dates valides sans NULL", "oui"])
                have_dd = True
                dd_val = gdf[COL_DATE_DEBUT]
    else:
        fb = str(COL_DATE_DEBUT).strip()
        if is_valid_iso_date(fb):
            rows.append(["date_debut", fb, "entête du script", "date unique", "oui"])
            have_dd = True
            dd_val = fb
        elif fb == "":
            rows.append(["date_debut", "", "entête du script", "valeur vide", "non"])
            errors.append("date_debut : fallback statique — valeur vide interdite")
        else:
            rows.append(["date_debut", fb, "entête du script", "date invalide", "non"])
            errors.append(f"date_debut : fallback statique — date invalide (valeur fournie : {fb})")

    # date_fin
    ctype = gpkg_schema.get(COL_DATE_FIN, None)
    if exists(COL_DATE_FIN, cols):
        _mark(COL_DATE_FIN)
        if ctype != "date":
            rows.append(["date_fin", q(COL_DATE_FIN), "colonne GPKG", f"type GPKG incorrect: {ctype}", "non"])
            errors.append(f"date_fin : colonne '{COL_DATE_FIN}' — type GPKG incorrect (date attendu)")
        else:
            # on ne push pas tout de suite, on stocke dans df_row
            df_row = ["date_fin", q(COL_DATE_FIN), "colonne GPKG", "dates valides (NULL autorisés)", "oui"]
            have_df = True
            df_val = gdf[COL_DATE_FIN]
    else:
        fb = str(COL_DATE_FIN).strip()
        if is_valid_iso_date(fb):
            # valeur statique valide → on stocke aussi dans df_row
            df_row = ["date_fin", fb, "entête du script", "date unique", "oui"]
            have_df = True
            df_val = fb
        elif fb == "":
            rows.append(["date_fin", "", "entête du script", "facultatif", "oui"])
        else:
            rows.append(["date_fin", fb, "entête du script", "date invalide", "non"])
            errors.append(f"date_fin : fallback statique — date invalide (valeur fournie : {fb})")

    # test relationnel final
    if have_dd and have_df and df_row is not None:
        try:
            def _norm(val):
                if isinstance(val, str):
                    return datetime.date.fromisoformat(val)
                if hasattr(val, "dt"):
                    return val.dt.date
                return val

            def _is_seq(x):
                return hasattr(x, "__iter__") and not isinstance(x, (str, bytes, datetime.date))

            dd = _norm(dd_val)
            df = _norm(df_val)

            dd_is_seq = _is_seq(dd)
            df_is_seq = _is_seq(df)

            conflict = False

            if dd_is_seq or df_is_seq:
                # On rend les deux comparables en listes
                dd_list = list(dd) if dd_is_seq else [dd] * (len(df) if df_is_seq else 1)
                df_list = list(df) if df_is_seq else [df] * (len(dd) if dd_is_seq else 1)

                # Boucle universelle
                for i, (db, df_) in enumerate(zip(dd_list, df_list)):
                    if db and df_ and df_ < db:
                        errors.append(f"dates inconsistantes ligne {i}: date_fin ({df_}) < date_debut ({db})")
                        conflict = True
            else:
                # Les deux scalaires
                if df < dd:
                    errors.append(f"dates inconsistantes: date_fin ({df}) < date_debut ({dd})")
                    conflict = True

            if conflict:
                df_row[3] = "date_fin < date_debut"
                df_row[4] = "non"

        except Exception:
            pass

    # ajout unique de la ligne date_fin si elle a été construite
    if df_row is not None:
        rows.append(df_row)


# ======================================================================
#  FONCTION PUBLIQUE
# ======================================================================
def diagnose_mapping(available_cols: List[str], gdf, gpkg_schema, contacts) -> Tuple[List[List[str]], List[str], List[str]]:
    cols = list(available_cols or [])
    rows, errors, warnings = [], [], []
    contact_ids = {str(c["contactId"]) for c in contacts}
    _diag_base_metadata(rows, errors, warnings)
    _diag_text_columns(cols, gdf, rows, errors)
    _diag_linear_id(cols, gdf, rows, errors)
    _diag_author(cols, gdf, rows, errors, contact_ids)
    _diag_type_desordre(cols, gdf, rows, errors, warnings)
    _diag_categorie_desordre(cols, gdf, rows, errors, warnings)
    _diag_source(cols, gdf, rows, errors)
    _diag_cote(cols, gdf, rows, errors)
    _diag_positions(cols, gdf, rows, errors)
    _diag_dates(cols, gdf, rows, errors, gpkg_schema)

    return rows, errors, warnings

diagnose_mapping.USED_COLUMNS = USED_COLUMNS

