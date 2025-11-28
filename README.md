# sirs_import  

**FR :** Outil Python pour importer des désordres dans SIRS
**EN :** Python tool for importing damages into the SIRS

---

# Sommaire / Table of contents

- [Description](#description--description)
- [Installation](#installation--installation)
- [Utilisation](#utilisation--usage)
- [Fichier de configuration](#fichier-de-configuration--configuration-file)
- [Format des données attendues](#données-attendues--expected-data-format)
- [Identifiants SIRS normalisés](#identifiants-sirs--sirs-reference-identifiers)
- [Export JSON](#export-json--json-output)
- [Dépendances](#dépendances--dependencies)
- [Avertissements](#avertissements--warnings)
- [Statut du projet](#statut-du-projet--project-status)
- [Licence](#licence--license)
- [Support / Contact](#support--contact)

---

# Description / Description

**FR :**
`sirs_import` permet de valider, transformer et importer des données de désordres, observations et photographies dans SIRS, à partir de fichiers GeoPackage (GPKG) et d’arbres de photos.
Le système effectue :
- détection automatique des colonnes
- application des valeurs de repli (fallback)
- validation des UUID
- vérification temporelle
- normalisation des références
- génération finale du JSON pour l’import SIRS

**EN :**
`sirs_import` validates, transforms and imports damage/inspection/photo data into SIRS using GeoPackage (GPKG) input and photo directories. 
The system performs:
- automatic column detection
- fallback application
- UUID validation
- temporal verification
- reference normalization
- final JSON generation for SIRS import

---

# Installation / Installation

## A) Mode développement local / Local development mode

git clone https://github.com/TechCabbalr/sirs_import.git  
cd sirs_import  
pip install -e .  

---

# Utilisation / Usage

## Mode par défaut / Default mode  
cd path/to/data  
sirs_import

## Extraction linearId et contactId uniquement / Extract-only mode 
cd chemin/vers/données  
sirs_import --extract

Crée les fichiers /create files <layer_name>_linearId.txt et/and <layer_name>_contactId.txt

## Import complet vers CouchDB / Full import into CouchDB  
cd path/to/data  
sirs_import --upload

## Fichier de configuration / Configuration file

**FR :** Un fichier config_sirs.toml doit être placé dans le répertoire projet. On peut aussi fournir l'argument --config chemin/vers/config  
**EN :** A config_sirs.toml file must exist in the project directory. The argument --config chemin/vers/config can also be given

Exemple fourni / Example provided:

config_sirs.example.toml

---

# Données attendues / Expected data format

## Désordres
**FR :** Les colonnes liées aux désordres peuvent avoir n'importe quel nom et seront spéficiées dans le fichier de configuration (.toml)  
**EN :** Columns related to disorders can have any name, which should be defined in the configuration file (.toml)

## Observations
**FR :** Les colonnes d'observations sont détectées automatiquement sur la base du schéma <prefixe1>_<suffixe_autorisé>. Si obs1 est le préfixe, on attend:  
**EN :** Observation columns are automatically detected by parsing <prefixe1>_<suffixe_autorisé> name patterns. If obs1 is the prefix, we expect:

```
obs1_date                # obligatoire /mandatory
obs1_evolution
obs1_suite
obs1_designation
obs1_observateurId
obs1_suiteApporterId
obs1_nombreDesordres
obs1_urgenceId
```


## Photos
**FR :** Les colonnes d'observations sont détectées automatiquement sur la base du schéma <prefixe1>_<prefixe2>_<suffixe_autorisé>. Si obs1 et pho1 sont les préfixes, on attend:  
**EN :** Observation columns are automatically detected by parsing <prefixe1>_<prefixe2>_<suffixe_autorisé> name patterns. If obs1 and pho1 are the prefixes, we expect:

```
obs1_pho1_chemin              # obligatoire /mandatory
obs1_pho1_photographeId
obs1_pho1_date
obs1_pho1_designation
obs1_pho1_libelle
obs1_pho1_orientationPhoto
obs1_pho1_coteId
```

## Répertoire des photos / Photo directory

**FR :** Le fichier peut restructurer le dossier photo pour coller à l'architecture typique utilisée par SIRS. Les photos seront renommées si nécessaire et leur chemin dans le fichier GPKG mis à jour.  
**EN :** The script can automatically reorganize the photo directory to match the standard folder structure expected by SIRS. Photos will be renamed if necessary, and their paths inside the GPKG file will be updated accordingly.

Arborescence finale / Final directory structure:

./folder_name/
    TRONCON_A/
    TRONCON_B/
    TRONCON_C/

---

## Identifiants SIRS / SIRS reference identifiers

Un certain nombre de champs acceptent des entiers > 0 avec ou sans préfixes. Cela vaut pour les colonnes GPKG et pour les statiques qui seraient définis dans le fichier de configuration.

Champs concernés :

| Nom fonctionnel (JSON SIRS) | Variable de config (TOML)   | Valeurs entières autorisées | Forme préfixée autorisée (chaîne)         |
| --------------------------- | --------------------------- | --------------------------- | ----------------------------------------- |
| `positionId`                | `COL_POSITION_ID`           | 3 à 15, ou 99               | `RefPosition:X`                           |
| `coteId` (désordre)         | `COL_COTE_ID`               | 1 à 8, ou 99                | `RefCote:X`                               |
| `sourceId`                  | `COL_SOURCE_ID`             | 0 à 4, ou 99                | `RefSource:X`                             |
| `categorieDesordreId`       | `COL_CATEGORIE_DESORDRE_ID` | 1 à 7                       | `RefCategorieDesordre:X`                  |
| `typeDesordreId`            | `COL_TYPE_DESORDRE_ID`      | 1 à 73, ou 99               | `RefTypeDesordre:X`                       |
| `urgenceId`                 | `OBS_FALLBACK_URGENCE`      | 1, 2, 3, 4, 99              | `RefUrgence:X`                            |
| `suiteApporterId`           | `OBS_FALLBACK_SUITE`        | 1 à 8                       | `RefSuiteApporter:X`                      |
| `orientationPhoto`          | `PHO_FALLBACK_ORIENTATION`  | 1 à 9, ou 99                | `RefOrientationPhoto:X`                   |
| `coteId` (photo)            | `PHO_FALLBACK_COTE`         | 1 à 8, ou 99                | `RefCote:X`                               |
| `nombreDesordres`           | `OBS_FALLBACK_NB_DESORDRES` | entier natif ≥ 0 (0,1,2,…)  | pas de forme préfixée (entier uniquement) |



Ces champs sont vérifiés et normalisés automatiquement.

---

### Principe des valeurs statiques et fallbacks / Static values & fallback logic

**FR :**
Certaines variables du fichier de configuration peuvent être définies soit comme noms de colonnes GPKG, soit comme valeurs uniques appliquées automatiquement en l’absence de colonne dans les données (statiques). Les champs d’observations et de photos peuvent également utiliser des valeurs par défaut si leurs champs ne sont pas présents dans le GPKG (fallbacks)

Priorité interne de lecture
1. valeur présente dans le GPKG
2. valeur issue du fichier de configuration (si définie)

**EN :**
Some configuration entries may be set either as GPKG column names or as constant values automatically applied when no such column exists (static). Observation and photo fields may also rely on default values when their corresponding data fields are not present (fallbacks).

Internal resolution order:
1. value present in the GPKG
2. value from configuration (if defined)

COL_POSITION_ID = "pos"
→ lecture depuis colonne `pos` / read from GPKG column `pos`

COL_POSITION_ID = 7
→ positionId = 7 pour toutes les lignes / positionId = 7 for all rows

obs2_observateurId absent
→ observateur par défaut utilisé / default observer assigned

obs3_pho1_orientationId manquant
→ orientation par défaut appliquée (ex: 99) / default orientation applied (e.g., 99)

---

# Export JSON / JSON output

nom_GPKG.json

**FR :** Ce fichier peut ensuite être importé dans SIRS (sisr_import --upload).  
**EN :** This output can then be ingested into SIRS (sisr_import --upload).

---

# Licence / License

**FR :** Utilisation strictement NON COMMERCIALE. Voir LICENSE pour les termes complets.  
**EN :** Strictly NON-COMMERCIAL USE. See LICENSE for full terms.

---

# Dépendances / Dependencies

- Python ≥ 3.10
- pandas
- fiona
- shapely
- requests
- tomllib / tomli
- wcwidth

---

# Avertissements / Warnings

**FR :** Ce programme manipule des données sensibles et modifie les fichiers sources. Sauvegarder les données originales.  
**EN :** This tool processes potentially critical data et modify source files. Data should be backed up before processing.

---

# Statut du projet / Project status

**FR :** Projet en développement actif. API et comportement susceptibles d’évoluer.  
**EN :** Under active development; API may still change.

---

# Support / Contact

**FR :** Les contributions pertinentes pourront être examinées et intégrées. Signalez les bugs via GitHub issues.  
**EN :** Relevant contributions may be reviewed and merged. Bug reports welcome.






