class SirsError(Exception):
    """Erreur générique dans l'import SIRS."""
    pass

class CouchDBError(SirsError):
    """Erreur liée à CouchDB."""
    pass

class GpkgReadError(SirsError):
    """Erreur de lecture du fichier GPKG."""
    pass

class DataNotFoundError(SirsError):
    """Aucune donnée trouvée alors qu'elle était attendue."""
    pass

class DataValidationError(SirsError):
    """Erreur de validation des données."""
    pass

class ExtractProcessError(SirsError):
    """Erreur lors de l'extraction EXTRACT_ONLY."""
    pass

class GpkgWriteError(SirsError):
    """Erreur lors de l’écriture du fichier GPKG."""
    pass

class DataValidationError(SirsError):
    """Erreur de validations des données."""
    pass

class PhotoMigrationError(SirsError):
    """Erreur de migration des photos."""
    pass

class GpkgUpdateError(SirsError):
    """Erreur de miseà jour du GDF interne."""
    pass

class UserCancelled(SirsError):
    """Fin du processus utilisateur"""
    pass

class JsonExportError(SirsError):
    """Fin du processus utilisateur"""
    pass


