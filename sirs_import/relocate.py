# -*- coding: utf-8 -*-
import os
import re
import uuid
import shutil
from datetime import datetime
from .helpers import bold, yellow
from .exceptions import UserCancelled, PhotoMigrationError, GpkgUpdateError
from .config_loader import CONFIG, PROJECT_DIR
COL_TRONCONS  = CONFIG["COL_TRONCONS"]
COL_DESIGNATION = CONFIG["COL_DESIGNATION"]
COL_LIBELLE     = CONFIG["COL_LIBELLE"]


# ======================================================================
# UTILITAIRES
# ======================================================================

# nettoie un nom de fichier en supprimant les caractères non autorisés
def _sanitize_name(name: str) -> str:
    if not isinstance(name, str):
        return "undefined"
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    return name


# sépare un nom de fichier en racine + extension
def _split_filename(fname: str):
    fname = str(fname).strip()
    if "." not in fname:
        return _sanitize_name(fname), ""
    root, ext = fname.rsplit(".", 1)
    root = _sanitize_name(root)
    ext = "." + ext
    return root, ext


# résout un chemin relatif en chemin absolu
def _resolve_absolute_path(raw: str) -> str:
    raw = str(raw).strip()
    if os.path.isabs(raw):
        return os.path.abspath(raw)
    return os.path.abspath(os.path.join(PROJECT_DIR, raw))


# teste l’existence d’un fichier
def _file_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False


# ======================================================================
# DIAGNOSTIC
# ======================================================================

# analyse la conformité des chemins photos dans le GDF
def _diagnose_paths(gdf):
    import pandas as pd
    photo_cols = [
        c for c in gdf.columns
        if "_pho" in c and c.endswith("_chemin")
    ]
    missing = []
    all_conform = True
    for _, row in gdf.iterrows():
        troncon = str(row.get(COL_TRONCONS, "")).strip()
        for col in photo_cols:
            raw = row.get(col)
            if raw is None or pd.isna(raw):
                continue
            raw_str = str(raw).replace("\\", "/").strip()
            if raw_str == "" or raw_str.lower() in ("na", "nan", "none", "<na>"):
                continue
            if not raw_str.startswith(f"{troncon}/"):
                all_conform = False
            abs_path = _resolve_absolute_path(raw_str)
            if not _file_exists(abs_path):
                missing.append(abs_path)
    if missing:
        return {"status": "missing", "missing": missing}
    if all_conform:
        return {"status": "conform", "missing": []}
    return {"status": "needs_migration", "missing": []}


# ======================================================================
# DUPLICATIONS — DÉTECTION
# ======================================================================

# crée une map des fichiers vers leurs références multiples dans le gdf
def collect_photo_references(gdf):
    photo_cols = [c for c in gdf.columns if "_pho" in c and c.endswith("_chemin")]
    refmap = {}
    for idx, row in gdf.iterrows():
        obs_id = idx
        troncon = str(row.get(COL_TRONCONS)).strip()
        desordre = None
        if COL_DESIGNATION in gdf.columns:
            val = row.get(COL_DESIGNATION)
            if isinstance(val, str) and val.strip():
                desordre = val.strip()
        if desordre is None and COL_LIBELLE in gdf.columns:
            val = row.get(COL_LIBELLE)
            if isinstance(val, str) and val.strip():
                desordre = val.strip()
        for col in photo_cols:
            raw = row.get(col)
            if not raw:
                continue
            abs_path = os.path.abspath(_resolve_absolute_path(raw))
            refmap.setdefault(abs_path, []).append(
                {"obs_id": obs_id, "troncon": troncon, "desordre": desordre, "col": col}
            )
    return refmap


# classe les doublons selon les catégories 1 à 4
def _classify_duplications(refmap):
    cat1 = {}
    cat2 = {}
    cat3 = {}
    cat4 = {}
    for abs_path, occs in refmap.items():
        if len(occs) < 2:
            continue
        obs_ids = set(o["obs_id"] for o in occs)
        troncons = set(o["troncon"] for o in occs)
        desordres = set((o["desordre"] or "None") for o in occs)
        if len(troncons) > 1:
            cat4[abs_path] = occs
            continue
        if len(obs_ids) == 1:
            cat1[abs_path] = occs
            continue
        if len(desordres) == 1:
            cat2[abs_path] = occs
            continue
        cat3[abs_path] = occs
    return cat1, cat2, cat3, cat4


# formatte une occurrence de duplication en string lisible
def _fmt_occ(o):
    d = o["desordre"] if o["desordre"] else "None"
    return f"({o['troncon']}:{d}:{o['col']})"


