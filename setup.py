from setuptools import setup, find_packages

setup(
    name="va_ai_transcribeerder",
    version="0.1",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
)