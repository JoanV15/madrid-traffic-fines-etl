import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Aseguramos que se pueda importar el paquete desde la carpeta raíz
current_file_path = os.path.abspath(__file__)
tests_dir = os.path.dirname(current_file_path)
root_dir = os.path.dirname(tests_dir)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from traficFines.cache import Cache, CacheURL, CacheError
from traficFines.madrid_fines import MadridFines, MadridError


class TestCache(unittest.TestCase):
    """Pruebas para el módulo de caché."""

    def setUp(self):
        """Se ejecuta antes de cada test: preparamos un entorno limpio."""
        self.test_app = "test_suite_app"
        self.cache = Cache(app_name=self.test_app, obsolescence=1)

    def tearDown(self):
        """Se ejecuta después de cada test: borramos la basura generada."""
        if os.path.exists(self.cache.cache_dir):
            shutil.rmtree(self.cache.cache_dir)

    def test_creation(self):
        """Prueba que se crea el directorio."""
        self.assertTrue(os.path.exists(self.cache.cache_dir))

    def test_set_get(self):
        """Prueba guardar y recuperar datos."""
        data = {"clave": "valor"}
        self.cache.set("prueba", data)
        self.assertTrue(self.cache.exists("prueba"))
        recuperado = self.cache.load("prueba")
        self.assertEqual(data, recuperado)

    def test_delete(self):
        """Prueba el borrado."""
        self.cache.set("borrar", 123)
        self.cache.delete("borrar")
        self.assertFalse(self.cache.exists("borrar"))


class TestCacheURL(unittest.TestCase):
    """Pruebas para la caché de URLs con Mocking."""

    def setUp(self):
        self.test_app = "test_suite_url"
        self.cache_url = CacheURL(app_name=self.test_app)

    def tearDown(self):
        if os.path.exists(self.cache_url.cache_dir):
            shutil.rmtree(self.cache_url.cache_dir)

    @patch('traficFines.cache.requests.get')
    def test_get_url_download(self, mock_get):
        """Simula una descarga cuando no hay caché."""
        # Configuramos el Mock para que devuelva un 200 OK con contenido falso
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"contenido_csv_simulado"
        mock_get.return_value = mock_response

        url = "http://fake.url/data.csv"

        # Ejecutamos
        content = self.cache_url.get(url)

        # Verificaciones
        self.assertEqual(content, b"contenido_csv_simulado")
        # Verificar que se llamó a requests.get una vez
        mock_get.assert_called_once()
        # Verificar que ahora existe en caché (usando los métodos redefinidos)
        self.assertTrue(self.cache_url.exists(url))


class TestMadridFines(unittest.TestCase):
    """Pruebas de la lógica de negocio."""

    def setUp(self):
        self.app = MadridFines(app_name="test_suite_madrid")

    def tearDown(self):
        if os.path.exists(self.app._cache.cache_dir):
            shutil.rmtree(self.app._cache.cache_dir)

    def test_clean_logic(self):
        """Prueba la limpieza de columnas y datos."""
        # DataFrame sucio simulado
        data = {
            ' CALIFICACION ': [' LEVE ', 'GRAVE'],
            ' VEL_LIMITE ': ['50', '30'],
            ' HORA ': [12.30, 20.00],
            ' ANIO ': [2024, 2024],
            ' MES ': [1, 1],
            'COORDENADA-X': ['100', '200'],
            'DESCUENTO': ['SI', 'NO']
        }
        df = pd.DataFrame(data)

        # Ejecutar limpieza
        MadridFines.clean(df)

        # Verificaciones
        # 1. Nombres de columnas limpios y snake_case
        self.assertIn('CALIFICACION', df.columns)
        self.assertIn('COORDENADA_X', df.columns)

        # 2. Valores limpios (strip)
        self.assertEqual(df.iloc[0]['CALIFICACION'], 'LEVE')

        # 3. Tipos numéricos
        self.assertTrue(pd.api.types.is_numeric_dtype(df['VEL_LIMITE']))

        # 4. Índice fecha creado
        self.assertTrue(isinstance(df.index, pd.DatetimeIndex))

    @patch('traficFines.madrid_fines.MadridFines.load')
    def test_add_integration(self, mock_load):
        """Prueba que add llama a load y concatena datos."""
        # Simulamos que load devuelve un DF pequeño ya limpio
        df_simulado = pd.DataFrame({
            'ANIO': [2024], 'MES': [1], 'HORA': [10.00],
            'IMP_BOL': [100], 'DESCUENTO': ['SI'], 'CALIFICACION': ['LEVE']
        })
        mock_load.return_value = df_simulado

        self.app.add(2024, 1)

        self.assertEqual(len(self.app.data), 1)
        self.assertIn((1, 2024), self.app.loaded)


if __name__ == '__main__':
    unittest.main()