"""Base Command class, and related routines"""

import os
import sys
import tempfile
import traceback
import time
import optparse

from pip import cmdoptions
from pip.log import logger
from pip.download import PipSession
from pip.exceptions import (BadCommand, InstallationError, UninstallationError,
                            CommandError, PreviousBuildDirError)
from pip.backwardcompat import StringIO
from pip.baseparser import ConfigOptionParser, UpdatingDefaultsHelpFormatter
from pip.status_codes import (SUCCESS, ERROR, UNKNOWN_ERROR, VIRTUALENV_NOT_FOUND,
                              PREVIOUS_BUILD_DIR_ERROR)
from pip.util import get_prog


__all__ = ['Command']


class Command(object):
    name = None
    usage = None
    hidden = False

    def __init__(self):
        parser_kw = {
            'usage': self.usage,
            'prog': '%s %s' % (get_prog(), self.name),
            'formatter': UpdatingDefaultsHelpFormatter(),
            'add_help_option': False,
            'name': self.name,
            'description': self.__doc__,
        }

        self.parser = ConfigOptionParser(**parser_kw)

        # Commands should add options to this option group
        optgroup_name = '%s Options' % self.name.capitalize()
        self.cmd_opts = optparse.OptionGroup(self.parser, optgroup_name)

        # Add the general options
        gen_opts = cmdoptions.make_option_group(cmdoptions.general_group, self.parser)
        self.parser.add_option_group(gen_opts)

    def _build_session(self, options):
        session = PipSession()

        # Handle custom ca-bundles from the user
        if options.cert:
            session.verify = options.cert

        # Handle timeouts
        if options.timeout:
            session.timeout = options.timeout

        # Handle configured proxies
        if options.proxy:
            session.proxies = {
                "http": options.proxy,
                "https": options.proxy,
            }

        # Determine if we can prompt the user for authentication or not
        session.auth.prompting = not options.no_input

        return session

    def setup_logging(self):
        pass

    def parse_args(self, args):
        # factored out for testability
        return self.parser.parse_args(args)

    def main(self, args):
        options, args = self.parse_args(args)

        # console level
        if options.level:
            level = getattr(logger, options.level)
        else:
            default_level = logger.level_from_name(logger.DEFAULT_LEVEL_NAME)
            level_index = logger.levels.index(default_level)
            level_index -= options.verbose
            level_index += options.quiet
            level = logger.level_for_integer(level_index)

        # log level
        log_level = logger.level_from_name(options.log_level or logger.DEFAULT_LOG_LEVEL_NAME)

        # log mode
        log_mode = 'w'
        if options.log_append:
            log_mode = 'a'

        log_fp = open_logfile(options.log_file, log_mode)
        # TODO: log consumer needs to enforce timestamps/levels
        logger.add_consumers(
            (level, sys.stdout),
            (log_level, log_fp)
        )

        self.setup_logging()

        #TODO: try to get these passing down from the command?
        #      without resorting to os.environ to hold these.

        if options.no_input:
            os.environ['PIP_NO_INPUT'] = '1'

        if options.exists_action:
            os.environ['PIP_EXISTS_ACTION'] = ' '.join(options.exists_action)

        if options.require_venv:
            # If a venv is required check if it can really be found
            if not os.environ.get('VIRTUAL_ENV'):
                logger.fatal('Could not find an activated virtualenv (required).')
                sys.exit(VIRTUALENV_NOT_FOUND)


        exit = SUCCESS
        try:
            status = self.run(options, args)
            # FIXME: all commands should return an exit status
            # and when it is done, isinstance is not needed anymore
            if isinstance(status, int):
                exit = status
        except PreviousBuildDirError:
            e = sys.exc_info()[1]
            logger.fatal(str(e))
            logger.info('Exception information:\n%s' % format_exc())
            exit = PREVIOUS_BUILD_DIR_ERROR
        except (InstallationError, UninstallationError):
            e = sys.exc_info()[1]
            logger.fatal(str(e))
            logger.info('Exception information:\n%s' % format_exc())
            exit = ERROR
        except BadCommand:
            e = sys.exc_info()[1]
            logger.fatal(str(e))
            logger.info('Exception information:\n%s' % format_exc())
            exit = ERROR
        except CommandError:
            e = sys.exc_info()[1]
            logger.fatal('ERROR: %s' % e)
            logger.info('Exception information:\n%s' % format_exc())
            exit = ERROR
        except KeyboardInterrupt:
            logger.fatal('Operation cancelled by user')
            logger.info('Exception information:\n%s' % format_exc())
            exit = ERROR
        except:
            logger.fatal('Exception:\n%s' % format_exc())
            exit = UNKNOWN_ERROR

        log_fp.close()
        return exit


def format_exc(exc_info=None):
    if exc_info is None:
        exc_info = sys.exc_info()
    out = StringIO()
    traceback.print_exception(*exc_info, **dict(file=out))
    return out.getvalue()


def open_logfile(filename, mode):
    """Open the log file; Write separator if mode=='a'"""
    filename = os.path.expanduser(filename)
    filename = os.path.abspath(filename)
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    exists = os.path.exists(filename)
    log_fp = open(filename, mode)
    if exists and mode == 'a':
        log_fp.write('%s\n' % ('-' * 60))
    return log_fp
