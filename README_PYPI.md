# sirs_import

Outil Python pour importer des désordres dans SIRS à partir d'un fichier GeoPackage (GPKG)

---

# Description

`sirs_import` permet de valider, transformer et importer des données de désordres, observations et photographies dans SIRS, à partir de fichiers GeoPackage (GPKG) et d’un dossier photos.

Le système effectue :
- détection automatique des colonnes
- application des valeurs de repli (fallback)
- validation des UUID
- vérification temporelle
- normalisation des références
- génération finale du JSON pour l’import SIRS

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

Crée les fichiers `<layer_name>_linearId.txt` et `<layer_name>_contactId.txt`

## Import complet vers CouchDB

```
cd path/to/data
sirs_import --upload
```

---

# Fichier de configuration

Un fichier `config_sirs.toml` doit être présent dans le répertoire projet.  
On peut aussi utiliser :

```
sirs_import --config chemin/vers/config.toml
```

Exemple fourni : [config_sirs.example.toml](https://github.com/jln-codes/sirs_import/blob/main/sirs_import/config_sirs.example.toml)

---

# Données attendues

## Désordres

Les colonnes liées aux désordres peuvent avoir n’importe quel nom et doivent être définies dans le fichier de configuration.

## Observations

Exemple (avec préfixe `obs1`) :

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

L’existence du champ obligatoire (suffixe `date`) détermine l’existence de l’élément.

## Photos

Exemple (prefix `obs1_pho1`) :

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

Le package peut restructurer le dossier photo pour coller à l'architecture typique utilisée par SIRS. Les photos seront renommées si nécessaire et leur chemin dans le fichier GPKG mis à jour.

Arborescence proposée:

```
racine_dossier = digue/
├─ TRONCON_A/
│  ├─ photo001.jpg
│  ├─ photo002.jpg
│  └─ …
├─ TRONCON_B/
│  ├─ photo003.jpg
│  └─ …
└─ TRONCON_C/
   ├─ photo004.jpg
   └─ …
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

Le fichier `nom_couche.json` généré peut ensuite être importé dans SIRS via :

```
sirs_import --upload
```

Le processus de validation garanti que les données seront valide du point de vue de CouchDB et de SIRS. 
A vous cependant de vous assurer qu'elles contiennent assez d'information pour être pertinente du point de vue du gestionnaire de digues. 


---

# Licence

Utilisation strictement NON COMMERCIALE.  
Voir :
https://github.com/jln-codes/sirs_import/blob/main/LICENSE

---

# Dépendances

* Python 3.10 ou 3.11 uniquement  
* pandas  
* geopandas  
* fiona  
* shapely  
* requests  
* wcwidth  
* tomli (pour Python < 3.11)  
* numpy < 2  
* numexpr >= 2.8.4  
* bottleneck >= 1.3.6  

---

# Avertissements

Ce programme manipule des données sensibles et modifie les fichiers sources.  
Sauvegardez les données originales.

Certaines relations entre champs ne sont pas vérifiées.  
La responsabilité de la cohérence métier vous incombe.

---

# Statut du projet

Développement actif — l’API reste susceptible d’évoluer.

---

# Support / Contact

Contribution et signalement d’anomalies via :  
https://github.com/jln-codes/sirs_import/issues

---

# English version

Full English documentation available at:  
https://github.com/jln-codes/sirs_import/blob/main/README.en.md
