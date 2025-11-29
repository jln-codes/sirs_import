# -*- coding: utf-8 -*-
import datetime
from .helpers import is_valid_iso_date
from typing import Dict, Iterable, List, Tuple, Optional

from .config_loader import CONFIG
COL_DATE_DEBUT   = CONFIG["COL_DATE_DEBUT"]
COL_DATE_FIN     = CONFIG["COL_DATE_FIN"]
COL_TRONCONS     = CONFIG["COL_TRONCONS"]
COL_DESIGNATION  = CONFIG["COL_DESIGNATION"]
COL_LIBELLE      = CONFIG["COL_LIBELLE"]


def _lazy_isna():
    """
    Retourne une fonction isna compatible pandas si dispo,
    sinon une fonction qui retourne toujours False.
    """
    try:
        from pandas import isna
        return isna
    except ImportError:
        return lambda x: False


def _to_date(value) -> Optional[datetime.date]:
    """
    Convertit une valeur en datetime.date si possible,
    sinon None.
    Tolérante et silencieuse.
    """
    isna = _lazy_isna()

    if value is None:
        return None

    if isna(value):
        return None

    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value

    if isinstance(value, datetime.datetime):
        return value.date()

    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().date()
        except Exception:
            pass

    s = str(value).strip()
    if not s:
        return None
    if not is_valid_iso_date(s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except Exception:
        return None


def _resolve_bounds_per_row(
    gdf,
    columns: Iterable[str],
):
    """
    Renvoie bornes date_debut / date_fin pour chaque ligne.
    dd_series / df_series : séries si colonnes GPKG présentes
    dd_static / df_static : valeurs statiques config
    """
    cols = set(columns)

    dd_series = None
    df_series = None
    dd_static = None
    df_static = None

    if COL_DATE_DEBUT in cols:
        dd_series = gdf[COL_DATE_DEBUT]
    else:
        if isinstance(COL_DATE_DEBUT, str) and COL_DATE_DEBUT.strip():
            dd_static = _to_date(COL_DATE_DEBUT)

    if COL_DATE_FIN in cols:
        df_series = gdf[COL_DATE_FIN]
    else:
        if isinstance(COL_DATE_FIN, str) and COL_DATE_FIN.strip():
            df_static = _to_date(COL_DATE_FIN)

    return dd_series, df_series, dd_static, df_static


def temporal_constraints(
    gdf,
    observations: Dict[str, Iterable[str]],
    observation_dates: Dict[str, object],
    photo_patterns: Dict[Tuple[str, str], Iterable[str]],
    gpkg_schema: Dict[str, str],
) -> List[str]:
    """
    Vérifie les règles temporelles métier SANS modifier gdf ni les autres modules.

    Règles :

        obsN_date :
            date_debut <= obsN_date <= date_fin

        obsN_phoM_date :
            date_debut <= pho <= date_fin
            obs_date  <= pho

    Retourne une liste d'erreurs avec une référence métier TRONCON:DESORDRE au lieu de l’index.
    """
    errors: List[str] = []

    columns = list(gdf.columns)
    dd_series, df_series, dd_static, df_static = _resolve_bounds_per_row(gdf, columns)
    cols_set = set(columns)

    # =====================================================================
    # Ids lisibles pour les messages d’erreur
    # =====================================================================
    ids = {}
    for idx, row in gdf.iterrows():
        troncon = str(row.get(COL_TRONCONS, "")).strip()
        designation = str(row.get(COL_DESIGNATION, "")).strip()
        libelle = str(row.get(COL_LIBELLE, "")).strip()
        desordre = designation if designation else libelle
        ids[idx] = f"{troncon}:{desordre}"

    # Y a-t-il au moins une limite temporelle quelque part ?
    have_bounds = any([
        dd_series is not None,
        df_series is not None,
        dd_static is not None,
        df_static is not None
    ])


    # =====================================================================
    # 1) obsN_date
    # =====================================================================
    for obs_key, suffixes in observations.items():
        date_col = f"{obs_key}_date"
        if date_col not in cols_set:
            continue

        obs_series = gdf[date_col]

        for idx, obs_val in obs_series.items():
            od = _to_date(obs_val)
            if od is None:
                continue

            if have_bounds:
                if dd_series is not None:
                    dd = _to_date(dd_series.iloc[idx])
                else:
                    dd = dd_static

                if df_series is not None:
                    df = _to_date(df_series.iloc[idx])
                else:
                    df = df_static

                if dd is not None and od < dd:
                    errors.append(
                        f"{date_col} ({od}) < date_debut ({dd}) sur {ids[idx]}"
                    )

                if df is not None and od > df:
                    errors.append(
                        f"{date_col} ({od}) > date_fin ({df}) sur {ids[idx]}"
                    )


    # =====================================================================
    # 2) obsN_phoM_date
    # =====================================================================
    for (obs_key, pho_key), suffixes in photo_patterns.items():
        date_suffixes = [s for s in suffixes if s.split("_", 1)[0] == "date"]
        if not date_suffixes:
            continue

        for suf in date_suffixes:
            fullcol = f"{obs_key}_{pho_key}_{suf}"
            if fullcol not in cols_set:
                continue

            pho_series = gdf[fullcol]
            obs_series = observation_dates.get(obs_key)

            for idx, pho_val in pho_series.items():
                pd_ = _to_date(pho_val)
                if pd_ is None:
                    continue

                if obs_series is not None and idx in obs_series.index:
                    od = _to_date(obs_series.loc[idx])
                    if od is not None and pd_ < od:
                        errors.append(
                            f"{fullcol} ({pd_}) < date observation ({od}) sur {ids[idx]}"
                        )

                if have_bounds:
                    if dd_series is not None and idx in dd_series.index:
                        dd = _to_date(dd_series.loc[idx])
                    else:
                        dd = dd_static

                    if df_series is not None and idx in df_series.index:
                        df = _to_date(df_series.loc[idx])
                    else:
                        df = df_static

                    if dd is not None and pd_ < dd:
                        errors.append(
                            f"{fullcol} ({pd_}) < date_debut ({dd}) sur {ids[idx]}"
                        )

                    if df is not None and pd_ > df:
                        errors.append(
                            f"{fullcol} ({pd_}) > date_fin ({df}) sur {ids[idx]}"
                        )

    return errors

