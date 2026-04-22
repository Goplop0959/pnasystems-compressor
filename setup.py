"""Setup script for pnasystems-compressor."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pnasystems-compressor",
    version="1.0.0",
    author="Powerentity",
    description="A fully custom, lossless, high‑efficiency compression/decompression system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Goplop0959/pnasystems-compressor",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: System :: Archiving :: Compression",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": ["pytest", "twine", "wheel"],
    },
)
