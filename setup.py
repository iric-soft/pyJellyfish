#!/usr/bin/env python3

import os
import sys
import tarfile
from contextlib import contextmanager
from glob import glob
from logging import INFO
from setuptools import Command, Extension, find_packages, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.errors import OptionError, SetupError
from subprocess import CalledProcessError, check_output


def safe_extract_tarfile(tarball, destination):
    with tarfile.open(tarball, 'r:gz') as tar:
        def is_within_directory(directory, target):

            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)

            prefix = os.path.commonprefix([abs_directory, abs_target])

            return prefix == abs_directory

        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):

            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")

            tar.extractall(path, members, numeric_owner=numeric_owner)

        safe_extract(tar, destination)


def locate(pkg, extra_args=[]):
    try:
        output = check_output(extra_args + ['which', pkg], universal_newlines=True)
        return os.path.abspath(output.strip())
    except CalledProcessError:
        return None


def is_needed_patchelf():
    if sys.platform == 'linux':
        patchelf_executable = locate(
            'patchelf',
            ['env', 'PATH='+os.path.abspath('./jf/bin')+':'+os.environ['PATH']]
        )
        return not bool(patchelf_executable)
    return False


@contextmanager
def pushd(dirname, makedirs=False, mode=0o777, exist_ok=False):
    """From: https://github.com/jimporter/patchelf-wrapper/blob/master/setup.py
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
        """Override spawn because we need the flexibility to be able
        to change cwd in subprocesses.
        """
        with pushd(cwd):
            super().spawn(cmd)


class JellyfishCommand(SuperCommand):
    """Custom Jellyfish command for compiling jellyfish."""

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
                raise OptionError(
                        "error in jellyfish-version option: accepted versions " +
                        "are 2.2.10 and 2.3.0"
                    )
        else:
            self.version = '2.3.0'


    def run(self):
        self.announce(
            '%s\nInstalling jellyfish v%s\n%s' %('*'*40, self.version, '*'*40),
            level=INFO
        )

        lib_path = os.path.abspath(
            './jf/lib/python%s.%s/site-packages'
            % tuple(sys.version.split('.')[:2])
        )

        dir_name = 'jellyfish-%s' % self.version
        jf_tarball = os.path.join('./jf/pkgs', '%s.tar.gz' % dir_name)

        build_dir = os.path.abspath('./jf/build')
        prefix = os.path.abspath('./jf')

        env_pkg_config_path = os.environ.get('PKG_CONFIG_PATH')
        _pkg_config_path = '%s/lib/pkgconfig:%s' % (prefix, env_pkg_config_path)

        patchelf_executable = locate(
            'patchelf',
            ['env', 'PATH='+os.path.abspath('./jf/bin')+':'+os.environ['PATH']]
        )

        if sys.platform == 'linux':
            if patchelf_executable is None:
                raise SetupError('No patchelf executable found or installed')
            else:
                self.announce('Found patchelf at ' + patchelf_executable, level=INFO)

        def get_ext_name():
            ext_path = glob(os.path.join(lib_path, '_dna_jellyfish*'))
            assert len(ext_path) == 1
            ext_file = os.path.basename(ext_path[0])
            return ext_file

        def get_lib_name():
            ext_file = get_ext_name()
            if sys.platform == 'linux':
                out = check_output(['ldd', ext_file])
                libs = [x for x in out.decode().split('\n') if 'libjellyfish' in x]
                assert len(libs) == 1
                lib = libs[0].strip().split(' ')[0]
            elif sys.platform == 'darwin':
                out = check_output(['otool', '-L', ext_file])
                libs = [x for x in out.decode().split('\n')[1:] if 'libjellyfish' in x]
                assert len(libs) == 1
                lib = os.path.basename(libs[0].strip().split(' ')[0])
            return lib

        self.mkpath(build_dir)

        safe_extract_tarfile(jf_tarball, "./jf/build")

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
                'PKG_CONFIG_PATH=' + _pkg_config_path,
                sys.executable, '-m', 'pip',
                'install',
                '.',
                '--target', lib_path,
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
            self.mkpath('pyjellyfish/.libs')

            self.copy_file(
                os.path.join('./jf/lib', get_lib_name()),
                os.path.join('./pyjellyfish/.libs', get_lib_name())
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

            # the following `install_name_tool` commands simply copies what
            # `delocate` (https://github.com/matthew-brett/delocate) was
            # doing when run on this project's wheel; the goal here is
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
            level=INFO
        )


class PatchElfCommand(SuperCommand):
    """Custom command for detecting and installing patchelf"""

    description = 'install patchelf with pip in the current build directory'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.mkpath('jf/bin')

        lib_path = os.path.abspath(
            './jf/lib/python%s.%s/site-packages'
            % tuple(sys.version.split('.')[:2])
        )

        if sys.prefix == sys.base_prefix:
            # not in a virtual environment;
            # a handy hack for installing bin and lib in a custom
            # environment when not using venv (not recommended):
            # https://stackoverflow.com/a/29103053/16653409

            self.spawn(
                [
                    'env',
                    'PYTHONUSERBASE=%s' % os.path.abspath('./jf'),
                    sys.executable, '-m', 'pip',
                    'install',
                    'patchelf',
                    '--user',
                    '--upgrade',
                    '--no-cache-dir',
                    '--force'
                ]
            )

        else:
            # in a virtual environment;
            # looks like there is no native way for pip to specify a target
            # build directory: https://github.com/pypa/pip/issues/3934,
            # defaulting to a simple mv command

            self.spawn(
                [
                    sys.executable, '-m', 'pip',
                    'install',
                    'patchelf',
                    '--target', lib_path,
                    '--upgrade',
                    '--no-cache-dir',
                    '--force'
                ]
            )

            self.move_file(
                os.path.join(lib_path, 'bin', 'patchelf'),
                './jf/bin/'
            )


class BuildExtCommand(build_ext):
    def build_extension(self, ext):
        ext_dest = self.get_ext_fullpath(ext.name)
        self.mkpath(os.path.dirname(ext_dest))
        ext_loc = os.path.join(os.getcwd(), os.path.basename(ext_dest))
        if os.path.isfile(ext_loc):
            self.copy_file(ext_loc, ext_dest)
        else:
            raise OptionError(
                "Cannot find extension %s located at %s" % (
                    ext.name,
                    os.path.basename(ext_loc)
                ))


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
                """Returns true if jellyfish is not installed.

                Also makes sure the imported jellyfish is the one
                built in the installation repo and not a pre-installed
                version in python's libraries folder making sure a
                _dna_jellyfish extension module exists, otherwise a
                DistutilsOptionError will be raised.
                """

                try:
                    import dna_jellyfish
                    jf_loc = os.path.abspath(dna_jellyfish.__file__)
                    cur_loc = os.path.abspath(os.getcwd())
                    if os.path.dirname(jf_loc) == cur_loc:
                        return False
                except ModuleNotFoundError:
                    pass

                return True

            def has_absent_patchelf(self):
                if self.has_absent_jellyfish():
                    return is_needed_patchelf()
                return False

            def expand_sub_commands(self):
                for add_sub_cmd in self.add_sub_cmds:
                    if add_sub_cmd not in self.sub_commands:
                        self.sub_commands.insert(0, add_sub_cmd)

            # order is important
            add_sub_cmds = [
                ('jellyfish', has_absent_jellyfish),
                ('patchelf', has_absent_patchelf)
            ]

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
    version='1.2.0',
    description='A python wrapper around DNA k-kmer counter Jellfish',
    long_description=long_description,
    url='https://github.com/iric-soft/pyJellyfish',
    author='Albert Feghaly',
    author_email='bioinformatique@iric.ca',
    license='BSD',
    classifiers=classifiers,
    keywords='k-mer DNA',
    # https://setuptools.pypa.io/en/latest/userguide/datafiles.html
    # https://stackoverflow.com/a/58050701
    # https://stackoverflow.com/a/54953494
    packages=['pyjellyfish'],
    package_data={'pyjellyfish': ['.*libs/*']},
    include_package_data=True,
    exclude_package_data={"jf": ["pkgs/*"]},
    ext_modules=[Extension("_dna_jellyfish", sources=[])],
    py_modules = ["dna_jellyfish"],
    python_requires='>=3.6',
    cmdclass={
        'jellyfish': JellyfishCommand,
        'patchelf': PatchElfCommand,
        'build_py': BuildPyCommand,
        'build_ext': BuildExtCommand,
        'develop': DevelopCommand
    }
)

if __name__ == '__main__':
    setup(**metadata)
