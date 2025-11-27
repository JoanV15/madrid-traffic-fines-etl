# TraficFines

Paquete para el análisis de multas del Ayuntamiento de Madrid.

## Instalación
pip install traficFines-0.1.0-py3-none-any.whl

## Uso
```python
from traficFines.madrid_fines import MadridFines
app = MadridFines()
app.add(2024, 12)
app.fines_hour("grafico.png")