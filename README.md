pyJellyfish : Python wrapper around Jellyfish (k-mer counter)
=============================================================

[![Python version][py-image]][py-link]
[![PyPi version][pypi-image]][pypi-link]
[![Build status][ci-image]][ci-link]

Introduction
------------

This tool essentially serves as an installer for Jellyfish for use with
Python. A small bundle of utilities is also included as a bonus.

Citing
------

-   Guillaume Marcais and Carl Kingsford, A fast, lock-free approach for
    efficient parallel counting of occurrences of k-mers. Bioinformatics
    (2011) 27(6): 764-770; doi:
    <https://doi.org/10.1093/bioinformatics/btr011>

Install
-------

### With pip

``` {.sourceCode .shell}
python -m venv $HOME/.virtualenvs/km
source $HOME/.virtualenvs/km/bin/activate
pip install --upgrade setuptools wheel pip
pip install .
```

### Options

Additionally, pyJellyfish contains an option to manually specify which
Jellyfish version one wishes to build against. This can be done by
running setup.py with the the custom build command `jellyfish`.

``` {.sourceCode .shell}
source $HOME/.virtualenvs/km/bin/activate
python setup.py jellyfish --version 2.2.10
```

Note that the setup script will automatically detect if jellyfish is
installed on your system and build against it if found. After running
the previous commands, installation will proceed as usual, skipping the
jellyfish installation step.

``` {.sourceCode .shell}
pip install .
```

#### Requirements

-   Python 3.6.0 or later

[py-image]: https://img.shields.io/badge/python-3.6-blue.svg
[py-link]: https://www.python.org/download/releases/3.6.0
[pypi-image]: https://img.shields.io/pypi/v/pyjellyfish.svg
[pypi-link]: https://pypi.python.org/pypi/pyjellyfish
[ci-image]: https://travis-ci.org/iric-soft/pyJellyfish.svg?branch
[ci-link]: https://travis-ci.org/iric-soft/pyJellyfish
