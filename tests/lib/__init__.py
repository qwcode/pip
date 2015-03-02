from __future__ import absolute_import

import os
import sys
import re
import textwrap
import site

import scripttest
import virtualenv

from pip._vendor import pkg_resources
from pip.utils import normalize_path, dist_is_editable
from tests.lib.path import Path

DATA_DIR = Path(__file__).folder.folder.join("data").abspath
SRC_DIR = Path(__file__).abspath.folder.folder.folder

pyversion = sys.version[:3]


def path_to_url(path):
    """
    Convert a path to URI. The path will be made absolute and
    will not have quoted path parts.
    (adapted from pip.util)
    """
    path = os.path.normpath(os.path.abspath(path))
    drive, path = os.path.splitdrive(path)
    filepath = path.split(os.path.sep)
    url = '/'.join(filepath)
    if drive:
        return 'file:///' + drive + url
    return 'file://' + url


class TestData(object):
    """
    Represents a bundle of pre-created test data.

    This copies a pristine set of test data into a root location that is
    designed to be test specific. The reason for this is when running the tests
    concurrently errors can be generated because the related tooling uses
    the directory as a work space. This leads to two concurrent processes
    trampling over each other. This class gets around that by copying all
    data into a directory and operating on the copied data.
    """

    def __init__(self, root, source=None):
        self.source = source or DATA_DIR
        self.root = Path(root).abspath

    @classmethod
    def copy(cls, root):
        obj = cls(root)
        obj.reset()
        return obj

    def reset(self):
        self.root.rmtree()
        self.source.copytree(self.root)

    @property
    def packages(self):
        return self.root.join("packages")

    @property
    def packages2(self):
        return self.root.join("packages2")

    @property
    def packages3(self):
        return self.root.join("packages3")

    @property
    def src(self):
        return self.root.join("src")

    @property
    def indexes(self):
        return self.root.join("indexes")

    @property
    def reqfiles(self):
        return self.root.join("reqfiles")

    @property
    def find_links(self):
        return path_to_url(self.packages)

    @property
    def find_links2(self):
        return path_to_url(self.packages2)

    @property
    def find_links3(self):
        return path_to_url(self.packages3)

    def index_url(self, index="simple"):
        return path_to_url(self.root.join("indexes", index))


class TestFailure(AssertionError):
    """
    An "assertion" failed during testing.
    """
    pass


class ProjectNotInstalledError(AssertionError):
    """Raised when project not installed"""


class VersionConflictError(AssertionError):
    """Raised when a conflicting version is present"""


class DistInfoExpectedError(AssertionError):
    """Raised when a dist-info install is expected but not present"""


class EggInfoExpectedError(AssertionError):
    """Raised when a egg-info install is expected but not present"""


class UserInstallExpectedError(AssertionError):
    """Raised when a user install is expected but not present"""


class UserInstallUnexpectedError(AssertionError):
    """Raised when a user install is unexpected but present"""


class EditableInstallExpectedError(AssertionError):
    """Raised when an editable install is expected but not present"""


class PackageExpectedrror(AssertionError):
    """Raised when an import package is expected but not present"""


class PathExpectedrror(AssertionError):
    """Raised when a path is expected to be intalled but not present"""


class PathNotExpectedrror(AssertionError):
    """Raised when a path is not expected to be intalled but is present"""


class PthUpdateNotExpected(AssertionError):
    """Raised when easy-intall.pth is unexpectedly updated"""


