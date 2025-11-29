# sirs_import

Python tool for importing geopackage data (GPKG) into SIRS

---

# Table of contents

# Table of contents

* [Description](#description)
* [Installation](#installation)
* [Usage](#usage)
* [Configuration file](#configuration-file)
* [Expected data format](#expected-data-format)
* [Static values & fallbacks](#static-values--fallbacks)
* [JSON output](#json-output)
* [Dependencies](#dependencies)
* [⚠️ Warnings](#warnings)
* [Project status](#project-status)
* [License](#license)
* [Support / Contact](#support--contact)


---

# Description

`sirs_import` validates, transforms and imports damage/inspection/photo data into SIRS using GeoPackage (GPKG) input and photo directories.
The system performs:

* automatic column detection
* fallback application
* UUID validation
* temporal verification
* reference normalization
* final JSON generation for SIRS import

---

# Installation

## Installation via PyPI

```
pip install sirs_import
```
## Local developpement

```
git clone [https://github.com/TechCabbalr/sirs_import.git](https://github.com/TechCabbalr/sirs_import.git)
cd sirs_import
pip install -e .
```
---

# Usage

## Default mode

cd path/to/data
sirs_import

## Extract-only mode

cd path/to/data
sirs_import --extract

Creates the files <layer_name>_linearId.txt and <layer_name>_contactId.txt

## Full import into CouchDB

cd path/to/data
sirs_import --upload

---

# Configuration file

A config_sirs.toml file must exist in the project directory. The argument --config path/to/config can also be given.

Example provided:

[config_sirs.example.toml](https://github.com/TechCabbalr/sirs_import/blob/main/config_sirs.example.toml)

---

# Expected data format

## Disorders

Columns related to disorders can have any name, which should be defined in the configuration file (.toml).

## Observations

Observation columns are automatically detected by parsing <prefixe1>_<suffixe_autorisé> name patterns. If obs1 is the prefix, we expect:

```
obs1_date                # mandatory
obs1_evolution
obs1_suite
obs1_designation
obs1_observateurId
obs1_suiteApporterId
obs1_nombreDesordres
obs1_urgenceId
```
These columns can inclure NULL values.

The presence of the mandatory column (suffix date) automatically implies the existence of the observation.

Fallback values when defined may take over absent columns [fallbacks](#static-values--fallbacks). 

## Photos

Observation/photo columns are automatically detected using <prefix1>*<prefix2>*<suffix> name patterns. If obs1 and pho1 are prefixes:

```
obs1_pho1_chemin              # mandatory
obs1_pho1_photographeId
obs1_pho1_date
obs1_pho1_designation
obs1_pho1_libelle
obs1_pho1_orientationPhoto
obs1_pho1_coteId
```
These columns can inclure NULL values.

The presence of the mandatory column (suffix chemin) automatically implies the existence of the observation.

Fallback values when defined may take over absent columns [fallbacks](#static-values--fallbacks). 

## Photo directory

The script can automatically reorganize the photo directory to match the standard folder structure expected by SIRS. Photos will be renamed if necessary, and their paths inside the GPKG file will be updated accordingly.

Final directory structure:

```
./folder_name/
TRONCON_A/
TRONCON_B/
TRONCON_C/
```

---

## SIRS reference identifiers

Some fields accept integers > 0 with or without prefixes. This applies to values within GPKG columns and static values defined in the configuration file when columns are absent.

Fields accepting such values :

| Name in JSON/SIRS           | Name in sirs_config.toml    | Authorized integers          | Prefixes                                  |
| --------------------------- | --------------------------- | --------------------------- | ----------------------------------------- |
| `positionId`                | `COL_POSITION_ID`           | 3 à 15, ou 99               | `RefPosition:X`                           |
| `coteId` (disorder)         | `COL_COTE_ID`               | 1 à 8, ou 99                | `RefCote:X`                               |
| `sourceId`                  | `COL_SOURCE_ID`             | 0 à 4, ou 99                | `RefSource:X`                             |
| `categorieDesordreId`       | `COL_CATEGORIE_DESORDRE_ID` | 1 à 7                       | `RefCategorieDesordre:X`                  |
| `typeDesordreId`            | `COL_TYPE_DESORDRE_ID`      | 1 à 73, ou 99               | `RefTypeDesordre:X`                       |
| `urgenceId`                 | `OBS_FALLBACK_URGENCE`      | 1, 2, 3, 4, 99              | `RefUrgence:X`                            |
| `suiteApporterId`           | `OBS_FALLBACK_SUITE`        | 1 à 8                       | `RefSuiteApporter:X`                      |
| `orientationPhoto`          | `PHO_FALLBACK_ORIENTATION`  | 1 à 9, ou 99                | `RefOrientationPhoto:X`                   |
| `coteId` (photo)            | `PHO_FALLBACK_COTE`         | 1 à 8, ou 99                | `RefCote:X`                               |
| `nombreDesordres`           | `OBS_FALLBACK_NB_DESORDRES` | integer ≥ 0 (0,1,2,…)       | not applicable                            |



These fields are normalized automatically.

---

# Static values & fallbacks

Some configuration entries may be set either as GPKG column names or as constant values automatically applied when no such column exists (static). Observation and photo fields may also rely on default values when their corresponding data fields are not present (fallbacks).

Internal resolution order:
1. value present in the GPKG
2. value from configuration (if defined)

COL_POSITION_ID = "pos"
→ read from GPKG column `pos`

COL_POSITION_ID = 7
→ positionId = 7 for all rows

obs2_observateurId absent
→ default observer assigned

obs3_pho1_orientationId manquant
→ default orientation applied (e.g., 99)

---

# JSON output

This output (layer_name.json) can then be parsed and uploaded into SIRS (sisr_import --upload).

The validation process ensures that the import is valid from CouchDB and SIRS points of view. However you should still make sure they include enough data to be meaningful.

---

# License

Strictly NON-COMMERCIAL USE. See [LICENSE](https://github.com/TechCabbalr/sirs_import/blob/4665596ff29e4f1437181034d16e0fa0a1a7dd72/LICENSE) for full terms.

---

# Dependencies

* Python ≥ 3.10
* pandas
* fiona
* shapely
* requests
* tomllib / tomli
* wcwidth

---

# ⚠️ Warnings

This tool processes potentially critical data and may modify source files. Data should be backed up before processing.

It has been developped using data from SIRS v2.52. The compatibility with SIRS 2.53 is likely but has not been tested yet. 

categorieDesordreId et typeDesordreId are not independant but this tool does not encode their relation. You must make sure that the data are correct otherwise SIRS may crash.

---

# Project status

Under active development; API may still change.

---

# Support / Contact

Relevant contributions may be reviewed and merged. Bug reports welcome.