# affiche un rapport complet de duplications
def _print_duplication_report(cat1, cat2, cat3, cat4):
    total = len(cat1) + len(cat2) + len(cat3) + len(cat4)
    print()
    print(bold(yellow(f"⚠️ {total} fichiers référencés plusieurs fois.")))

    if cat1:
        print()
        print(bold(yellow("# Photos utilisées plusieurs fois dans la même observation")))
        for path, occs in cat1.items():
            print(yellow(f"  - {path}"))
            print(yellow("      refs:"))
            for o in occs:
                print(yellow(f"        {_fmt_occ(o)}"))

    if cat2:
        print()
        print(bold(yellow("# Photos utilisées plusieurs fois dans le même désordre")))
        for path, occs in cat2.items():
            print(yellow(f"  - {path}"))
            print(yellow("      refs:"))
            for o in occs:
                print(yellow(f"        {_fmt_occ(o)}"))

    if cat3:
        print()
        print(bold(yellow("# Photos utilisées sur plusieurs désordres d’un même tronçon")))
        for path, occs in cat3.items():
            print(yellow(f"  - {path}"))
            print(yellow("      refs:"))
            for o in occs:
                print(yellow(f"        {_fmt_occ(o)}"))

    if cat4:
        print()
        print(bold(yellow("# Photos utilisées sur plusieurs tronçons différents.")))
        for path, occs in cat4.items():
            print(yellow(f"  - {path}"))
            print(yellow("      refs:"))
            for o in occs:
                print(yellow(f"        {_fmt_occ(o)}"))
        print(yellow("❗ Duplication physique des photos nécessaire pour conserver le schéma SIRS."))

    return {
        "has_duplication": total > 0,
        "has_cross_troncon": len(cat4) > 0
    }



# ======================================================================
# MIGRATION
# ======================================================================

# simule la relocalisation et détecte les collisions potentielles
def _simulate_relocation(gdf, filename_strategy="keep"):
    import pandas as pd
    photo_cols = [c for c in gdf.columns if "_pho" in c and c.endswith("_chemin")]
    mapping = {}
    collisions = []
    for _, row in gdf.iterrows():
        troncon = str(row.get(COL_TRONCONS, "undefined")).strip()
        for col in photo_cols:
            raw = row.get(col)
            if not raw:
                continue
            old_abs = _resolve_absolute_path(raw)
            base = os.path.basename(old_abs)
            root, ext = _split_filename(base)
            ext = ext.lower()
            if filename_strategy == "keep":
                pass
            elif filename_strategy == "prefix_date":
                obs_date_col = col.replace("_chemin", "_date")
                d = row.get(obs_date_col)
                prefix = "00000000_" if pd.isna(d) else d.strftime("%Y%m%d") + "_"
                root = prefix + root
            elif filename_strategy == "uuid":
                root = uuid.uuid4().hex
            fname = root + ext
            new_abs = os.path.join(PROJECT_DIR, troncon, fname)
            mapping.setdefault(old_abs, []).append(new_abs)
    all_dests = []
    for lst in mapping.values():
        for dest in lst:
            all_dests.append(os.path.normpath(dest))
    counts = {}
    for d in all_dests:
        counts[d] = counts.get(d, 0) + 1
    collisions = [d for d, n in counts.items() if n > 1]
    return mapping, collisions


# applique la relocalisation des fichiers
def _apply_relocation(mapping):
    for old_abs, new_list in mapping.items():
        old_abs_norm = os.path.normpath(os.path.abspath(old_abs))
        new_list_unique = []
        for x in new_list:
            x = os.path.normpath(os.path.abspath(x))
            if x not in new_list_unique:
                new_list_unique.append(x)
        if len(new_list_unique) == 1:
            new_abs_norm = new_list_unique[0]
            try:
                if os.path.samefile(old_abs_norm, new_abs_norm):
                    continue
            except:
                if old_abs_norm.lower() == new_abs_norm.lower():
                    continue
            os.makedirs(os.path.dirname(new_abs_norm), exist_ok=True)
            shutil.move(old_abs_norm, new_abs_norm)
            continue
        keep_src = False
        for new_abs in new_list_unique:
            new_abs_norm = os.path.normpath(os.path.abspath(new_abs))
            try:
                if os.path.samefile(old_abs_norm, new_abs_norm):
                    keep_src = True
                    continue
            except:
                if old_abs_norm.lower() == new_abs_norm.lower():
                    keep_src = True
                    continue
            os.makedirs(os.path.dirname(new_abs_norm), exist_ok=True)
            shutil.copy2(old_abs_norm, new_abs_norm)
        if not keep_src:
            try:
                os.remove(old_abs_norm)
            except:
                pass


