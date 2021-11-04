#!/usr/bin/env python3

from setuptools import setup, find_packages, Extension
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.command.build_ext import build_ext
from distutils.cmd import Command
from distutils import log
from distutils.errors import DistutilsOptionError
from functools import partial
from glob import glob
import os
import sys
import shutil


class SuperCommand(Command):
    def spawn(self, cmd, search_path=1, cwd=None):
        """Override spawn because we want flexible cwd and env
        functionalities. An alternative would have been to copy
        distutils.spawn and make slight edits for adjusting
        cwd and env arguments directly in Popen. The current
        method was chosen to reduce the number of lines in this
        file.
        """

        self.spawn_multiprocess(cmd, search_path, self.dry_run, cwd)


    @classmethod
    def spawn_multiprocess(cls, cmd, search_path, dry_run, cwd):
        """A wrapper around distutils.spawn with custom cwd functionality
        enabled. Uses multiprocessing to edit os.environ and for
        calling os.chdir() to avoid chaging global variables.
        """

        from concurrent.futures import ProcessPoolExecutor
        ex = ProcessPoolExecutor(max_workers=1)
        p = ex.submit(cls._spawn, cmd, search_path, dry_run, cwd, os.getpid())
        p.result()
        ex.shutdown()


    @staticmethod
    def _spawn(cmd, search_path, dry_run, cwd, main_pid):
        """This function is only meant to be run inside a new process"""

        import distutils.spawn
        assert os.getpid() != main_pid
        if cwd is not None:
            os.chdir(cwd)
        distutils.spawn.spawn(cmd, search_path, dry_run=dry_run)


class JellyfishCommand(SuperCommand):
    """ Custom Jellyfish commands for compiling jellyfish. """

    description = 'build and install jellyfish in default libpath'

    user_options = [(
            'version=',
            None,
            'jellyfish version [2.2.10, 2.3.0] (default: 2.3.0)'
        )]


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

        self.mkpath('jfbuild/jf')

        dir_name = 'jellyfish-%s' % self.version
        base_url = 'https://github.com/gmarcais/Jellyfish'
        url = '%s/releases/download/v%s/%s.tar.gz' % (
                base_url,
                self.version,
                dir_name
            )

        build_dir = os.path.abspath('jfbuild/jf')
        prefix = os.path.join(os.getcwd(), 'jfbuild/jf/jellyfish')

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
                # jellyfish Debian package (in newer versions)
                # Also adding --enable-python-binding by itself is not sufficient
                # starting from version 2.2.7
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
                self.spawn,
                [
                    'env',
                    'PKG_CONFIG_PATH=' + _pkg_config_path,
                    sys.executable, '-m', 'pip',
                    'install',
                    '.',
                    '--target', os.path.join(os.getcwd(), 'jfbuild/dnajf'),
                    '--upgrade'
                ],
                cwd=os.path.join(build_dir, dir_name, 'swig', 'python')
            )
        ]

        for cmd in commands:
            cmd()

        ext_path = glob('jfbuild/dnajf/_dna_jellyfish*')
        assert len(ext_path) == 1
        ext_file = os.path.basename(ext_path[0])
        shutil.copyfile('jfbuild/dnajf/dna_jellyfish.py', 'dna_jellyfish.py')
        shutil.copyfile(os.path.join('jfbuild/dnajf', ext_file), ext_file)

        self.announce(
            '%s\nSuccessfully installed jellyfish\n%s' %('*'*40, '*'*40),
            level=log.INFO
        )


class BuildExtCommand(build_ext):
    def build_extension(self, ext):
        ext_dest = self.get_ext_fullpath(ext.name)
        self.mkpath(os.path.dirname(ext_dest))
        ext_loc = os.path.join(os.getcwd(), os.path.basename(ext_dest))
        shutil.copyfile(ext_loc, ext_dest)


# Ideally, this class would be a Singleton, but that would be
# unnecessary for our purposes here.  A great Singleton implementation
# can be found here: https://stackoverflow.com/a/7346105/16653409
#@Singleton
class ClassFactory(object):
    def __init__(self):
        self.classes = {}

    def __call__(self, *parents):
        name = ':'.join([p.__name__ for p in parents])
        if name not in self.classes:
            new_class = self.create(parents)
            self.classes[name] = new_class
        return self.classes[name]

    def create(self, parents):

        class CustomCommand(*parents):
            """Custom setuptools.command command."""

            def run(self):
                self.expand_sub_commands()
                for cmd_name in self.get_sub_commands():
                    self.run_command(cmd_name)
                super(CustomCommand, self).run()

            def has_absent_jellyfish(self):
                """Returns true if jellyfish is not installed."""
                try:
                    import dna_jellyfish
                    return False
                except (ModuleNotFoundError, ImportError):
                    return True

            def expand_sub_commands(self):
                if self.add_sub_cmd not in self.sub_commands:
                    self.sub_commands.insert(0, self.add_sub_cmd)

            add_sub_cmd = ('jellyfish', has_absent_jellyfish)

        return CustomCommand


factory = ClassFactory()

def create_command_class(klass):
    return factory(*klass.__bases__)


@create_command_class
class BuildPyCommand(build_py):
    """Custom build command."""
    pass


@create_command_class
class DevelopCommand(develop):
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

    'License :: OSI Approved :: BSD 3-clause License',

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
    license='BSD',
    classifiers=classifiers,
    keywords='k-mer DNA',
    packages=find_packages(),
    ext_modules=[Extension("_dna_jellyfish", sources=[])],
    py_modules = ["dna_jellyfish"],
    python_requires='>=3.5',
    cmdclass={
        'jellyfish': JellyfishCommand,
        'build_py': BuildPyCommand,
        'build_ext': BuildExtCommand,
        'develop': DevelopCommand
    }
)

if __name__ == '__main__':
    setup(**metadata)
