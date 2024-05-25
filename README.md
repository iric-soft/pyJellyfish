pyJellyfish : Python wrapper around Jellyfish
=============================================

[![Python version][py3.8-image]][py3.8-link]
[![Python version][py3.9-image]][py3.9-link]
[![Python version][py3.10-image]][py3.10-link]
[![Python version][py3.11-image]][py3.11-link]
[![Python version][py3.12-image]][py3.12-link]
[![PyPi version][pypi-image]][pypi-link]

Introduction
------------

This tool essentially serves as an installer for the k-mer counter Jellyfish
for use with Python. A small bundle of utilities is also included. A typical
use-case for this package would be km: <https://github.com/iric-soft/km>.

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
pip install --upgrade pip
pip install .
```

### Options

Note that pyJellyfish has an option to manually specify which
Jellyfish version one wishes to build against. This can be done by
running pip install with specific arguments:

``` {.sourceCode .shell}
source $HOME/.virtualenvs/km/bin/activate
pip install . --config-settings="--build-option='--jf-version=2.3.0'"
```

For building pyJellyfish distributions, use the `build` command:

``` {.sourceCode .shell}
source $HOME/.virtualenvs/km/bin/activate
pip install build
python -m build --config-setting="--build-option='--jf-version=2.3.0'"
```

#### Requirements

-   Python 3.8.0 or later

[py3.8-image]: https://img.shields.io/badge/python-3.8-blue.svg
[py3.8-link]: https://www.python.org/downloads/release/python-380
[py3.9-image]: https://img.shields.io/badge/python-3.9-blue.svg
[py3.9-link]: https://www.python.org/downloads/release/python-390
[py3.10-image]: https://img.shields.io/badge/python-3.10-blue.svg
[py3.10-link]: https://www.python.org/downloads/release/python-3100
[py3.11-image]: https://img.shields.io/badge/python-3.11-blue.svg
[py3.11-link]: https://www.python.org/downloads/release/python-3110
[py3.12-image]: https://img.shields.io/badge/python-3.12-blue.svg
[py3.12-link]: https://www.python.org/downloads/release/python-3120

[pypi-image]: https://img.shields.io/pypi/v/pyjellyfish.svg
[pypi-link]: https://pypi.python.org/pypi/pyjellyfish
