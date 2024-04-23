from setuptools import setup
# https://click.palletsprojects.com/en/8.1.x/setuptools/#setuptools-integration
# TODO: include all the required packages

setup(
    name="NestPy",
    version="0.1.0",
    py_modules=["main"],
    install_requires=["python-dotenv", "click", "requests"],
    entry_points={
        "console_scripts": [
            "nestpy = main:cli",
        ],
    },
)
