#!/usr/bin/env python3

from setuptools import setup, find_packages, Extension
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.command.build_ext import build_ext
from distutils.cmd import Command
from distutils import log
from contextlib import contextmanager
from distutils.errors import DistutilsOptionError
from glob import glob
import tarfile
import os
import sys
import subprocess


@contextmanager
def pushd(dirname, makedirs=False, mode=0o777, exist_ok=False):
    """This function was shamelessly copied from
    https://github.com/jimporter/patchelf-wrapper/blob/master/setup.py
    with slight modifications
    """
    old = os.getcwd()
    if makedirs and dirname is not None:
        try:
            os.makedirs(dirname, mode)
        except OSError as e:
            if ( not exist_ok or e.errno != errno.EEXIST or
                 not os.path.isdir(dirname) ):
                raise

    if dirname is not None:
        os.chdir(dirname)

    try:
        yield
    finally:
        os.chdir(old)


class SuperCommand(Command):
    def spawn(self, cmd, cwd=None):
        """Override spawn because we want flexible to able
        to change cwd in subprocesses.
        """

        with pushd(cwd):
            super().spawn(cmd)


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

        lib_path = os.path.abspath(
            './jf/lib/python%s/site-packages'
            % sys.version[:3]
        )

        dir_name = 'jellyfish-%s' % self.version
        jf_tarball = os.path.join('./jf/pkgs', '%s.tar.gz' % dir_name)

        build_dir = os.path.abspath('./jf/build')
        prefix = os.path.abspath('./jf')

        env_pkg_config_path = os.environ.get('PKG_CONFIG_PATH')
        _pkg_config_path = '%s/lib/pkgconfig:%s' % (
                prefix,
                env_pkg_config_path
            )

        # from: https://github.com/jimporter/patchelf-wrapper/blob/master/setup.py
        if sys.platform == 'linux':
            try:
                output = subprocess.check_output(
                    ['which', 'patchelf'], universal_newlines=True
                )
                patchelf_executable = os.path.abspath(output.strip())
                self.announce('Found patchelf at {}'.format(output),
                              log.INFO)
                found_patchelf = True
            except Exception:
                self.announce('patchelf not found', log.INFO)
                patchelf_executable = os.path.abspath('./jf/bin/patchelf')
                found_patchelf = False
        else:
            patchelf_executable = None
            found_patchelf = None

        def get_ext_name():
            ext_path = glob(os.path.join(lib_path, '_dna_jellyfish*'))
            assert len(ext_path) == 1
            ext_file = os.path.basename(ext_path[0])
            return ext_file

        def get_lib_name():
            ext_file = get_ext_name()
            if sys.platform == 'linux':
                out = subprocess.check_output(['ldd', ext_file])
                libs = [x for x in out.decode().split('\n') if 'libjellyfish' in x]
                assert len(libs) == 1
                lib = libs[0].strip().split(' ')[0]
            elif sys.platform == 'darwin':
                out = subprocess.check_output(['otool', '-L', ext_file])
                libs = [x for x in out.decode().split('\n')[1:] if 'libjellyfish' in x]
                assert len(libs) == 1
                lib = os.path.basename(libs[0].strip().split(' ')[0])
            return lib

        self.mkpath(build_dir)

        with tarfile.open(jf_tarball, 'r:gz') as tar:
            tar.extractall('./jf/build')

        self.spawn(
            ['./configure', '--prefix', prefix],
            #['./configure', '--prefix', prefix, '--enable-python-binding'],
            # --enable-python-binding will install jellyfish.py in addition
            # to dna_jellyfish module without passing through pip which
            # is messy and does not address the conflict with the other
            # jellyfish Debian package (in newer versions)
            # Also adding --enable-python-binding by itself is not sufficient
            # starting from version 2.2.7
            cwd=os.path.join(build_dir, dir_name)
        )

        self.spawn(
            ['make', '-j', '8'],
            cwd=os.path.join(build_dir, dir_name)
        )

        self.spawn(
            ['make', 'install'],
            cwd=os.path.join(build_dir, dir_name)
        )

        self.spawn(
            [
                'env',
                'PKG_CONFIG_PATH=%s' % _pkg_config_path,
                sys.executable, '-m', 'pip',
                'install',
                '.',
                '--target', os.path.join(os.getcwd(), lib_path),
                '--upgrade'
            ],
            cwd=os.path.join(build_dir, dir_name, 'swig', 'python')
        )

        self.copy_file(
            os.path.join(lib_path, 'dna_jellyfish.py'),
            './dna_jellyfish.py'
        )

        self.copy_file(
            os.path.join(lib_path, get_ext_name()),
            os.path.join('.', get_ext_name())
        )

        if sys.platform == 'linux':
            self.mkpath('jf/bin')
            self.mkpath('pyjellyfish/.libs')

            self.copy_file(
                os.path.join('./jf/lib', get_lib_name()),
                os.path.join('./pyjellyfish/.libs', get_lib_name())
            )

            if found_patchelf:
                pass
            elif sys.prefix == sys.base_prefix:
                # not in a virtual environment
                # a handy hack for install bin and lib in a costum
                # environment when not using venv (not recommended):
                # https://stackoverflow.com/a/29103053/16653409
                self.spawn(
                    [
                        'env',
                        'PYTHONUSERBASE=%s' % os.path.abspath('./jf'),
                        sys.executable, '-m', 'pip',
                        'install',
                        'patchelf-wrapper',
                        '--user',
                        '--upgrade',
                        '--no-cache-dir',
                        '--force'
                    ]
                )
            else:
                # in a virtual environment
                self.spawn(
                    [
                        sys.executable, '-m', 'pip',
                        'install',
                        'patchelf-wrapper',
                        '--target', lib_path,
                        '--upgrade',
                        '--no-cache-dir',
                        '--force'
                    ]
                )

                # looks like there is no native way for pip to specify a target
                # build directory: https://github.com/pypa/pip/issues/3934,
                # defaulting to a simple mv command
                self.move_file(
                    os.path.join(os.path.dirname(sys.executable), 'patchelf'),
                    './jf/bin/'
                )

            self.spawn(
                [
                    patchelf_executable,
                    '--set-rpath',
                    '$ORIGIN/pyjellyfish/.libs',
                    get_ext_name()
                ]
            )

        elif sys.platform == 'darwin':
            self.mkpath('pyjellyfish/.dylibs')

            self.copy_file(
                os.path.join('./jf/lib', get_lib_name()),
                os.path.join('./pyjellyfish/.dylibs', get_lib_name())
            )

            # the following `install_name_tool` commands simply copy what
            # `delocate` (https://github.com/matthew-brett/delocate) was
            # doing when run against on this project's wheel; the goal was
            # for everything to happen during installation
            self.spawn(
                [
                    'install_name_tool',
                    '-change',
                    os.path.abspath(os.path.join('./jf/lib', get_lib_name())),
                    os.path.join('@loader_path/pyjellyfish/.dylibs', get_lib_name()),
                    get_ext_name()
                ]
            )

            # this command doesn't seem to be essential, as per this answer:
            # https://stackoverflow.com/a/35220218/16653409, but is kept just
            # because it was being run by delocate
            self.spawn(
                [
                    'install_name_tool',
                    '-id',
                    os.path.join('/DLC/pyjellyfish/.dylibs', get_lib_name()),
                    os.path.join('./pyjellyfish/.dylibs', get_lib_name())
                ]
            )

        self.announce(
            '%s\nSuccessfully installed jellyfish\n%s' %('*'*40, '*'*40),
            level=log.INFO
        )


