# -*- coding: utf-8 -*-
import os
import re
import sys
import argparse
from .diag_des import diagnose_mapping
from .diag_obs import validate_observation_structure
from .diag_pho import detect_photo_patterns, validate_photo_structure
from .json_builder import generate_json
from .relocate import process_photo_migration
from .check_dates import temporal_constraints

from .exceptions import (
    SirsError, CouchDBError, GpkgReadError,
    DataNotFoundError, ExtractProcessError, GpkgWriteError,
    DataValidationError, PhotoMigrationError, GpkgUpdateError,
    UserCancelled, JsonExportError
)

from .couchdb import (
    couchdb_database_exists, get_all_troncons, get_all_contacts,
    couchdb_upload_bulk, validate_troncons_key, choose_join_key,
    resolve_linear_id, TRONCONS_MISSING, get_all_users
)

from .helpers import (
    read_gpkg_columns, red, yellow, bold,
    print_mapping_verbose, is_valid_uuid, print_error_block,
    print_unused_columns,
    check_no_empty_columns, validate_fallbacks,
    apply_normalization_after_validation
)

from .config_loader import CONFIG, PROJECT_DIR
COUCH_DB                    = CONFIG["COUCH_DB"]
GPKG_FILE                   = CONFIG["GPKG_FILE"]
GPKG_LAYER                  = CONFIG["GPKG_LAYER"]
GPKG_PATH                   = CONFIG["GPKG_PATH"]
COL_TRONCONS                = CONFIG["COL_TRONCONS"]
COL_LINEAR_ID               = CONFIG["COL_LINEAR_ID"]
COL_POSITION_ID             = CONFIG["COL_POSITION_ID"]
COL_COTE_ID                 = CONFIG["COL_COTE_ID"]
COL_SOURCE_ID               = CONFIG["COL_SOURCE_ID"]
COL_CATEGORIE_DESORDRE_ID   = CONFIG["COL_CATEGORIE_DESORDRE_ID"]
COL_TYPE_DESORDRE_ID        = CONFIG["COL_TYPE_DESORDRE_ID"]

def process_extract_only(gdf, troncons):
    # 1) Valider COL_TRONCONS
    ok, mode = validate_troncons_key(COL_TRONCONS, gdf)
    if not ok:
        raise ExtractProcessError(mode)
    TRONCONS_MODE = mode

    # 2) Préparer les valeurs de jointure
    col_existe_deja = COL_LINEAR_ID in gdf.columns

    try:
        if TRONCONS_MODE == "column":
            distinct_values = (
                gdf[COL_TRONCONS].astype(str).str.strip().unique().tolist()
            )
        else:
            distinct_values = [COL_TRONCONS.strip()]
    except Exception as e:
        raise ExtractProcessError(f"⛔ Erreur lecture COL_TRONCONS : {e}")

    join_key = choose_join_key(distinct_values, troncons)

    # 3) Effectuer la jointure
    try:
        if TRONCONS_MODE == "column":
            gdf[COL_LINEAR_ID] = gdf[COL_TRONCONS].apply(
                lambda v: resolve_linear_id(str(v).strip(), troncons, join_key)
            )
        else:
            static_value = COL_TRONCONS.strip()
            gdf[COL_LINEAR_ID] = resolve_linear_id(
                static_value, troncons, join_key
            )
    except Exception as e:
        raise ExtractProcessError(f"⛔ Erreur durant la résolution des linearId : {e}")

    # 4) Rapport des tronçons introuvables
    if TRONCONS_MISSING:
        missing_list = sorted(TRONCONS_MISSING)
        msg = ["⛔ Certaines valeurs de COL_TRONCONS n'ont pas pu être rattachées :", *missing_list]
        raise ExtractProcessError(msg)

    # 5) Confirmer l’écrasement éventuel
    if col_existe_deja:
        print()
        print(f"⚠️ La colonne '{COL_LINEAR_ID}' existe déjà dans le GPKG!  Souhaitez-vous l'écraser?")
        print("(1) écraser")
        print("(2) annuler")
        try:
            resp = input("Votre choix: ").strip().lower()
        except EOFError:
            raise UserCancelled(bold(f"❌ Mise à jour de {GPKG_FILE} annulée."))
        if resp not in ("1","o","oui","y","yes"):
            raise UserCancelled(bold(f"❌ Mise à jour de {GPKG_FILE} annulée."))

    # 6) Vérifier les linearId générés
    vals = gdf[COL_LINEAR_ID].dropna().astype(str)

    invalid = [v for v in vals if not is_valid_uuid(v)]
    if invalid:
        raise ExtractProcessError(
            f"⛔ linearId invalides détectés (format UUID) : {invalid[:10]}"
        )

    lengths = {len(v) for v in vals}
    if not lengths.issubset({32, 36}):
        raise ExtractProcessError(
            f"⛔ Longueur invalide dans linearId : {sorted(lengths)}"
        )

    uuid_valids = {t["linearId"] for t in troncons}
    unknown = [v for v in vals if v not in uuid_valids]
    if unknown:
        raise ExtractProcessError(
            f"⛔ Certains linearId ne correspondent pas à CouchDB : {unknown[:10]}"
        )

    print()
    print(f"⚙️ Ajout des linearId à {GPKG_FILE}")
    return gdf


