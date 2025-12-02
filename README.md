# Madrid Traffic Fines

Paquete Python diseñado para scrappear, almacenar y analizar los datos de multas de tráfico del Portal de Datos Abiertos del Ayuntamiento de Madrid.

## Instalación

Ejecuta estos comandos en tu terminal desde la raíz del proyecto:

1. **Prepara el entorno:**
   ```bash
   pip install wheel
   
2. **Genera el ejecutable (.whl):**
   python setup.py sdist bdist_wheel

3. **Instala el paquete:**
   pip install dist/traficFines-0.1.0-py3-none-any.whl

## Uso y Funciones
  Importa la clase principal y utiliza sus métodos para analizar los datos:
  
  from traficFines.madrid_fines import MadridFines
  
  app = MadridFines()
  
  app.add(year, month): Descarga los datos del mes indicado. Si es la primera vez, hace scraping de la web del Ayuntamiento; si ya existe, carga desde disco (caché). Limpia y normaliza los datos automáticamente.
  
  app.fines_hour(nombre_fichero): Genera y guarda una imagen con un gráfico lineal mostrando la evolución de multas por hora del día.
  
  app.fines_calification(): Devuelve un DataFrame con el recuento de multas agrupadas por calificación (LEVE, GRAVE, MUY GRAVE).
  
  app.total_payment(): Devuelve un DataFrame con el resumen financiero. Calcula la recaudación máxima posible y la mínima estimada (aplicando descuentos por pronto pago).

