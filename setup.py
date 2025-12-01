from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="traficFines",
    version="0.1.0",
    author="Joan F. Vázquez",
    author_email="joanfe01@ucm.es",
    description="Proyecto del modulo 1: Programación avanzada en python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JoanV15/ProyectoT1/",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "pandas",
        "numpy",
        "matplotlib",
        "requests",
        "beautifulsoup4",
        "folium"
    ],

)