# ======================================================================
# MISE À JOUR DU GDF
# ======================================================================

def _update_gdf(gdf, mapping):
    photo_cols = [c for c in gdf.columns if "_pho" in c and c.endswith("_chemin")]
    for idx, row in gdf.iterrows():
        troncon = str(row.get(COL_TRONCONS, "undefined")).strip()
        for col in photo_cols:
            raw = row.get(col)
            if not raw:
                continue
            old_abs = os.path.abspath(_resolve_absolute_path(raw))
            if old_abs not in mapping:
                continue
            for cand in mapping[old_abs]:
                rel = os.path.relpath(cand, PROJECT_DIR)

                # colonne incompatible (sécurité)
                if col.endswith("_date"):
                    raise GpkgUpdateError([
                        "❗ ERREUR de conversion dans _update_gdf()",
                        f"Tentative d’écriture d’un chemin dans une colonne date : {col}",
                        f"Ligne={idx}, valeur={rel}",
                        "Corrigez la structure du GPKG."
                    ])

                if re.match(r"^\d{4}-\d{2}-\d{2}$", rel):
                    raise GpkgUpdateError([
                        "❗ ERREUR de conversion dans _update_gdf()",
                        f"Tentative d’écriture d’une date dans une colonne chemin : {col}",
                        f"Ligne={idx}, valeur={rel}",
                        "Corrigez la structure du GPKG."
                    ])

                if rel.startswith(f"{troncon}/"):
                    gdf.at[idx, col] = rel
                    break

    return gdf

# ======================================================================
# MAPPING
# ======================================================================
def _generate_target_mapping(gdf, collisions, strategy_for_collisions, strategy_other):
    import pandas as pd

    photo_cols = [c for c in gdf.columns if "_pho" in c and c.endswith("_chemin")]
    mapping = {}

    # liste normalisée des chemins en collision
    collisions_norm = set(os.path.normpath(os.path.abspath(c)) for c in collisions)

    for _, row in gdf.iterrows():
        troncon = str(row.get(COL_TRONCONS, "undefined")).strip()

        for col in photo_cols:
            raw = row.get(col)
            if not raw:
                continue

            old_abs = os.path.abspath(_resolve_absolute_path(raw))
            base = os.path.basename(old_abs)
            root, ext = _split_filename(base)
            ext = ext.lower()

            # on reconstruit new_abs "keep"
            fname_keep = root + ext
            new_abs_keep = os.path.normpath(os.path.join(PROJECT_DIR, troncon, fname_keep))

            # ce fichier est-il affecté par collision ?
            in_collision = (new_abs_keep in collisions_norm)

            strategy = strategy_for_collisions if in_collision else strategy_other

            if strategy == "keep":
                fname = fname_keep

            elif strategy == "prefix_date":
                obs_date_col = col.replace("_chemin", "_date")
                d = row.get(obs_date_col)
                prefix = "00000000_" if pd.isna(d) else d.strftime("%Y%m%d") + "_"
                fname = prefix + root + ext

            elif strategy == "uuid":
                fname = uuid.uuid4().hex + ext

            else:
                raise ValueError(f"unknown strategy: {strategy}")

            new_abs = os.path.join(PROJECT_DIR, troncon, fname)
            mapping.setdefault(old_abs, []).append(new_abs)

    return mapping


# ======================================================================
# PIPELINE COMPLET
# ======================================================================

