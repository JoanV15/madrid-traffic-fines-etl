import os
import pickle
import time
import hashlib
import requests
from pathlib import Path


class CacheError(Exception):
    """Excepción base para errores de caché."""
    pass


class Cache:
    """Gestiona el almacenamiento de objetos en disco."""

    def __init__(self, app_name: str = "trafic_app", obsolescence: int = 30):
        # Atributos privados
        self._app_name = app_name
        self._obsolescence = obsolescence  # Días

        # Definir ruta: Home del usuario / .app_name
        self._cache_dir = Path.home() / f".{app_name}"

        # Crea directorio si no existe
        if not self._cache_dir.exists():
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise CacheError(f"No se pudo crear el directorio de caché: {e}")

    @property
    def app_name(self):
        return self._app_name

    @property
    def cache_dir(self):
        return str(self._cache_dir)

    @property
    def obsolescence(self):
        return self._obsolescence

    def _get_path(self, name: str) -> Path:
        """Devuelve la ruta completa del fichero."""
        return self._cache_dir / name

    def exists(self, name: str) -> bool:
        """Comprueba si existe el fichero."""
        return self._get_path(name).exists()

    def set(self, name: str, data: object) -> None:
        """Guarda datos en disco usando pickle."""
        try:
            with open(self._get_path(name), 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            raise CacheError(f"Error guardando {name}: {e}")

    def load(self, name: str) -> object:
        """Carga datos del disco."""
        if not self.exists(name):
            raise CacheError(f"El fichero {name} no existe en caché.")

        try:
            with open(self._get_path(name), 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            raise CacheError(f"Error leyendo {name}: {e}")

    def how_old(self, name: str) -> float:
        """Devuelve la edad del fichero en días (float)."""
        if not self.exists(name):
            return float('inf')  # Infinito si no existe, recomendación de la IA

        stat = self._get_path(name).stat()
        mtime = stat.st_mtime
        age_seconds = time.time() - mtime
        return age_seconds / (24 * 3600)

    def delete(self, name: str) -> None:
        """Borra un fichero de la caché."""
        path = self._get_path(name)
        if path.exists():
            try:
                os.remove(path)
            except OSError:
                pass

    def clear(self) -> None:
        """Borra todo el contenido de la caché."""
        for item in self._cache_dir.glob('*'):
            if item.is_file():
                try:
                    os.remove(item)
                except OSError:
                    pass


class CacheURL(Cache):
    """
    La clase cache url amplia esta cache original.
    Se encarga de gestionar descargas de Internet.
    """

    def _get_hash(self, url: str, **kwargs) -> str:
        """
        Método auxiliar para generar el hash MD5 consistente.
        """
        key_str = url + str(sorted(kwargs.items()))
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, url: str, **kwargs) -> object:
        name_hash = self._get_hash(url, **kwargs)

        # Aquí llamamos al exists del PADRE (Cache) pasándole el hash directamente
        if super().exists(name_hash):
            # 2. ¿ES VÁLIDO? (Obsolescencia)
            age = super().how_old(name_hash)
            if age < self.obsolescence:
                # Devolvemos lo local para ahorrar tiempo
                return super().load(name_hash)

        # Si no existe o es viejo -> DESCARGAR
        try:
            # print(f"Descargando: {url}...") # Debug
            response = requests.get(url, **kwargs)
            response.raise_for_status()  # Error si 404/500

            # Guardamos el contenido binario del CSV
            data = response.content

            # Guardamos en caché para la próxima vez
            super().set(name_hash, data)

            return data

        except requests.RequestException as e:
            raise CacheError(f"Error descargando {url}: {e}")

    def exists(self, url: str, **kwargs) -> bool:
        """Comprueba si existe la URL cacheada."""
        return super().exists(self._get_hash(url, **kwargs))

    def load(self, url: str, **kwargs) -> object:
        """Carga el contenido de la URL cacheada."""
        return super().load(self._get_hash(url, **kwargs))

    def how_old(self, url: str, **kwargs) -> float:
        """Devuelve la antigüedad de la URL cacheada."""
        return super().how_old(self._get_hash(url, **kwargs))

    def delete(self, url: str, **kwargs) -> None:
        """Borra la URL de la caché."""
        super().delete(self._get_hash(url, **kwargs))