def rewrite_gpkg(gdf, gpkg_schema, orig_geom_type, orig_crs):
    import fiona
    import pandas as pd
    from shapely.geometry import mapping

    # Colonnes qui doivent être stockées en string
    REF_COLUMNS = {
        COL_POSITION_ID,
        COL_COTE_ID,
        COL_SOURCE_ID,
        COL_CATEGORIE_DESORDRE_ID,
        COL_TYPE_DESORDRE_ID
    }

    # Adapter le schema GPKG pour correspondre aux valeurs normalisées
    for col in list(gpkg_schema.keys()):
        if col in REF_COLUMNS:
            gpkg_schema[col] = "str"

    # Suppression de l'ancien fichier
    try:
        os.remove(GPKG_PATH)
    except Exception as e:
        raise GpkgWriteError(
            [f"⛔ Impossible de supprimer l’ancien GPKG '{GPKG_PATH}' :", str(e)]
        )

    # Création du nouveau GPKG
    try:
        dst = fiona.open(
            GPKG_PATH,
            mode="w",
            driver="GPKG",
            layer=GPKG_LAYER,
            schema={"geometry": orig_geom_type, "properties": gpkg_schema},
            crs=orig_crs,
        )
    except Exception as e:
        raise GpkgWriteError(
            [f"⛔ Impossible de créer le GPKG '{GPKG_PATH}' :", str(e)]
        )

    # Écriture des données
    try:
        with dst:
            for _, row in gdf.iterrows():
                props = {}
                for col, ctype in gpkg_schema.items():
                    if col == "geometry":
                        continue
                    val = row[col] if col in row else None

                    # Gestion du NULL
                    if pd.isna(val):
                        props[col] = None

                    # Gestion ISO date
                    elif ctype == "date":
                        props[col] = (
                            val.strftime("%Y-%m-%d")
                            if hasattr(val, "strftime")
                            else str(val)
                        )

                    # Colonnes normalisées → string forcée
                    elif col in REF_COLUMNS:
                        props[col] = str(val)

                    # Cas normal
                    else:
                        props[col] = val

                dst.write(
                    {
                        "geometry": mapping(row.geometry)
                        if row.geometry is not None
                        else None,
                        "properties": props,
                    }
                )
    except Exception as e:
        raise GpkgWriteError(
            [f"⛔ Erreur lors de l’écriture des données dans le GPKG '{GPKG_PATH}' :", str(e)]
        )

    print()
    print(bold(f"✅ Le fichier {GPKG_FILE} a été mis à jour."))
    return 0