class TestPipResult(object):
    """Return object from PipTestEnvironment.run"""

    def __init__(self, impl, verbose=False):
        self._impl = impl

        if verbose:
            print(self.stdout)
            if self.stderr:
                print('======= stderr ========')
                print(self.stderr)
                print('=======================')

    def __getattr__(self, attr):
        return getattr(self._impl, attr)

    if sys.platform == 'win32':

        @property
        def stdout(self):
            return self._impl.stdout.replace('\r\n', '\n')

        @property
        def stderr(self):
            return self._impl.stderr.replace('\r\n', '\n')

        def __str__(self):
            return str(self._impl).replace('\r\n', '\n')
    else:
        # Python doesn't automatically forward __str__ through __getattr__

        def __str__(self):
            return str(self._impl)

    # def assert_installed(self, pkg_name, editable=True, with_files=[],
    #                      without_files=[], without_egg_link=False,
    #                      use_user_site=False, sub_dir=False):
    def assert_installed(self, spec, package=None, editable=False,
                         user_install=False, dist_info=False, egg_info=False,
                         with_paths=[], without_paths=[]):
        """Assert that a requirement specifier is fulfilled, i.e that a project
        with a certain version specifier (or no specifier) is installed.

        Custom exceptions are used for the sake of testing.

        :param spec: project specifier (e.g. 'pip', or 'pip==1.6.0')
        :param package: an import package to confirm is present
        :param editable: confirm install is editable
        :param user_install: confirm as a user install
        :param dist_info: confirm as a dist-info install
        :param egg_info: confirm as a egg-info install
        :param with_paths: paths to confirm were installed
        :param without_paths: paths to confirm were not installed

        """

        env = self.test_env

        # create working set
        working_set = pkg_resources.WorkingSet([
            env.user_site_path,
            env.site_packages_path])

        # confirm spec is fulfilled
        req = pkg_resources.Requirement.parse(spec)
        try:
            installed_dist = working_set.find(req)
        except pkg_resources.VersionConflict as e:
            raise VersionConflictError(e)
        if installed_dist is None:
            raise ProjectNotInstalledError()

        install_location = normalize_path(installed_dist.location)
        is_user_install = install_location.startswith(
            normalize_path(env.user_site_path))

        # confirm user install
        if user_install and not is_user_install:
                raise UserInstallExpectedError()

        # confirm normal site install
        if not user_install and is_user_install:
                raise UserInstallUnexpectedError()

        # confirm editable or not
        is_editable = dist_is_editable(installed_dist)
        if editable and not is_editable:
            raise EditableInstallExpectedError()

        # confirm a certain package is present
        if package:
            package_path = os.path.join(install_location, package)
            if not os.path.exists(package_path):
                PackageExpectedrror()

        is_dist_info = (type(installed_dist) == pkg_resources.DistInfoDistribution)

        # confirm dist-info
        if dist_info and not is_dist_info:
            raise DistInfoExpectedError()

        # confirm egg-info
        if egg_info and is_dist_info:
            raise EggInfoExpectedError()

        # with_paths
        for p in with_paths:
            install_path = normalize_path(install_location, p)
            if install_path not in self.files_created:
                raise PathExpectedrror()

        # without_paths
        for p in without_paths:
            install_path = normalize_path(install_location, p)
            if install_path in self.files_created:
                raise PathNotExpectedrror()

        # confirm unexpected pth update
        pth_file = os.path.join(install_location, 'easy-install.pth')
        if not editable and pth_file in self.files_updated:
            raise PthUpdateNotExpected()


