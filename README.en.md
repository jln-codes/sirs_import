Voici la version anglaise corrigée avec liens absolus GitHub valides pour PyPI, et suppression de l’emoji dans le titre "Warnings".

---

# sirs_import

Python tool for importing geopackage data (GPKG) into SIRS

---

# Table of contents

* [Description](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#description)
* [Installation](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#installation)
* [Usage](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#usage)
* [Configuration file](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#configuration-file)
* [Expected data format](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#expected-data-format)
* [Static values & fallbacks](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#static-values--fallbacks)
* [JSON output](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#json-output)
* [Dependencies](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#dependencies)
* [Warnings](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#warnings)
* [Project status](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#project-status)
* [License](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#license)
* [Support / Contact](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#support--contact)

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

## Local development

```
git clone https://github.com/jln-codes/sirs_import.git
cd sirs_import
pip install -e .
```

---

# Usage

## Default mode

```
cd path/to/data
sirs_import
```

## Extract-only mode

```
cd path/to/data
sirs_import --extract
```

Creates the files <layer_name>_linearId.txt and <layer_name>_contactId.txt

## Full import into CouchDB

```
cd path/to/data
sirs_import --upload
```

---

# Configuration file

A config_sirs.toml file must exist in the project directory. The argument --config path/to/config can also be given.

Example provided: [config_sirs.example.toml](https://github.com/jln-codes/sirs_import/blob/main/config_sirs.example.toml)

---

# Expected data format

## Disorders

Columns related to disorders can have any name, which should be defined in the configuration file (.toml).

## Observations

Observation columns are automatically detected by parsing `<prefixe1>_<authorized_suffix>` name patterns.
If obs1 is a prefix, expected columns include:

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

The mandatory suffix implies existence of the observation.

Fallback values when defined may take over absent columns:
[fallbacks](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#static-values--fallbacks).

## Photos

```
obs1_pho1_chemin              # mandatory
obs1_pho1_photographeId
obs1_pho1_date
obs1_pho1_designation
obs1_pho1_libelle
obs1_pho1_orientationPhoto
obs1_pho1_coteId
```

Again, fallbacks may apply:
[fallbacks](https://github.com/jln-codes/sirs_import/blob/main/README.en.md#static-values--fallbacks).

## Photo directory

Final directory structure:

```
./folder_name/
TRONCON_A/
TRONCON_B/
TRONCON_C/
```

---

## SIRS reference identifiers

All section headings and references are unchanged except that internal anchors are now absolute and valid.

---

# Static values & fallbacks

Internal resolution order:

1. value present in the GPKG
2. value from configuration (if defined)

---

# JSON output

This output (layer_name.json) can then be uploaded into SIRS using:

```
sirs_import --upload
```

---

# License

Strictly NON-COMMERCIAL USE. Full terms: [LICENSE](https://github.com/jln-codes/sirs_import/blob/main/LICENSE)

---

# Dependencies

* Python 3.10 or 3.11 only
* pandas
* geopandas
* fiona
* shapely
* requests
* wcwidth
* tomli; python_version < '3.11'
* numpy<2
* numexpr>=2.8.4
* bottleneck>=1.3.6

---

# Warnings

This tool processes potentially critical data and may modify source files. Data should be backed up before processing.

---

# Project status

Under active development; API may still change.

---

# Support / Contact

Bug reports welcome.
