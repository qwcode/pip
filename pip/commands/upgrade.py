## TODO: ignore editables

from __future__ import absolute_import

import logging
import os
import tempfile
import shutil
import warnings

from pip.req import InstallRequirement, RequirementSet, parse_requirements
from pip.locations import virtualenv_no_global, distutils_scheme, src_prefix
from pip.basecommand import Command
from pip.index import PackageFinder
from pip.exceptions import (
    InstallationError, CommandError, PreviousBuildDirError,
)
from pip import cmdoptions
from pip.utils.deprecation import RemovedInPip7Warning, RemovedInPip8Warning


logger = logging.getLogger(__name__)


class UpgradeCommand(Command):
    """
    Upgrade installed packages.
    """
    name = 'upgrade'

    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
    """

    summary = 'Upgrade installed packages.'

    def __init__(self, *args, **kw):
        super(UpgradeCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '--eager',
            action='store_true',
            help='Upgrade dependencies even if already satisfied.')

        cmd_opts.add_option(cmdoptions.requirements.make())
        cmd_opts.add_option(cmdoptions.build_dir.make())

        cmd_opts.add_option(
            '--force-reinstall',
            dest='force_reinstall',
            action='store_true',
            help='When upgrading, reinstall all packages even if they are '
                 'already up-to-date.')

        cmd_opts.add_option(
            '-I', '--ignore-installed',
            dest='ignore_installed',
            action='store_true',
            help='Ignore the installed packages (reinstalling instead).')

        cmd_opts.add_option(cmdoptions.no_deps.make())

        cmd_opts.add_option(cmdoptions.install_options.make())
        cmd_opts.add_option(cmdoptions.global_options.make())

        cmd_opts.add_option(
            "--compile",
            action="store_true",
            dest="compile",
            default=True,
            help="Compile py files to pyc",
        )

        cmd_opts.add_option(
            "--no-compile",
            action="store_false",
            dest="compile",
            help="Do not compile py files to pyc",
        )

        cmd_opts.add_option(cmdoptions.use_wheel.make())
        cmd_opts.add_option(cmdoptions.no_use_wheel.make())

        cmd_opts.add_option(
            '--pre',
            action='store_true',
            default=False,
            help="Include pre-release and development versions. By default, "
                 "pip only finds stable versions.")

        cmd_opts.add_option(cmdoptions.no_clean.make())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def _build_package_finder(self, options, index_urls, session):
        """
        Create a package finder appropriate to this install command.
        This method is meant to be overridden by subclasses, not
        called directly.
        """
        return PackageFinder(
            find_links=options.find_links,
            index_urls=index_urls,
            use_wheel=options.use_wheel,
            allow_external=options.allow_external,
            allow_unverified=options.allow_unverified,
            allow_all_external=options.allow_all_external,
            allow_all_prereleases=options.pre,
            process_dependency_links=options.process_dependency_links,
            session=session,
        )

    def run(self, options, args):

        options.build_dir = os.path.abspath(options.build_dir)
        install_options = options.install_options or []
        temp_target_dir = None
        global_options = options.global_options or []
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.info('Ignoring indexes: %s', ','.join(index_urls))
            index_urls = []

        if options.use_mirrors:
            warnings.warn(
                "--use-mirrors has been deprecated and will be removed in the "
                "future. Explicit uses of --index-url and/or --extra-index-url"
                " is suggested.",
                RemovedInPip7Warning,
            )

        if options.mirrors:
            warnings.warn(
                "--mirrors has been deprecated and will be removed in the "
                "future. Explicit uses of --index-url and/or --extra-index-url"
                " is suggested.",
                RemovedInPip7Warning,
            )
            index_urls += options.mirrors

        with self._build_session(options) as session:

            finder = self._build_package_finder(options, index_urls, session)

            requirement_set = RequirementSet(
                build_dir=options.build_dir,
                src_dir=src_prefix,
                download_dir=None,
                upgrade_eager=options.eager,
                ignore_installed=options.ignore_installed,
                ignore_dependencies=options.ignore_dependencies,
                force_reinstall=options.force_reinstall,
                session=session,
                pycompile=options.compile,
            )
            for name in args:
                requirement_set.add_requirement(
                    InstallRequirement.from_line(name, None, upgrade=True))
            for filename in options.requirements:
                for req in parse_requirements(
                        filename,
                        finder=finder, options=options, session=session,
                        upgrade=True):
                    requirement_set.add_requirement(req)
            if not requirement_set.has_requirements:
                opts = {'name': self.name}
                if options.find_links:
                    msg = ('You must give at least one requirement to %(name)s'
                           ' (maybe you meant "pip %(name)s %(links)s"?)' %
                           dict(opts, links=' '.join(options.find_links)))
                else:
                    msg = ('You must give at least one requirement '
                           'to %(name)s (see "pip help %(name)s")' % opts)
                logger.warning(msg)
                return

            try:
                requirement_set.prepare_files(finder)
                requirement_set.install(
                    install_options,
                    global_options
                )
                installed = ' '.join([
                    req.name for req in
                    requirement_set.successfully_installed
                ])
                if installed:
                    logger.info('Successfully installed %s', installed)
            except PreviousBuildDirError:
                options.no_clean = True
                raise
            finally:
                # Clean up
                if not options.no_clean:
                    requirement_set.cleanup_files()

            return requirement_set
