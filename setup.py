"""Project setup script."""

from setuptools import setup, find_packages

setup(
    name="meshcore-web",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "Flask>=3.0.0",
        "SQLAlchemy>=2.0.23",
        "meshcore>=1.0.0",
        "pyserial>=3.5",
        "python-dotenv>=1.0.0",
        "Flask-SQLAlchemy>=3.1.1",
        "Flask-Login>=0.6.3",
        "Flask-WTF>=1.2.1",
        "gunicorn>=21.2.0",
    ],
)