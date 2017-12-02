from setuptools import setup

setup(
    name='sharelatex_git',
    version='0.3',
    scripts=['sharelatex-git'],
    install_requires=[
        'requests',
        'bs4',
    ],
)
