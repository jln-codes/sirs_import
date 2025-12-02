Voici la version finale prête à coller dans PyPI. Tous les liens internes sont désormais absolus et valides.

---

English version [here](https://github.com/jln-codes/sirs_import/blob/main/README.en.md)

# sirs_import

Outil Python pour importer des désordres dans SIRS à partir d'un fichier geopackage (GPKG)

---

# Sommaire

* [Description](https://github.com/jln-codes/sirs_import/blob/main/README.md#description)
* [Installation](https://github.com/jln-codes/sirs_import/blob/main/README.md#installation)
* [Utilisation](https://github.com/jln-codes/sirs_import/blob/main/README.md#utilisation)
* [Fichier de configuration](https://github.com/jln-codes/sirs_import/blob/main/README.md#fichier-de-configuration)
* [Données attendues](https://github.com/jln-codes/sirs_import/blob/main/README.md#données-attendues)
* [Valeurs statiques et fallbacks](https://github.com/jln-codes/sirs_import/blob/main/README.md#valeurs-statiques-et-fallbacks)
* [Export JSON](https://github.com/jln-codes/sirs_import/blob/main/README.md#export-json)
* [Dépendances](https://github.com/jln-codes/sirs_import/blob/main/README.md#dépendances)
* [⚠️ Avertissements](https://github.com/jln-codes/sirs_import/blob/main/README.md#avertissements)
* [Statut du projet](https://github.com/jln-codes/sirs_import/blob/main/README.md#statut-du-projet)
* [Licence](https://github.com/jln-codes/sirs_import/blob/main/README.md#licence)
* [Support / Contact](https://github.com/jln-codes/sirs_import/blob/main/README.md#support--contact)

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
git clone https://github.com/jln-codes/sirs_import.git
cd sirs_import
pip install -e .
```

---

# Utilisation

## Mode par défaut

```
cd path/to/data
sirs_import
```

## Extraction linearId et contactId uniquement

```
cd chemin/vers/données
sirs_import --extract
```

Crée les fichiers <layer_name>_linearId.txt et <layer_name>_contactId.txt

## Import complet vers CouchDB

```
cd path/to/data
sirs_import --upload
```

---

# Fichier de configuration

Un fichier config_sirs.toml doit être placé dans le répertoire projet. On peut aussi fournir l'argument --config chemin/vers/config.toml.

Exemple fourni : [config_sirs.example.toml](https://github.com/jln-codes/sirs_import/blob/main/sirs_import/config_sirs.example.toml)

---

# Données attendues

## Désordres

Les colonnes liées aux désordres peuvent avoir n'importe quel nom et seront spécifiées dans le fichier de configuration (.toml).

## Observations

Les colonnes d'observations sont détectées automatiquement sur la base du schéma `<prefixe1>_<suffixe_autorisé>`. Par exemple, si on utilise obs1 comme préfixe, on attend :

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

Les colonnes non obligatoires peuvent éventuellement être prises en charge par les [fallbacks](https://github.com/jln-codes/sirs_import/blob/main/README.md#valeurs-statiques-et-fallbacks).

## Photos

Les colonnes d'observations sont détectées automatiquement sur la base du schéma `<prefixe1>_<prefixe2>_<suffixe_autorisé>`. Si obs1 et pho1 sont les préfixes, on attend :

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

Les colonnes non obligatoires peuvent éventuellement être prises en charge par les [fallbacks](https://github.com/jln-codes/sirs_import/blob/main/README.md#valeurs-statiques-et-fallbacks).

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

Un certain nombre de champs acceptent des entiers > 0 avec ou sans préfixes. Cela vaut pour les colonnes GPKG et pour les statiques définis dans le fichier de configuration.

Ces champs sont vérifiés et normalisés automatiquement.

---

# Valeurs statiques et fallbacks

Certaines variables du fichier de configuration peuvent être définies soit comme noms de colonnes GPKG, soit comme valeurs uniques appliquées automatiquement en l’absence de colonne dans les données (statiques). Les champs d’observations et de photos peuvent également utiliser des valeurs par défaut si leurs champs ne sont pas présents dans le GPKG.

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

Ce fichier (nom_couche.json) peut ensuite être importé dans SIRS (`sirs_import --upload`).

---

# Licence

Utilisation strictement NON COMMERCIALE. Voir [LICENSE](https://github.com/jln-codes/sirs_import/blob/main/LICENSE)

---

# Dépendances

* Python 3.10  ou 3.11 uniquement
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

# ⚠️ Avertissements

Ce programme manipule des données sensibles et modifie les fichiers sources. Sauvegarder les données originales.

---

# Statut du projet

Projet en développement actif. API et comportement susceptibles d’évoluer.

---

# Support / Contact

Signalez les bugs via GitHub issues.
