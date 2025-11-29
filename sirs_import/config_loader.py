import os
import sys
import argparse
from .config_defaults import DEFAULTS


def get_toml_loader():
    """
    Retourne le module tomllib (Python 3.11+) ou tomli (3.10 et inf).
    """
    try:
        import tomllib
        return tomllib
    except Exception:
        pass

    try:
        import tomli
        return tomli
    except Exception:
        pass

    return None


def load_config_file(path):
    """
    Charge un fichier TOML.
    Retourne {} si problème de parsing ou erreur.
    """
    toml = get_toml_loader()
    if toml is None:
        print(f"Warning: TOML parser unavailable. '{path}' ignoré.")
        return {}

    try:
        with open(path, "rb") as f:
            return toml.load(f)
    except Exception as e:
        print(f"Warning: erreur lecture config '{path}': {e}")
        return {}


def merge_config(path):
    """
    Charge la config utilisateur et l’injecte dans DEFAULTS.
    """
    user = load_config_file(path)
    cfg = DEFAULTS.copy()
    cfg.update(user)
    return cfg


def red(text: str) -> str:
    return f"\033[41m\033[1m{text} \033[0m"


def red_block(text: str) -> str:
    return f"\033[41m\033[1m{text}\033[0m"


from wcwidth import wcswidth

def print_red_block(lines):
    maxlen = max(wcswidth(line) for line in lines)
    for line in lines:
        pad = " " * (maxlen - wcswidth(line))
        print(f"\033[41m\033[1m{line}{pad}\033[0m")


def load_config():
    """
    Logique d’ordre :
    1) --config /chemin/vers/config_sirs.toml
    2) config_sirs.toml dans cwd
    """

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config")
    args, remaining = parser.parse_known_args()

    # IMPORTANT : restaurer sys.argv sans l'argument --config
    sys.argv = [sys.argv[0]] + remaining

    # 1) Chemin explicite fourni par l’utilisateur
    if args.config:

        # chemin inexistant
        if not os.path.exists(args.config):
            print()
            print_red_block([
                f"⛔ ERREUR: fichier config introuvable:",
                f"{args.config}",
            ])
            print()
            sys.exit(1)

        # chemin existe mais ce n'est PAS un fichier
        if not os.path.isfile(args.config):
            print()
            print_red_block([
                f"⛔ ERREUR: le chemin fourni n'est pas un fichier:",
                f"{args.config}",
                "Un chemin de fichier .toml est requis.",
            ])
            print()
            sys.exit(1)

        # pas un .toml
        if not args.config.lower().endswith(".toml"):
            print()
            print_red_block([
                f"⛔ ERREUR: format incorrect:",
                f"{args.config}",
                "Le fichier de configuration doit être un .toml",
            ])
            print()
            sys.exit(1)

        print()
        print(f"⚙️ Chargement config via --config: {args.config}")
        return args.config, merge_config(args.config)


    # 2) config_sirs.toml dans le PWD
    cwd_cfg = os.path.join(os.getcwd(), "config_sirs.toml")
    if os.path.exists(cwd_cfg):
        print()
        print(f"⚙️ Chargement config locale depuis: {cwd_cfg}")
        return cwd_cfg, merge_config(cwd_cfg)

    print()
    print_red_block([
        "⛔ ERREUR: aucun fichier config_sirs.toml trouvé dans le répertoire courant.",
        "Placez-vous dans votre dossier projet et relancez:",
        "cd /ma/digue && python3 -m sirs_import"
    ])
    print()
    sys.exit(1)


# CHARGEMENT INITIAL
CONFIG_PATH, CONFIG = load_config()

# PROJECT_DIR = répertoire contenant config_sirs.toml
PROJECT_DIR = os.path.dirname(CONFIG_PATH)


# Post-traitement: calcul du GPKG_PATH
def compute_GPKG_PATH():
    if CONFIG.get("GPKG_PATH"):
        return

    if CONFIG.get("GPKG_FILE"):
        CONFIG["GPKG_PATH"] = os.path.join(PROJECT_DIR, CONFIG["GPKG_FILE"])
    else:
        CONFIG["GPKG_PATH"] = None


compute_GPKG_PATH()