def process_photo_migration(gdf):
    # 1) Vérification existence physique
    diag = _diagnose_paths(gdf)

    if diag["status"] == "missing":
        raise PhotoMigrationError(
            ["⛔ Ces photos sont introuvables physiquement :"] + diag["missing"]
        )

    if diag["status"] == "conform":
        print()
        print("✅ Les chemins photos et l'arboresence sont déjà conformes. Aucune migration nécessaire.")
        return gdf

    # si on arrive ici :
    # diag["status"] == "needs_migration"
    print("⚙️ Migration requise : chemins non conformes.")


    # 2) Détection des doublons
    refmap = collect_photo_references(gdf)
    cat1, cat2, cat3, cat4 = _classify_duplications(refmap)
    if any([cat1, cat2, cat3, cat4]):
        _print_duplication_report(cat1, cat2, cat3, cat4)
        print()
        if cat4:
            print("Si cet usage multiple des photos est intentionnel et que vous acceptez leur duplication, vous pouvez continuer.")
            print("Sinon, corrigez votre fichier avant migration.")
        else:
            print("Si cet usage multiple des photos est intentionnel, vous pouvez continuer.")
            print("Sinon, corrigez votre fichier avant migration.")
        print("(1) continuer")
        print("(2) annuler")
        try:
            resp = input("Votre choix: ").strip().lower()
        except EOFError:
            raise UserCancelled(bold("❌ Migration annulée"))
        if resp not in ("1","o","oui","y","yes"):
            raise UserCancelled(bold("❌ Migration annulée"))

    # 3) Cas sans collision → KEEP
    mapping, collisions = _simulate_relocation(gdf, filename_strategy="keep")
    if not collisions:
        print()
        print("📁 Migration possible sans renommage.")
        print("(1) continuer")
        print("(2) annuler")
        try:
            resp = input("Votre choix: ").strip().lower()
        except EOFError:
            raise UserCancelled(bold("❌ Migration annulée"))
        if resp not in ("1","o","oui","y","yes"):
            raise UserCancelled(bold("❌ Migration annulée"))

        try:
            _apply_relocation(mapping)
            gdf = _update_gdf(gdf, mapping)
            print()
            print("✅ Migration photo terminée.")
        except Exception as e:
            raise PhotoMigrationError(
                ["⛔ Erreur durant la migration des photos :", str(e)]
            )
        return gdf

    # 4) Collisions → test prefix_date
    mapping_date, collisions_date = _simulate_relocation(gdf, filename_strategy="prefix_date")
    if not collisions_date:
        print()
        print(bold(yellow("⚠️ Il faut rajouter la date comme préfixe ou renommer les fichiers avec des UUIDs pour éviter les collisions.")))
        print("(1) Rajouter le préfixe date aux fichiers problématiques uniquement")
        print("(2) Rajouter le préfixe date à tous les fichiers")
        print("(3) Renommer les fichiers problématiques avec un UUID")
        print("(4) Renommer tous les fichiers avec un UUID")
        try:
            resp = input("Votre choix: ").strip().lower()
        except EOFError:
            raise UserCancelled("❌ Migration annulée")
        if resp == "1":
            mapping2 = _generate_target_mapping(gdf, collisions, strategy_for_collisions="prefix_date", strategy_other="keep")
        elif resp == "2":
            mapping2 = _generate_target_mapping(gdf, collisions, strategy_for_collisions="prefix_date", strategy_other="prefix_date")
        elif resp == "3":
            mapping2 = _generate_target_mapping(gdf, collisions, strategy_for_collisions="uuid", strategy_other="keep")
        elif resp == "4":
            mapping2 = _generate_target_mapping(gdf, collisions, strategy_for_collisions="uuid", strategy_other="uuid")
        else:
            raise UserCancelled(bold("❌ Migration annulée"))

        try:
            _apply_relocation(mapping2)
            gdf = _update_gdf(gdf, mapping2)
            print()
            print("📁 Migration photo terminée.")
        except Exception as e:
            raise PhotoMigrationError(
                ["⛔ Erreur durant la migration des photos :", str(e)]
            )
        return gdf

    # 5) Prefix date ne suffit pas → UUID
    mapping_uuid, collisions_uuid = _simulate_relocation(gdf, filename_strategy="uuid")
    if not collisions_uuid:
        print()
        print("Il faut renommer les fichiers avec des UUIDs pour éviter les collisions.")
        print("(1) Renommer uniquement les fichiers problématiques avec un UUID")
        print("(2) Renommer tous les fichiers avec un UUID")
        try:
            resp = input("Votre choix: ").strip().lower()
        except EOFError:
            raise UserCancelled("❌ Migration annulée")
        if resp == "1":
            mapping2 = _generate_target_mapping(gdf, collisions, strategy_for_collisions="uuid", strategy_other="keep")
        elif resp == "2":
            mapping2 = _generate_target_mapping(gdf, collisions, strategy_for_collisions="uuid", strategy_other="uuid")
        else:
            raise UserCancelled(bold("❌ Migration annulée"))

        try:
            _apply_relocation(mapping2)
            gdf = _update_gdf(gdf, mapping2)
            print()
            print("📁 Migration photo terminée.")
        except Exception as e:
            raise PhotoMigrationError(
                ["⛔ Erreur durant la migration des photos :", str(e)]
            )
        return gdf

    # 6) Collisions même avec UUID (théoriquement impossible)
    raise PhotoMigrationError(
        ["⛔ Collisions impossibles à résoudre même avec UUID (improbable).",
         "Vérifiez les chemins et permissions disque."]
    )



