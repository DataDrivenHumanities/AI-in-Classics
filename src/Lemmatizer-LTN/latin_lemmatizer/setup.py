"""
Setup script for the latin_lemmatizer package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="latin-lemmatizer",
    version="0.1.0",
    description="A Python client for the Latin Lemmatizer API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Aidan Burrowes",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.27",
        "python-dotenv>=1.0.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Topic :: Text Processing :: Linguistic",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="latin, linguistics, morphology, lemmatization, inflection",
)