class PipTestEnvironment(scripttest.TestFileEnvironment):
    """
    A specialized TestFileEnvironment for testing pip
    """

    #
    # Attribute naming convention
    # ---------------------------
    #
    # Instances of this class have many attributes representing paths
    # in the filesystem.  To keep things straight, absolute paths have
    # a name of the form xxxx_path and relative paths have a name that
    # does not end in '_path'.

    exe = sys.platform == 'win32' and '.exe' or ''
    verbose = False

    def __init__(self, base_path, *args, **kwargs):
        # Make our base_path a test.lib.path.Path object
        base_path = Path(base_path)

        # Store paths related to the virtual environment
        _virtualenv = kwargs.pop("virtualenv")
        venv, lib, include, bin = virtualenv.path_locations(_virtualenv)
        # workaround for https://github.com/pypa/virtualenv/issues/306
        if hasattr(sys, "pypy_version_info"):
            lib = os.path.join(venv, 'lib-python', pyversion)
        self.venv_path = venv
        self.lib_path = lib
        self.include_path = include
        self.bin_path = bin

        if hasattr(sys, "pypy_version_info"):
            self.site_packages_path = self.venv_path.join("site-packages")
        else:
            self.site_packages_path = self.lib_path.join("site-packages")

        self.user_base_path = self.venv_path.join("user")
        self.user_bin_path = self.user_base_path.join(
            self.bin_path - self.venv_path
        )
        self.user_site_path = self.venv_path.join(
            "user",
            site.USER_SITE[len(site.USER_BASE) + 1:],
        )

        # Create a Directory to use as a scratch pad
        self.scratch_path = base_path.join("scratch").mkdir()

        # Set our default working directory
        kwargs.setdefault("cwd", self.scratch_path)

        # Setup our environment
        environ = kwargs.get("environ")
        if environ is None:
            environ = os.environ.copy()

        environ["PATH"] = Path.pathsep.join(
            [self.bin_path] + [environ.get("PATH", [])],
        )
        environ["PYTHONUSERBASE"] = self.user_base_path
        # Writing bytecode can mess up updated file detection
        environ["PYTHONDONTWRITEBYTECODE"] = "1"
        kwargs["environ"] = environ

        # Call the TestFileEnvironment __init__
        super(PipTestEnvironment, self).__init__(base_path, *args, **kwargs)

        # Expand our absolute path directories into relative
        for name in ["base", "venv", "lib", "include", "bin", "site_packages",
                     "user_base", "user_site", "user_bin", "scratch"]:
            real_name = "%s_path" % name
            setattr(self, name, getattr(self, real_name) - self.base_path)

        # Make sure temp_path is a Path object
        self.temp_path = Path(self.temp_path)
        # Ensure the tmp dir exists, things break horribly if it doesn't
        self.temp_path.mkdir()

        # create easy-install.pth in user_site, so we always have it updated
        #   instead of created
        self.user_site_path.makedirs()
        self.user_site_path.join("easy-install.pth").touch()


    def _ignore_file(self, fn):
        if fn.endswith('__pycache__') or fn.endswith(".pyc"):
            result = True
        else:
            result = super(PipTestEnvironment, self)._ignore_file(fn)
        return result

    def run(self, *args, **kw):
        if self.verbose:
            print('>> running %s %s' % (args, kw))
        cwd = kw.pop('cwd', None)
        run_from = kw.pop('run_from', None)
        assert not cwd or not run_from, "Don't use run_from; it's going away"
        cwd = cwd or run_from or self.cwd
        return TestPipResult(
            super(PipTestEnvironment, self).run(cwd=cwd, *args, **kw),
            verbose=self.verbose,
        )

    def pip(self, *args, **kwargs):
        return self.run("pip", *args, **kwargs)

    def pip_install_local(self, *args, **kwargs):
        return self.pip(
            "install", "--no-index",
            "--find-links", path_to_url(os.path.join(DATA_DIR, "packages")),
            *args, **kwargs
        )


# FIXME ScriptTest does something similar, but only within a single
# ProcResult; this generalizes it so states can be compared across
# multiple commands.  Maybe should be rolled into ScriptTest?
def diff_states(start, end, ignore=None):
    """
    Differences two "filesystem states" as represented by dictionaries
    of FoundFile and FoundDir objects.

    Returns a dictionary with following keys:

    ``deleted``
        Dictionary of files/directories found only in the start state.

    ``created``
        Dictionary of files/directories found only in the end state.

    ``updated``
        Dictionary of files whose size has changed (FIXME not entirely
        reliable, but comparing contents is not possible because
        FoundFile.bytes is lazy, and comparing mtime doesn't help if
        we want to know if a file has been returned to its earlier
        state).

    Ignores mtime and other file attributes; only presence/absence and
    size are considered.

    """
    ignore = ignore or []

    def prefix_match(path, prefix):
        if path == prefix:
            return True
        prefix = prefix.rstrip(os.path.sep) + os.path.sep
        return path.startswith(prefix)

    start_keys = set([k for k in start.keys()
                      if not any([prefix_match(k, i) for i in ignore])])
    end_keys = set([k for k in end.keys()
                    if not any([prefix_match(k, i) for i in ignore])])
    deleted = dict([(k, start[k]) for k in start_keys.difference(end_keys)])
    created = dict([(k, end[k]) for k in end_keys.difference(start_keys)])
    updated = {}
    for k in start_keys.intersection(end_keys):
        if (start[k].size != end[k].size):
            updated[k] = end[k]
    return dict(deleted=deleted, created=created, updated=updated)


