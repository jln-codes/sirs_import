# sirs_import

Python tool for importing geopackage data (GPKG) into SIRS

---

# Table of contents

* [Description](#description)
* [Installation](#installation)
* [Usage](#usage)
* [Configuration file](#configuration-file)
* [Expected data format](#expected-data-format)
* [SIRS reference identifiers](#sirs-reference-identifiers)
* [JSON output](#json-output)
* [Dependencies](#dependencies)
* [Warnings](#warnings)
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

config_sirs.example.toml

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

## Photo directory

The script can automatically reorganize the photo directory to match the standard folder structure expected by SIRS. Photos will be renamed if necessary, and their paths inside the GPKG file will be updated accordingly.

Final directory structure:

./folder_name/
TRONCON_A/
TRONCON_B/
TRONCON_C/

---

# SIRS reference identifiers

Several fields accept integers > 0 with or without prefixes. This applies both to GPKG columns and to static values defined in the configuration file.

These fields are automatically verified and normalized.

---

# JSON output

nom_GPKG.json

This output can then be ingested into SIRS (sisr_import --upload).

---

# License

Strictly NON-COMMERCIAL USE. See LICENSE for full terms.

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

# Warnings

This tool processes potentially critical data and may modify source files. Data should be backed up before processing.

---

# Project status

Under active development; API may still change.

---

# Support / Contact

Relevant contributions may be reviewed and merged. Bug reports welcome.