class BuildExtCommand(build_ext):
    def build_extension(self, ext):
        ext_dest = self.get_ext_fullpath(ext.name)
        self.mkpath(os.path.dirname(ext_dest))
        ext_loc = os.path.join(os.getcwd(), os.path.basename(ext_dest))
        if os.path.isfile(ext_loc):
            self.copy_file(ext_loc, ext_dest)
        else:
            raise DistutilsOptionError('Cannot find extension %s' % ext_loc)



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
                # this assert just makes sure that don't need to manually
                # set binary distribution to True by following the same method
                # as this answer: https://stackoverflow.com/a/24793171/16653409
                assert self.distribution.has_ext_modules()
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
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

classifiers = [
    'Development Status :: 5 - Production/Stable',

    'Intended Audience :: Science/Research',
    'Intended Audience :: Healthcare Industry',
    'Topic :: Scientific/Engineering :: Bio-Informatics',
    'Topic :: Software Development',
    'Topic :: Software Development :: Build Tools',

    'License :: OSI Approved :: BSD License',

    'Programming Language :: Python :: 3.6',

    'Natural Language :: English',
]

metadata = dict(
    name='pyjellyfish',
    version='1.0.1',
    description='A python wrapper around DNA k-kmer counter Jellfish',
    long_description=long_description,
    url='https://github.com/iric-soft/pyJellyfish',
    author='Albert Feghaly',
    author_email='bioinformatique@iric.ca',
    license='BSD',
    classifiers=classifiers,
    keywords='k-mer DNA',
    packages=['pyjellyfish', 'jf'],
    package_data={'pyjellyfish': ['.*libs/*'], 'jf': ['pkgs/*']},
    ext_modules=[Extension("_dna_jellyfish", sources=[])],
    py_modules = ["dna_jellyfish"],
    python_requires='>=3.6',
    cmdclass={
        'jellyfish': JellyfishCommand,
        'build_py': BuildPyCommand,
        'build_ext': BuildExtCommand,
        'develop': DevelopCommand
    }
)

if __name__ == '__main__':
    setup(**metadata)
