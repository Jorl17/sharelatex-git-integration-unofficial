from setuptools import setup

setup(
    name='sharelatex_git',
    version='0.1',
    scripts=['sharelatex-git'],
    install_requires=[
        'requests',
        'bs4',
    ],
)