def assert_all_changes(start_state, end_state, expected_changes):
    """
    Fails if anything changed that isn't listed in the
    expected_changes.

    start_state is either a dict mapping paths to
    scripttest.[FoundFile|FoundDir] objects or a TestPipResult whose
    files_before we'll test.  end_state is either a similar dict or a
    TestPipResult whose files_after we'll test.

    Note: listing a directory means anything below
    that directory can be expected to have changed.
    """
    __tracebackhide__ = True

    start_files = start_state
    end_files = end_state
    if isinstance(start_state, TestPipResult):
        start_files = start_state.files_before
    if isinstance(end_state, TestPipResult):
        end_files = end_state.files_after

    diff = diff_states(start_files, end_files, ignore=expected_changes)
    if list(diff.values()) != [{}, {}, {}]:
        raise TestFailure('Unexpected changes:\n' + '\n'.join(
            [k + ': ' + ', '.join(v.keys()) for k, v in diff.items()]))

    # Don't throw away this potentially useful information
    return diff


def _create_test_package_with_subdirectory(script, subdirectory):
    script.scratch_path.join("version_pkg").mkdir()
    version_pkg_path = script.scratch_path / 'version_pkg'
    version_pkg_path.join("version_pkg.py").write(textwrap.dedent("""
                                def main():
                                    print('0.1')
                                """))
    version_pkg_path.join("setup.py").write(
        textwrap.dedent("""
    from setuptools import setup, find_packages
    setup(name='version_pkg',
          version='0.1',
          packages=find_packages(),
          py_modules=['version_pkg'],
          entry_points=dict(console_scripts=['version_pkg=version_pkg:main']))
        """))

    subdirectory_path = version_pkg_path.join(subdirectory)
    subdirectory_path.mkdir()
    subdirectory_path.join('version_subpkg.py').write(textwrap.dedent("""
                                def main():
                                    print('0.1')
                                """))

    subdirectory_path.join('setup.py').write(
        textwrap.dedent("""
from setuptools import setup, find_packages
setup(name='version_subpkg',
      version='0.1',
      packages=find_packages(),
      py_modules=['version_subpkg'],
      entry_points=dict(console_scripts=['version_pkg=version_subpkg:main']))
        """))

    script.run('git', 'init', cwd=version_pkg_path)
    script.run('git', 'add', '.', cwd=version_pkg_path)
    script.run(
        'git', 'commit', '-q',
        '--author', 'pip <pypa-dev@googlegroups.com>',
        '-am', 'initial version', cwd=version_pkg_path
    )

    return version_pkg_path


def _create_test_package(script):
    script.scratch_path.join("version_pkg").mkdir()
    version_pkg_path = script.scratch_path / 'version_pkg'
    version_pkg_path.join("version_pkg.py").write(textwrap.dedent("""
        def main():
            print('0.1')
    """))
    version_pkg_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup, find_packages
        setup(
            name='version_pkg',
            version='0.1',
            packages=find_packages(),
            py_modules=['version_pkg'],
            entry_points=dict(console_scripts=['version_pkg=version_pkg:main'])
        )
    """))
    script.run('git', 'init', cwd=version_pkg_path)
    script.run('git', 'add', '.', cwd=version_pkg_path)
    script.run(
        'git', 'commit', '-q',
        '--author', 'pip <pypa-dev@googlegroups.com>',
        '-am', 'initial version', cwd=version_pkg_path,
    )
    return version_pkg_path


def _change_test_package_version(script, version_pkg_path):
    version_pkg_path.join("version_pkg.py").write(textwrap.dedent('''\
        def main():
            print("some different version")'''))
    script.run(
        'git', 'clean', '-qfdx',
        cwd=version_pkg_path,
        expect_stderr=True,
    )
    script.run(
        'git', 'commit', '-q',
        '--author', 'pip <pypa-dev@googlegroups.com>',
        '-am', 'messed version',
        cwd=version_pkg_path,
        expect_stderr=True,
    )


def assert_raises_regexp(exception, reg, run, *args, **kwargs):
    """Like assertRaisesRegexp in unittest"""
    __tracebackhide__ = True

    try:
        run(*args, **kwargs)
        assert False, "%s should have been thrown" % exception
    except Exception:
        e = sys.exc_info()[1]
        p = re.compile(reg)
        assert p.search(str(e)), str(e)
