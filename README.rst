
======================================================
pyJellyfish : a wrapper around k-mer counter Jellyfish
======================================================

+-------------------------------------------------------------+-----------------------------------------------------------------+-----------------------------------------------------------------------------+
| .. image:: https://img.shields.io/badge/python-3.5-blue.svg | .. image:: https://travis-ci.org/iric-soft/pyJellyfish.svg?branch=master | .. image:: https://codecov.io/gh/iric-soft/pyJellyfish/branch/master/graph/badge.svg |
|    :target: https://www.python.org/download/releases/3.5.0/ |    :target: https://travis-ci.org/iric-soft/pyJellyfish                  |    :target: https://codecov.io/gh/iric-soft/pyJellyfish/                             |
+-------------------------------------------------------------+-----------------------------------------------------------------+-----------------------------------------------------------------------------+

-------------
Introduction:
-------------

This tool essentially serves as an installer for Jellyfish for use with Python.  A bundle of utilities are also included as a bonus.

-------
Citing:
-------
* Guillaume Marcais and Carl Kingsford, A fast, lock-free approach for efficient parallel counting of occurrences of k-mers. Bioinformatics (2011) 27(6): 764-770; doi: https://doi.org/10.1093/bioinformatics/btr011

--------
Install:
--------

With pip:
---------

.. code:: shell

  python -m venv $HOME/.virtualenvs/km
  source $HOME/.virtualenvs/km/bin/activate
  pip install --upgrade setuptools wheel pip
  pip install .

Requirements:
*************
* Python 3.5.0 or later
