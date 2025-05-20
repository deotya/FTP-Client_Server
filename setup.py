from setuptools import setup, find_packages

setup(
    name="file_manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.6",
        "pyftpdlib>=1.5.6",
        "colorama>=0.4.4",
        "paramiko>=3.5.0",
        "cryptography>=45.0.0",
        "bcrypt>=4.0.0",
        "pywin32>=306",
    ],
    entry_points={
        "console_scripts": [
            "file_manager=main:main",
        ],
    },
) 