import pandas as pd
import numpy as np
import requests
import io
import re
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from .cache import CacheURL, CacheError

# constantes
ROOT = "https://datos.madrid.es"
MADRID_FINES_URL = "/sites/v/index.jsp?vgnextoid=fb9a498a6bdb9410VgnVCM1000000b205a0aRCRD&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"


class MadridError(Exception):
    """Excepción para errores"""
    pass

def get_url(year: int, month: int) -> str:
    """
    Busca la URL navegando por la jerarquía del codigo HTML:
    1. LI (Mes) -> contiene P (Fecha)
    2. Dentro de ese LI -> buscar LI (Detalle) -> contiene P ("Detalle")
    3. Dentro de ese LI -> buscar A (CSV)
    """
    full_url = ROOT + MADRID_FINES_URL

    # Mapeo de meses
    meses_str = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    nombre_mes = meses_str[month - 1]
    objetivo_fecha = f"{year} {nombre_mes}"

    try:
        response = requests.get(full_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscamos el <p class="info-title"> que tiene la fecha (ej: "2025 Junio")
        p_fecha = soup.find(
            "p",
            class_="info-title",
            string=lambda t: t and objetivo_fecha in t
        )

        if not p_fecha:
            raise MadridError(f"No se encontró el bloque para la fecha: {objetivo_fecha}")

        # Subimos a su padre <li class="asociada-item"> (El contenedor principal del mes)
        li_mes = p_fecha.find_parent("li", class_="asociada-item")

        # Dentro de ese <li> del mes, buscamos el <p> que diga "Detalle"
        # Usamos recursive=True (por defecto) para que busque en los hijos anidados
        p_detalle = li_mes.find(
            "p",
            class_="info-title",
            string=lambda t: t and "Detalle" in t
        )

        if not p_detalle:
            raise MadridError(f"Se encontró el mes {objetivo_fecha}, pero no el apartado 'Detalle'.")

        # Subimos a su padre <li class="asociada-item"> (El contenedor del bloque Detalle)
        li_detalle = p_detalle.find_parent("li", class_="asociada-item")

        # Dentro del <li> de Detalle, buscamos el <a> con la clase del CSV
        enlace = li_detalle.find("a", class_="ico-csv")

        if enlace and 'href' in enlace.attrs:
            href = enlace['href']
            if href.startswith('/'):
                return ROOT + href
            elif href.startswith('http'):
                return href
            else:
                return ROOT + '/' + href
        else:
            raise MadridError("Se encontró el bloque Detalle, pero no el enlace CSV dentro.")

    except Exception as e:
        raise MadridError(f"Error buscando URL para {objetivo_fecha}: {e}")

class MadridFines:
    """Clase principal para gestionar multas."""

    def __init__(self, app_name: str = "trafic_app", obsolescence: int = 30):
        self._cache = CacheURL(app_name=app_name, obsolescence=obsolescence)
        self._data = pd.DataFrame()
        self._loaded = []

    @property
    def data(self):
        return self._data

    @property
    def loaded(self):
        return self._loaded

    @staticmethod
    def clean(df: pd.DataFrame) -> None:
        """
        Limpia el dataframe in-place.
        Unifica nombres de columnas (siempre guiones bajos) y tipos de datos.
        """
        # 1. Normalizar nombres de columnas:
        # - Quitamos espacios (strip)
        # - Reemplazamos guiones medios por bajos para unificar criterios (COORDENADA-X -> COORDENADA_X)
        df.columns = df.columns.str.strip().str.replace('-', '_')

        # 2. Limpieza de strings
        cols_texto = ['CALIFICACION', 'LUGAR', 'DENUNCIANTE', 'HECHO_BOL', 'DESCUENTO']

        for col in cols_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # 3. Conversión a Numéricos
        cols_num = ['VEL_LIMITE', 'VEL_CIRCULA', 'COORDENADA_X', 'COORDENADA_Y']

        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 4. Creación de fecha e índice
        if 'HORA' in df.columns and 'ANIO' in df.columns and 'MES' in df.columns:
            hora_float = df['HORA'].fillna(0)
            horas = hora_float.astype(int)
            minutos = ((hora_float - horas) * 100).round().astype(int)

            fechas_dict = {
                'year': df['ANIO'],
                'month': df['MES'],
                'day': 1,
                'hour': horas,
                'minute': minutos
            }

            df['fecha'] = pd.to_datetime(fechas_dict)
            df.set_index('fecha', inplace=True)

    @staticmethod
    def load(year: int, month: int, cacheurl: CacheURL) -> pd.DataFrame:
        """Descarga, lee y devuelve el DF crudo."""
        try:
            # Obtener URL (Scraping)
            url = get_url(year, month)

            # Descargar usando caché
            content_bytes = cacheurl.get(url)

            # Leer CSV
            content = io.BytesIO(content_bytes)
            df = pd.read_csv(content, sep=';', encoding='latin1')
            return df

        except Exception as e:
            raise MadridError(f"Error cargando datos {month}/{year}: {e}")

    def add(self, year: int, month: int = None) -> None:
        """Añade datos al dataset principal."""

        # Lógica para "Todo el año" si month es None (bucle del 1 al 12)
        if month is None:
            for m in range(1, 13):
                try:
                    self.add(year, m)
                except MadridError:
                    pass
            return

        # Verificar si ya está cargado
        if (month, year) in self._loaded:
            print(f"Datos de {month}/{year} ya cargados.")
            return

        print(f"Cargando datos de {month}/{year}...")

        # Cargar y Limpiar
        df_new = self.load(year, month, self._cache)
        self.clean(df_new)

        # Concatenar
        if self._data.empty:
            self._data = df_new
        else:
            self._data = pd.concat([self._data, df_new])

        # Registrar carga
        self._loaded.append((month, year))

    def fines_hour(self, fig_name: str) -> None:
        """Genera gráfico de líneas por hora."""
        if self._data.empty:
            raise MadridError("No hay datos cargados.")

        plt.figure(figsize=(10, 6))

        # Agrupar por Mes y Hora
        # Iteramos por cada mes cargado para pintar una línea
        for (m, y) in self._loaded:
            mask = (self._data['MES'] == m) & (self._data['ANIO'] == y)
            df_mes = self._data[mask]

            if not df_mes.empty:
                por_hora = df_mes.groupby(df_mes.index.hour).size()
                plt.plot(por_hora.index, por_hora.values, marker='o', label=f"{y}-{m}")

        plt.title("Evolución de sanciones por hora")
        plt.xlabel("Hora")
        plt.ylabel("Número de sanciones")
        plt.xticks(range(0, 24))
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()

        plt.savefig(fig_name)
        plt.close()
        print(f"Gráfico guardado en {fig_name}")

    def fines_calification(self) -> pd.DataFrame:
        """Resumen de multas por calificación."""
        if self._data.empty:
            return pd.DataFrame()
        resumen = self._data.groupby(['MES', 'ANIO', 'CALIFICACION']).size().unstack(fill_value=0)
        return resumen

    def total_payment(self) -> pd.DataFrame:
        """Resumen económico."""
        if self._data.empty:
            return pd.DataFrame()
        resumen = self._data.groupby(['MES', 'ANIO'])['IMP_BOL'].agg(
            recaudacion_max='sum',
            recaudacion_min=lambda x: (x * 0.5).sum()  # Lógica del 50%
        )
        return resumen