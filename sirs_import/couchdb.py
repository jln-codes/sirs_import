# -*- coding: utf-8 -*-
import os, csv
from .exceptions import CouchDBError, DataNotFoundError

from .config_loader import CONFIG, PROJECT_DIR
COUCH_DB   = CONFIG["COUCH_DB"]
COUCH_URL  = CONFIG["COUCH_URL"]
COUCH_USER = CONFIG["COUCH_USER"]
COUCH_PW   = CONFIG["COUCH_PW"]

TRONCONS_MISSING = set()

def couchdb_database_exists():
    import requests

    url = f"{COUCH_URL}/{COUCH_DB}"

    try:
        resp = requests.get(url, auth=(COUCH_USER, COUCH_PW), timeout=5)
    except Exception as e:
        raise CouchDBError(f"Impossible de joindre CouchDB ({COUCH_URL}) : {e}")

    if resp.status_code == 200:
        return

    if resp.status_code == 401:
        raise CouchDBError(f"Authentification refusée pour la base '{COUCH_DB}'")

    if resp.status_code == 404:
        raise CouchDBError(f"La base CouchDB '{COUCH_DB}' est introuvable")

    raise CouchDBError(f"Erreur HTTP {resp.status_code} lors de l'accès à '{COUCH_DB}'")



def couchdb_find(selector, fields=None, limit=10000):
    import requests

    url = f"{COUCH_URL}/{COUCH_DB}/_find"
    payload = {"selector": selector, "limit": limit}
    if fields:
        payload["fields"] = fields

    try:
        r = requests.post(url, json=payload, auth=(COUCH_USER, COUCH_PW), timeout=10)
        r.raise_for_status()
        docs = r.json().get("docs", [])
        return docs
    except:
        pass

    # fallback si _find échoue ou n’est pas supporté
    url_all = f"{COUCH_URL}/{COUCH_DB}/_all_docs?include_docs=true"
    r2 = requests.get(url_all, auth=(COUCH_USER, COUCH_PW), timeout=20)
    r2.raise_for_status()
    return [row["doc"] for row in r2.json().get("rows", []) if row.get("doc")]



def get_all_troncons(write_txt=True):
    docs = couchdb_find(
        {"@class": "fr.sirs.core.model.TronconDigue"},
        fields=["_id", "designation", "libelle"]
    )

    if not docs:
        raise DataNotFoundError("Aucun tronçon trouvé dans CouchDB.")

    troncons = []
    for t in docs:
        obj = {"linearId": t.get("_id")}

        d = t.get("designation")
        if isinstance(d, str):
            d = d.strip()
        if d not in (None, "", [], {}):
            obj["designation"] = d

        l = t.get("libelle")
        if isinstance(l, str):
            l = l.strip()
        if l not in (None, "", [], {}):
            obj["libelle"] = l

        troncons.append(obj)

    if write_txt:
        fname = os.path.join(PROJECT_DIR, f"{COUCH_DB}_linearId.txt")
        with open(fname, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["linearId", "libelle", "designation"])
            for t in troncons:
                writer.writerow([
                    t["linearId"],
                    t.get("libelle", ""),
                    t.get("designation", "")
                ])

    return troncons


def get_all_contacts(write_txt=True):
    docs = couchdb_find(
        {"@class": "fr.sirs.core.model.Contact"},
        fields=["_id", "nom", "prenom"]
    )

    if not docs:
        raise DataNotFoundError("Aucun contact trouvé dans CouchDB.")

    contacts = []
    for c in docs:
        obj = {"contactId": c.get("_id")}

        nom = c.get("nom")
        if isinstance(nom, str):
            nom = nom.strip()
        if nom not in (None, "", [], {}):
            obj["nom"] = nom

        pren = c.get("prenom")
        if isinstance(pren, str):
            pren = pren.strip()
        if pren not in (None, "", [], {}):
            obj["prenom"] = pren

        contacts.append(obj)

    if write_txt:
        fname = os.path.join(PROJECT_DIR, f"{COUCH_DB}_contactId.txt")
        with open(fname, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["contactId", "nom", "prenom"])
            for c in contacts:
                writer.writerow([
                    c["contactId"],
                    c.get("nom", ""),
                    c.get("prenom", "")
                ])

    return contacts


def choose_join_key(values, troncons):
    count_lib = 0
    count_des = 0

    # comptages des correspondances
    for v in values:
        for t in troncons:
            if t.get("libelle") == v:
                count_lib += 1
            if t.get("designation") == v:
                count_des += 1

    # victoire simple
    if count_lib > count_des:
        return "libelle"
    if count_des > count_lib:
        return "designation"

    # égalité → détecter les valeurs sans correspondance
    for v in values:
        matched = any(
            t.get("libelle") == v or t.get("designation") == v
            for t in troncons
        )
        if not matched:
            TRONCONS_MISSING.add(v)

    # égalité → règle fixe lors d'un match ex æquo ou absence totale de match
    return "libelle"


def validate_troncons_key(col_troncons: str, gdf):
    # cas 1 : colonne trouvée
    if col_troncons in gdf.columns:
        col = gdf[col_troncons]
        null_mask = col.isna() | col.astype(str).str.strip().eq("")
        if null_mask.any():
            return False, f"La colonne '{col_troncons}' contient des valeurs vides ou NULL."
        return True, "column"

    # cas 2 : colonne non trouvée → informer clairement
    cols = ", ".join(gdf.columns)

    if isinstance(col_troncons, str) and col_troncons.strip() != "":
        print()
        print(yellow(f"⚠️ '{col_troncons}' n'est pas une colonne du GPKG et sera considérée comme une valeur statique."))  
        return True, "static"

    # cas 3 : valeur statique vide → erreur
    return False, (
        f"COL_TRONCONS ('{col_troncons}') est vide et ne correspond à aucune colonne du GPKG."
    )
	
	
def resolve_linear_id(value, troncons, key):
    v = str(value).strip()

    for t in troncons:
        if t.get(key) == v:
            return t["linearId"]

    # si on arrive ici → pas trouvé
    TRONCONS_MISSING.add(v)
    return None

def couchdb_upload_bulk(documents):
    import requests

    url = f"{COUCH_URL}/{COUCH_DB}/_bulk_docs"
    payload = {"docs": documents}

    try:
        r = requests.post(url, json=payload, auth=(COUCH_USER, COUCH_PW), timeout=10)
    except Exception as e:
        return False, [f"Erreur de connexion : {e}"]

    if r.status_code not in (200, 201, 202):
        return False, [f"HTTP {r.status_code}: {r.text}"]

    resp = r.json()
    errors = []

    for idx, item in enumerate(resp):
        if "error" in item:
            reason = item.get("reason", "inconnu")
            errors.append(f"Doc {idx} : {item['error']} – {reason}")

    return len(errors) == 0, errors