# ------------------------------------------------------------
#  MAIN
# ------------------------------------------------------------
def real_main(argv=None):

    # argparse
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--extract",
        action="store_true",
        help="extraction tronçons + contacts uniquement",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="exécute le pipeline complet avec import couchdb",
    )
    args = parser.parse_args(argv)

    EXTRACT_ONLY = args.extract
    DO_UPLOAD = args.upload
    
    # tout sera loggé dans un fichier
    LOGFILE = os.path.join(PROJECT_DIR, f"{GPKG_LAYER}.log")
    log = open(LOGFILE, "w", encoding="utf-8")
    
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    class Tee:
        def __init__(self, console_stream, log_stream):
            self.console_stream = console_stream
            self.log_stream = log_stream

        def write(self, data):
            self.console_stream.write(data)
            self.console_stream.flush()

            cleaned = ansi_escape.sub('', data)
            self.log_stream.write(cleaned)
            self.log_stream.flush()

        def flush(self):
            self.console_stream.flush()
            self.log_stream.flush()

    sys.stdout = Tee(sys.stdout, log)
    sys.stderr = Tee(sys.stderr, log)

    # connexion couchdb
    print()
    print(f"⚙️ Tentative de connection à la base '{COUCH_DB}'")
    try:
        couchdb_database_exists()
        print()
        print(f"✅ '{COUCH_DB}' est connectée.")
    except CouchDBError:
        raise

    # extraction tronçons + contacts
    try:
        troncons = get_all_troncons(write_txt=EXTRACT_ONLY)
    except DataNotFoundError:
        raise
    try:
        users = get_all_users(write_txt=EXTRACT_ONLY)
    except DataNotFoundError:
        raise
    try:
        contacts = get_all_contacts(write_txt=EXTRACT_ONLY)
    except DataNotFoundError:
        raise				
    if EXTRACT_ONLY:
        print()
        print(f"✅ Les tronçons et leur linearId sont disponibles dans {COUCH_DB}_linearId.txt")
        print()
        print(f"✅ Les utilisateurs de la base (auteurs) et leur _id sont disponibles dans {COUCH_DB}_userId.txt")		
        print()
        print(f"✅ Les contacts (observateurs, photographes) et leur _id sont disponibles dans {COUCH_DB}_contactId.txt")
		
    contact_ids = {str(c["contactId"]) for c in contacts}
    user_ids    = {str(u["userId"])   for u in users}

    # lecture gpkg
    print()
    print(f"⚙️ Lecture du fichier {GPKG_FILE}")
    try:
        cols, gdf = read_gpkg_columns(
            GPKG_PATH, GPKG_LAYER, return_gdf=True
        )
    except GpkgReadError:
        raise
    try:
        import fiona
        with fiona.open(GPKG_PATH, layer=GPKG_LAYER) as src:
            gpkg_schema = src.schema["properties"]
            orig_geom_type = src.schema["geometry"]
            orig_crs = src.crs
    except Exception as e:
        raise GpkgReadError(f"Fiona : {e}")

    # extraction des linearId et observateurId
    if EXTRACT_ONLY:
        try:
            gdf = process_extract_only(gdf, troncons)
        except ExtractProcessError:
            raise

        # mise à jour explicite du schéma pour COL_LINEAR_ID si nécessaire
        if COL_LINEAR_ID not in gpkg_schema:
            gpkg_schema[COL_LINEAR_ID] = "str"

        try:
            rewrite_gpkg(gdf, gpkg_schema, orig_geom_type, orig_crs)
            print()
        except GpkgWriteError:
            raise
        return
    
    print()
    print(f"⚙️ Vérifications préliminaires de {GPKG_FILE}...")	
	
    # les colonnes vides ne sont pas autorisées
    try:
        check_no_empty_columns(gdf)
    except DataValidationError:
        raise

    # validation fallbacks avec contacts ET utilisateurs
    validate_fallbacks(contact_ids, user_ids)		

    # démarrage du processus principal
    total_rows = len(gdf)
    total_cols = len(cols)

    print()
    print(f"📁 Le fichier comporte {total_cols} colonnes et {total_rows} lignes")

    print()
    print("📁 Colonnes disponibles :")
    print([c for c in cols if c != "geometry"])

    # diagnostic désordres
    rows, errors, warnings = diagnose_mapping(cols, gdf, gpkg_schema, user_ids)
    used_des_cols = diagnose_mapping.USED_COLUMNS
    print()
    print(bold("🔎 Analyse des champs désordres éditables:"))
    print()
    print_mapping_verbose(rows, errors, warnings)
    if errors:
        msg = ["⛔ Blocages détectés au niveau désordres → import impossible :", *errors]
        raise DataValidationError(msg)

    print()
    print(bold("ℹ️ Rappels:"))
    print('   "@class": "fr.sirs.core.model.Desordre" est ajouté automatiquement.')
    print("   Les champs _id, _rev, dateMaj, lastUpdateAuthor sont calculés à l'import.")
    print("   Idem pour les bornes géographiques et geometry.")
    print("   Les champs prDebut et prFin sont également recalculés à l'import.")


    if warnings:
        print()
        print(bold(yellow("⚠️ Warnings:")))
        for w in warnings:
            print(yellow(f"   {w}"))

    print()
    print("✅ La structure des données de désordres est correcte!")

    print()
    print(bold("🔎 Analyse des observations :"))

    # diagnostic observations
    obs_data = validate_observation_structure(
        cols, gdf, gpkg_schema, contact_ids
    )

    obs_errors = obs_data["errors"]
    used_obs_columns = obs_data["used_columns"]
    invalid_obs_columns = obs_data["invalid_obs_columns"]
    fallback_observateur = obs_data["fallback_observateur"]
    fallback_urgence = obs_data["fallback_urgence"]
    fallback_suite = obs_data["fallback_suite"]
    fallback_nb_desordres = obs_data["fallback_nb_desordres"]
    observations = obs_data["patterns"]["observations"]

    # diagnostic photos
    photo_patterns = detect_photo_patterns(cols)
    observation_dates = {
        obs: gdf[f"{obs}_date"]
        for obs in observations
        if f"{obs}_date" in gdf.columns
    }

    photo_data = validate_photo_structure(
        photo_patterns, cols, gdf, observation_dates, gpkg_schema, contact_ids
    )

    used_photo_columns = photo_data["used_columns"]
    invalid_photo_columns = photo_data["invalid_photo_columns"]
    photo_errors = photo_data["errors"]

    fallback_photograph = photo_data["fallback_photograph"]
    fallback_photo_date = photo_data["fallback_photo_date"]
    fallback_photo_geom = photo_data["fallback_photo_geom"]

    # affichage obs + photos
    print()
    if not observations:
        print(yellow("⚠️ Aucune observation détectée !"))
    else:
        print(f"Nombre d’observations correctes : {len(observations)}")
        for obs, suffixes in observations.items():
            print(bold(f"• {obs}"))
            print("    - champs :", ", ".join(suffixes))

            if fallback_observateur.get(obs, False):
                print("            + observateurId par défaut utilisé")
            if fallback_urgence.get(obs, False):
                print("            + urgenceId par défaut utilisé")
            if fallback_suite.get(obs, False):
                print("            + suiteApporterId par défaut utilisé")
            if fallback_nb_desordres.get(obs, False):
                print("            + nombreDesordres par défaut utilisé")

            linked_photos = {
                pho: suf
                for (o, pho), suf in photo_patterns.items()
                if o == obs
            }
            if linked_photos:
                print("    - photos :")
                for pho, suf in linked_photos.items():
                    print(f"        • {pho} :", ", ".join(suf))

                    if fallback_photograph.get((obs, pho), False):
                        print("            + photographeId par défaut utilisé")

                    if fallback_photo_date.get((obs, pho), False):
                        print("            + date de l’observation réutilisée")

                    if fallback_photo_geom.get((obs, pho), False):
                        print("            + coordonnées du désordre parent appliquées")
            else:
                print("    - photos : (aucune)")


    # erreurs obs + photos
    printed = False
    if obs_errors:
        print()
        print_error_block(
            "⛔ erreurs au niveau observation → import impossible :",
            obs_errors,
            red
        )
        printed = True
    if photo_errors:
        print()		
        print_error_block(
            "⛔ erreurs au niveau photo → import impossible :",
            photo_errors,
            red
        )
        printed = True
    if printed:
        print()
        return 3

    # colonnes non reconnues
    invalid_all = invalid_obs_columns + invalid_photo_columns
    if invalid_all:
        print()
        print(
            bold(
                yellow(
                    "⚠️ colonnes suspectes (suffixe non reconnu) :"
                )
            )
        )
        print(yellow("   " + ", ".join(invalid_all)))

    # colonnes non utilisées
    used_obs_pho = used_obs_columns | used_photo_columns
    print()
    print_unused_columns(
        cols, used_des_cols, used_obs_pho, invalid_all
    )

    # mise à jour des références
    print()
    print("⚙️ Normalisation des valeurs référentielles (type RefXXX:n)")
    gdf = apply_normalization_after_validation(gdf)

    REF_COLUMNS = {
        COL_POSITION_ID,
        COL_COTE_ID,
        COL_SOURCE_ID,
        COL_CATEGORIE_DESORDRE_ID,
        COL_TYPE_DESORDRE_ID
    }

    for col in list(gpkg_schema.keys()):
        if col in REF_COLUMNS:
            gpkg_schema[col] = "str"


    # validation photos et migration
    print()
    print("⚙️ Vérification des chemins et de l'arborescence photos")
    try:
        gdf = process_photo_migration(gdf)
    except (PhotoMigrationError, GpkgUpdateError) as e:
        raise

    # mise à jour du GPKG
    try:
        rewrite_gpkg(gdf, gpkg_schema, orig_geom_type, orig_crs)
    except GpkgWriteError:
        raise

    # temporalité photos
    date_errors = temporal_constraints(
        gdf,
        observations,
        observation_dates,
        photo_patterns,
        gpkg_schema,
    )
    if date_errors:
        print_error_block(
            "⛔ erreurs temporelles → import impossible :",
            date_errors,
            red,
        )
        print()
        return 3

    # export json
    patterns = {"observations": observations, "photos": photo_patterns}
    try:
        json_stats = generate_json(gdf, patterns)
    except JsonExportError:
        raise
    except Exception as e:
        msg = ["⛔ Erreur durant la génération du JSON :", str(e)]
        raise JsonExportError(msg)
    print()
    print(bold(f"✅ Un fichier {GPKG_LAYER}.json contenant {json_stats['written']} désordres a été généré."))
    print()

    # upload couchdb
    if not DO_UPLOAD:
        return 0

    try:
        ok, import_errors = couchdb_upload_bulk(json_stats["documents"])
    except CouchDBError as e:
        raise

    if ok:
        print(bold(f"✅ {len(json_stats['documents'])} documents importés dans couchdb."))
        print()
        return 0

    # ici : échec partiel ou total du _bulk_docs
    raise CouchDBError(
        ["⛔ Erreurs lors de l'import couchdb (_bulk_docs) :", *import_errors[:10]]
    )


def main(argv=None):
    try:
        real_main()
    except UserCancelled as e:
        print()
        msg = e.args[0] if e.args else ""
        if isinstance(msg, list):
            for line in msg:
                print(line)
        else:
            print(msg)
        print()
        sys.exit(0)
    except SirsError as e:
        print()
        err = e.args[0]
        if isinstance(err, list):
            print_error_block(err[0], err[1:], red)
        else:
            print(red(str(err)))
        print()
        print(bold("➡️ Veuillez corriger le problème et relancer le script."))
        print()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())






