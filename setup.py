import pathlib
import re

from setuptools import setup

ROOT = pathlib.Path(__file__).parent

with open(ROOT / 'jishaku' / 'meta.py', 'r', encoding='utf-8') as f:
    VERSION_MATCH = re.search(r'VersionInfo\(major=(\d+), minor=(\d+), micro=(\d+), .+\)', f.read(), re.MULTILINE)

    if not VERSION_MATCH:
        raise RuntimeError('Версия не установлена ​​или не может быть найдена')

    VERSION = '.'.join([VERSION_MATCH.group(1), VERSION_MATCH.group(2), VERSION_MATCH.group(3)])

EXTRA_REQUIRES = {}

for feature in (ROOT / 'requirements').glob('*.txt'):
    with open(feature, 'r', encoding='utf-8') as f:
        EXTRA_REQUIRES[feature.with_suffix('').name] = f.read().splitlines()

REQUIREMENTS = EXTRA_REQUIRES.pop('_', [])

if not VERSION:
    raise RuntimeError('Версия не установлена')

with open(ROOT / 'README.md', 'r', encoding='utf-8') as f:
    README = f.read()

setup(
    name='disnake-jishaku-ru',
    author='darkness800',
    url='https://github.com/darkness800/disnake-jishaku-ru',

    license='MIT',
    description='Расширение Disnake, включая полезные инструменты для разработки и отладки ботов.',
    long_description=README,
    long_description_content_type='text/markdown',
    project_urls={
        'Code': 'https://github.com/darkness800/disnake-jishaku-ru',
        'Issue tracker': 'https://github.com/darkness800/disnake-jishaku-ru/issues'
    },

    version=VERSION,
    packages=['jishaku', 'jishaku.features', 'jishaku.repl', 'jishaku.shim'],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    python_requires='>=3.8.0',

    extras_require=EXTRA_REQUIRES,

    keywords='jishaku disnake disnake-jishaku-ru discord cog repl extension ru-fork',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Russian',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Communications :: Chat',
        'Topic :: Internet',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities'
    ]
)
