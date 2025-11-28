English version: see README.en.md

# sirs_import

Outil Python pour importer des désordres dans SIRS à partir d'un fichier geopackage (GPKG)

---

# Sommaire

* [Description](#description)
* [Installation](#installation)
* [Utilisation](#utilisation)
* [Fichier de configuration](#fichier-de-configuration)
* [Format des données attendues](#données-attendues)
* [Identifiants SIRS normalisés](#identifiants-sirs)
* [Export JSON](#export-json)
* [Dépendances](#dépendances)
* [Avertissements](#avertissements)
* [Statut du projet](#statut-du-projet)
* [Licence](#licence)
* [Support / Contact](#support--contact)

---

# Description

`sirs_import` permet de valider, transformer et importer des données de désordres, observations et photographies dans SIRS, à partir de fichiers GeoPackage (GPKG) et d’arbres de photos.
Le système effectue :

* détection automatique des colonnes
* application des valeurs de repli (fallback)
* validation des UUID
* vérification temporelle
* normalisation des références
* génération finale du JSON pour l’import SIRS

---

# Installation

## Installation via PyPI

```
pip install sirs_import
```

## Développement local

```
git clone [https://github.com/TechCabbalr/sirs_import.git](https://github.com/TechCabbalr/sirs_import.git)
cd sirs_import
pip install -e .
```
---

# Utilisation

## Mode par défaut

cd path/to/data
sirs_import

## Extraction linearId et contactId uniquement

cd chemin/vers/données
sirs_import --extract

Crée les fichiers <layer_name>_linearId.txt et <layer_name>_contactId.txt

## Import complet vers CouchDB

cd path/to/data
sirs_import --upload

---

# Fichier de configuration

Un fichier config_sirs.toml doit être placé dans le répertoire projet. On peut aussi fournir l'argument --config chemin/vers/config.

Exemple fourni :

config_sirs.example.toml

---

# Données attendues

## Désordres

Les colonnes liées aux désordres peuvent avoir n'importe quel nom et seront spécifiées dans le fichier de configuration (.toml).

## Observations

Les colonnes d'observations sont détectées automatiquement sur la base du schéma <prefixe1>_<suffixe_autorisé>. Si obs1 est le préfixe, on attend :

```
obs1_date                # obligatoire
obs1_evolution
obs1_suite
obs1_designation
obs1_observateurId
obs1_suiteApporterId
obs1_nombreDesordres
obs1_urgenceId
```

## Photos

Les colonnes d'observations sont détectées automatiquement sur la base du schéma <prefixe1>*<prefixe2>*<suffixe_autorisé>. Si obs1 et pho1 sont les préfixes, on attend :

```
obs1_pho1_chemin              # obligatoire
obs1_pho1_photographeId
obs1_pho1_date
obs1_pho1_designation
obs1_pho1_libelle
obs1_pho1_orientationPhoto
obs1_pho1_coteId
```

## Répertoire des photos

Le fichier peut restructurer le dossier photo pour coller à l'architecture typique utilisée par SIRS. Les photos seront renommées si nécessaire et leur chemin dans le fichier GPKG mis à jour.

Arborescence finale :

./folder_name/
TRONCON_A/
TRONCON_B/
TRONCON_C/

---

# Identifiants SIRS

Un certain nombre de champs acceptent des entiers > 0 avec ou sans préfixes. Cela vaut pour les colonnes GPKG et pour les statiques qui seraient définis dans le fichier de configuration.

Ces champs sont vérifiés et normalisés automatiquement.

---

# Export JSON

nom_GPKG.json

Ce fichier peut ensuite être importé dans SIRS (sisr_import --upload).

---

# Licence

Utilisation strictement NON COMMERCIALE. Voir LICENSE pour les termes complets.

---

# Dépendances

* Python ≥ 3.10
* pandas
* fiona
* shapely
* requests
* tomllib / tomli
* wcwidth

---

# Avertissements

Ce programme manipule des données sensibles et modifie les fichiers sources. Sauvegarder les données originales.

---

# Statut du projet

Projet en développement actif. API et comportement susceptibles d’évoluer.

---

# Support / Contact

Les contributions pertinentes pourront être examinées et intégrées. Signalez les bugs via GitHub issues.

