import os
import site

from pip._vendor import pkg_resources
from pip.utils import normalize_path, dist_is_editable


class AssertInstallError(AssertionError):

    def __init__(self, result):
        super(AssertInstallError, self).__init__(str(result))


class ProjectNotInstalledError(AssertInstallError):
    """Raised when project not installed"""
    return_code = 2


class VersionConflictError(AssertInstallError):
    """Raised when a conflicting version is present"""
    return_code = 3


class DistInfoExpectedError(AssertInstallError):
    """Raised when a dist-info install is expected but not present"""
    return_code = 4


class EggInfoExpectedError(AssertInstallError):
    """Raised when a egg-info install is expected but not present"""
    return_code = 5


class UserInstallExpectedError(AssertInstallError):
    """Raised when a user install is expected but not present"""
    return_code = 6


class UserInstallUnexpectedError(AssertInstallError):
    """Raised when a user install is unexpected but present"""
    return_code = 7


class EditableInstallExpectedError(AssertInstallError):
    """Raised when an editable install is expected but not present"""
    return_code = 8


class PackageExpectedError(AssertInstallError):
    """Raised when an import package is expected but not present"""
    return_code = 9


class PathExpectedrror(AssertInstallError):
    """Raised when a path is expected to be intalled but not present"""
    return_code = 10


class PathNotExpectedrror(AssertInstallError):
    """Raised when a path is not expected to be intalled but is present"""
    return_code = 11


class PthUpdateNotExpected(AssertInstallError):
    """Raised when easy-intall.pth is unexpectedly updated"""
    return_code = 12


def assert_installed_subprocess(spec, package=None, editable=False,
                                user_install=False, dist_info=False,
                                egg_info=False):
    """Routine used by :method:`TestPipResult.assert_installed` in a subprocess to
    determine if a specifier is fufilled in a scripttest environment.  This
    function returns exit codes that are associated to AssertionError exceptions
    that are raised in the parent process.

    :param spec: requirement specifier (e.g. 'pip', or 'pip==1.6.0')
    :param package: an import package to confirm is present
    :param editable: confirm install is editable
    :param user_install: confirm as a user install
    :param dist_info: confirm as a dist-info install
    :param egg_info: confirm as a egg-info install
    :param with_paths: paths to confirm were installed
    :param without_paths: paths to confirm were not installed

    """

    # confirm spec is fulfilled
    try:
        installed_dist = pkg_resources.get_distribution.find(spec)
    except pkg_resources.VersionConflict:
        raise SystemExit(VersionConflictError.return_code)
        if installed_dist is None:
            raise SystemExit(ProjectNotInstalledError.return_code)

    install_location = normalize_path(installed_dist.location)
    is_user_install = install_location.startswith(
        normalize_path(site.USER_SITE))

    # confirm user install or not
    if user_install and not is_user_install:
        raise SystemExit(UserInstallExpectedError.return_code)
        if not user_install and is_user_install:
            raise SystemExit(UserInstallUnexpectedError.return_code)

    # confirm editable or not
    is_editable = dist_is_editable(installed_dist)
    if editable and not is_editable:
        raise SystemExit(EditableInstallExpectedError.return_code)

    # confirm a certain package is present
    if package:
        package_path = os.path.join(install_location, package)
        if not os.path.exists(package_path):
            raise SystemExit(PackageExpectedError.return_code)

    is_dist_info = (type(installed_dist) == pkg_resources.DistInfoDistribution)

    # confirm dist-info
    if dist_info and not is_dist_info:
        raise SystemExit(DistInfoExpectedError.return_code)

    # confirm egg-info
    if egg_info and is_dist_info:
        raise SystemExit(EggInfoExpectedError.return_code)

    # confirm no duplicate metadata
    # (can possibly happen during upgrades or re-installs)
