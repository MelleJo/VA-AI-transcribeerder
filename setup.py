from setuptools import setup, find_packages

setup(
    name="va-ai-transcribeerder",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'openai',
        'psutil'
    ],
)
