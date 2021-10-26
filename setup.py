#!/usr/bin/env python3

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from distutils.cmd import Command
from distutils import log
from distutils.errors import DistutilsOptionError
from functools import partial
import os
import sys


def spawn(cmd, search_path, dry_run, cwd, env):
    """A wrapper around distutils.spawn with cwd and env
    enabled. Uses multiprocessing to edit os.environ and for 
    calling os.chdir() without any headaches.
    """

    from concurrent.futures import ProcessPoolExecutor
    ex = ProcessPoolExecutor(max_workers=1)
    p = ex.submit(_spawn, cmd, search_path, dry_run, cwd, env, os.getpid())
    p.result()
    ex.shutdown()


def _spawn(cmd, search_path, dry_run, cwd, env, main_pid):
    """this function is only meant to be run inside a new process"""
    import distutils.spawn
    assert os.getpid() != main_pid
    if env is not None:
        os.environ = dict(os.environ, **env)
    if cwd is not None:
        os.chdir(cwd)
    distutils.spawn.spawn(cmd, search_path, dry_run=dry_run)


class JellyfishCommand(Command):
    """ Custom Jellyfish commands for compiling jellyfish. """

    description = 'build and install jellyfish in default libpath'

    user_options = [
        ('version=', None,
         'jellyfish version [2.2.10, 2.3.0] (default: 2.3.0)')
    ]

    def initialize_options(self):
        self.version = None

    def finalize_options(self):
        if self.version:
            if self.version not in  ['2.2.10', '2.3.0']:
                raise DistutilsOptionError(
                        "error in jellyfish-version option: accepted versions " +
                        "are 2.2.10 and 2.3.0"
                    )
        else:
            self.version = '2.3.0'

    def run(self):
        self.announce(
            '%s\nInstalling jellyfish v%s\n%s' %('*'*40, self.version, '*'*40),
            level=log.INFO
        )

        self.mkpath('build_jf')

        dir_name = 'jellyfish-%s' % self.version
        base_url = 'https://github.com/gmarcais/Jellyfish'
        url = '%s/releases/download/v%s/%s.tar.gz' % (
                base_url,
                self.version,
                dir_name
            )

        build_dir = os.path.abspath('build_jf')
        prefix = os.path.normpath(sys.prefix)

        env_pkg_config_path = os.environ.get('PKG_CONFIG_PATH')
        _pkg_config_path = '%s/lib/pkgconfig:%s' % (
                prefix,
                env_pkg_config_path
            )

        commands = [
            partial(
                self.spawn,
                ['curl', '-L', url, '--output', dir_name+'.tar.gz'],
                cwd=build_dir
            ),
            partial(
                self.spawn,
                ['tar', 'xzvf', dir_name+'.tar.gz'],
                cwd=build_dir
            ),
            partial(
                self.spawn,
                ['./configure', '--prefix', prefix],
                #['./configure', '--prefix', prefix, '--enable-python-binding'],
                # --enable-python-binding will install jellyfish.py in addition
                # to dna_jellyfish module without passing through pip which
                # is messy and does not address the conflict with the other
                # jellyfish Debian package
                cwd=os.path.join(build_dir, dir_name)
            ),
            partial(
                self.spawn,
                ['make', '-j', '8'],
                cwd=os.path.join(build_dir, dir_name)
            ),
            partial(
                self.spawn,
                ['make', 'install'],
                cwd=os.path.join(build_dir, dir_name)
            ),
            partial(
                # --enable-python-binding fails starting from version 2.2.7
                self.spawn,
                [sys.executable, '-m', 'pip', 'install', '.'],
                cwd=os.path.join(build_dir, dir_name, 'swig', 'python'),
                env=dict(PKG_CONFIG_PATH=_pkg_config_path)
            )
        ]

        for cmd in commands:
            cmd()

        self.announce(
            '%s\nSuccessfully installed jellyfish\n%s' %('*'*40, '*'*40),
            level=log.INFO
        )

    def spawn(self, cmd, search_path=1, cwd=None, env=None):
        """Override spawn because we want flexible cwd and env
        functionalities. An alternative would have been to copy
        distutils.spawn and make slight edits for adjusting
        cwd and env arguments directly in Popen. The current
        method was chosen to reduce the number of lines in this
        file.
        """

        spawn(cmd, search_path, self.dry_run, cwd, env)


class CustomCommand(type):
    """Custom setuptools.command command."""

    def __new__(cls, clsname, bases, attr):
        attr['run'] = cls.run
        attr['has_absent_jellyfish'] = cls.has_absent_jellyfish
        attr['expand_sub_commands'] = cls.expand_sub_commands 
        attr['add_sub_cmd'] = cls.add_sub_cmd
        return super(CustomCommand, cls).__new__(cls, clsname, bases, attr)

    def run(self):
        self.expand_sub_commands()
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)
        super(self.__class__, self).run()

    def has_absent_jellyfish(self):
        """Returns true if jellyfish is not installed."""
        try:
            import dna_jellyfish
            return False
        except ModuleNotFoundError:
            return True

    def expand_sub_commands(self):
        if self.add_sub_cmd not in self.sub_commands:
            self.sub_commands.insert(0, self.add_sub_cmd)

    add_sub_cmd = ('jellyfish', has_absent_jellyfish)


class BuildPyCommand(build_py, metaclass=CustomCommand):
    """Custom build command."""
    pass


class DevelopCommand(develop, metaclass=CustomCommand):
    """Custom develop command."""
    pass


# Get the long description from the README file
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

classifiers = [
    'Development Status :: 5 - Production/Stable',

    'Intended Audience :: Science/Research',
    'Intended Audience :: Healthcare Industry',
    'Topic :: Scientific/Engineering :: Bio-Informatics',
    'Topic :: Software Development',
    'Topic :: Software Development :: Build Tools',

    'License :: OSI Approved :: MIT License',

    'Programming Language :: Python :: 3.7',

    'Natural Language :: English',
]

metadata = dict(
    name='pyjellyfish',
    version='0.1.0',
    description='A python wrapper around DNA k-kmer counter Jellfish',
    long_description=long_description,
    url='https://github.com/iric-soft/pyJellyfish',
    author='Albert Feghaly',
    author_email='bioinformatique@iric.ca',
    license='MIT',
    classifiers=classifiers,
    keywords='k-mer DNA',
    packages=find_packages(),
    python_requires='>=3.5',
    cmdclass={
        'jellyfish': JellyfishCommand,
        'build_py': BuildPyCommand,
        'develop': DevelopCommand
    }
)

if __name__ == '__main__':
    setup(**metadata)
