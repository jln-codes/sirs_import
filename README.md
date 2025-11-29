English version: see README.en.md

# sirs_import

Outil Python pour importer des désordres dans SIRS à partir d'un fichier geopackage (GPKG)

---

# Sommaire

* [Description](#description)
* [Installation](#installation)
* [Utilisation](#utilisation)
* [Fichier de configuration](#fichier-de-configuration)
* [Données attendues](#données-attendues)
* [Identifiants SIRS normalisés](#identifiants-sirs)
* [Export JSON](#export-json)
* [Dépendances](#dépendances)
* [⚠️ Avertissements](#avertissements)
* [Statut du projet](#statut-du-projet)
* [Licence](#licence)
* [Support / Contact](#support--contact)

---

# Description

`sirs_import` permet de valider, transformer et importer des données de désordres, observations et photographies dans SIRS, à partir de fichiers GeoPackage (GPKG) et d'un dossier photos.
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

[config_sirs.example.toml](https://github.com/TechCabbalr/sirs_import/blob/main/config_sirs.example.toml)

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

Ces colonnes peuvent inclure des NULL. 

L'existence de la colonne obligatoire (suffixe date) détermine l'existence de l'élémemt observation.

Les colonnes non obligatoires peuvent éventuellement être prises en charge par les [fallbacks](valeurs-statiques-et-fallbacks). 

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
Ces colonnes peuvent inclure des NULL. 

L'existence de la colonne obligatoire (suffixe chemin) détermine l'existence de l'élémemt photo.

Les colonnes non obligatoires peuvent éventuellement être prises en charge par les [fallbacks](valeurs-statiques-et-fallbacks). 

## Répertoire des photos

Le fichier peut restructurer le dossier photo pour coller à l'architecture typique utilisée par SIRS. Les photos seront renommées si nécessaire et leur chemin dans le fichier GPKG mis à jour.

Arborescence finale :

```
./folder_name/
TRONCON_A/
TRONCON_B/
TRONCON_C/
```

---

## Nomenclature SIRS

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

# Valeurs statiques et fallbacks

Certaines variables du fichier de configuration peuvent être définies soit comme noms de colonnes GPKG, soit comme valeurs uniques appliquées automatiquement en l’absence de colonne dans les données (statiques). Les champs d’observations et de photos peuvent également utiliser des valeurs par défaut si leurs champs ne sont pas présents dans le GPKG (fallbacks)

Priorité interne de lecture
1. valeur présente dans le GPKG
2. valeur issue du fichier de configuration (si définie)

COL_POSITION_ID = "pos"
→ lecture depuis colonne `pos`

COL_POSITION_ID = 7
→ positionId = 7 pour toutes les lignes

obs2_observateurId absent
→ observateur par défaut utilisé

obs3_pho1_orientationId manquant
→ orientation par défaut appliquée (ex: 99)

---

# Export JSON

Ce fichier (nom_couche.json) peut ensuite être importé dans SIRS (sisr_import --upload).

Le processus de validation garanti que les données seront valide du point de vue de CouchDB et de SIRS. A vous cependant de vous assurer qu'elles contiennent assez d'information pour être pertinente du point de vue du gestionnaire de digues. 

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

# ⚠️ Avertissements

Ce programme manipule des données sensibles et modifie les fichiers sources. Sauvegarder les données originales.

Ce programme a été développé sur des données au format SIRS v2.52. La compatibilité est avec SIRS v2.53 est probable mais non testée à ce jour. 

categorieDesordreId et typeDesordreId ne sont pas indépendantes. Cette relation n'est pas vérifiée par le package. Vous devez donc vous assurer de ne pas rentrer de combinaison non reconnues par SIRS sous risque de plantage. 

---

# Statut du projet

Projet en développement actif. API et comportement susceptibles d’évoluer.

---

# Support / Contact

Les contributions pertinentes pourront être examinées et intégrées. Signalez les bugs via GitHub issues.

