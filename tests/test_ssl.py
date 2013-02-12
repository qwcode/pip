
import sys
import os
from mock import Mock, patch
from pip.download import urlopen, VerifiedHTTPSHandler
from tests.test_pip import assert_raises_regexp, here, reset_env, run_pip
from nose import SkipTest
from nose.tools import assert_raises
from pip.backwardcompat import urllib2, ssl, URLError
from pip.exceptions import PipError

pypi_https = 'https://pypi.python.org/simple/'
pypi_http = 'http://pypi.python.org/simple/'

def find_file(filename, std_dirs, paths):
    """Searches for the directory where a given file is located,
    and returns a possibly-empty list of additional directories, or None
    if the file couldn't be found at all.

    'filename' is the name of a file, such as readline.h or libcrypto.a.
    'std_dirs' is the list of standard system directories; if the
        file is found in one of them, no additional directives are needed.
    'paths' is a list of additional locations to check; if the file is
        found in one of them, the resulting list will contain the directory.
    """

    # Check the standard locations
    for dir in std_dirs:
        f = os.path.join(dir, filename)
        print 'looking for', f
        if os.path.exists(f): return []

    # Check the additional directories
    for dir in paths:
        f = os.path.join(dir, filename)
        print 'looking for', f
        if os.path.exists(f):
            return [dir]

    # Not found anywhere
    return None

def find_library_file(compiler, libname, std_dirs, paths):
    result = compiler.find_library_file(std_dirs + paths, libname)
    if result is None:
        print "no compiler"
        return None

    # Check whether the found file is in one of the standard directories
    dirname = os.path.dirname(result)
    print dirname
    for p in std_dirs:
        # Ensure path doesn't end with path separator
        p = p.rstrip(os.sep)
        if p == dirname:
            print "return"
            return [ ]

    # Otherwise, it must have been in one of the additional directories,
    # so we have to figure out which one.
    for p in paths:
        # Ensure path doesn't end with path separator
        p = p.rstrip(os.sep)
        if p == dirname:
            return [p]
    else:
        assert False, "Internal error: Path not found in std_dirs or paths"


class Tests_py25:
    """py25 tests"""

    def setup(self):
        if sys.version_info >= (2, 6):
            raise SkipTest()

    def teardown(self):
        #make sure this is set back for other tests
        os.environ['PIP_ALLOW_NO_SSL'] = '1'

    def test_https_fails(self):
        """
        Test py25 access https fails
        """
        os.environ['PIP_ALLOW_NO_SSL'] = ''
        assert_raises_regexp(PipError, 'ssl certified', urlopen.get_opener, scheme='https')

    def test_https_ok_with_flag(self):
        """
        Test py25 access https url ok with --allow-no-ssl flag
        This doesn't mean it's doing cert verification, just accessing over https
        """
        os.environ['PIP_ALLOW_NO_SSL'] = '1'
        response = urlopen.get_opener().open(pypi_https)
        assert response.code == 200, str(dir(response))

    def test_http_ok(self):
        """
        Test http pypi access with pip urlopener
        """
        os.environ['PIP_ALLOW_NO_SSL'] = ''
        response = urlopen.get_opener().open(pypi_http)
        assert response.code == 200, str(dir(response))

    def test_install_fails_with_no_ssl_backport(self):
        """
        Test installing w/o ssl backport fails
        """
        reset_env(allow_no_ssl=False)
        #expect error because ssl's setup.py is hard coded to install test data to global prefix
        result = run_pip('install', 'INITools', expect_error=True)
        assert "You don't have an importable ssl module" in result.stdout

    def test_install_with_ssl_backport(self):
        """
        Test installing with ssl backport
        """

        # Detect SSL support for the socket module (via _ssl)
        from distutils.ccompiler import new_compiler

        compiler = new_compiler()
        inc_dirs = compiler.include_dirs + ['/usr/include']

        search_for_ssl_incs_in = [
                              '/usr/local/ssl/include',
                              '/usr/contrib/ssl/include/'
                             ]
        ssl_incs = find_file('openssl/ssl.h', inc_dirs,
                             search_for_ssl_incs_in
                             )
        if ssl_incs is not None:
            krb5_h = find_file('krb5.h', inc_dirs,
                               ['/usr/kerberos/include'])
            if krb5_h:
                ssl_incs += krb5_h

        ssl_libs = find_library_file(compiler, 'ssl',
                                     ['/usr/lib'],
                                     ['/usr/local/lib',
                                      '/usr/local/ssl/lib',
                                      '/usr/contrib/ssl/lib/'
                                     ] )

        assert ssl_libs


        # # allow_no_ssl=True so we can install ssl first
        # env = reset_env(allow_no_ssl=True)
        # #expect error because ssl's setup.py is hard coded to install test data to global prefix
        # result = run_pip('install', 'ssl', expect_error=True)
        # assert os.path.isfile('/usr/include/krb5.h')
        # assert False, result.stdout

        # #set it back to false
        # env.environ['PIP_ALLOW_NO_SSL'] = ''
        # result = run_pip('install', 'INITools', expect_error=True)
        # assert False, result.stdout
        # result.assert_installed('initools', editable=False)


class Tests_not_py25:
    """non py25 tests"""

    def setup(self):
        if sys.version_info < (2, 6):
            raise SkipTest()

    def teardown(self):
        os.environ['PIP_CERT_PATH'] = ''


    def test_https_ok(self):
        """
        Test https pypi access with pip urlopener
        """
        response = urlopen.get_opener(scheme='https').open(pypi_https)
        assert response.getcode() == 200, str(dir(response))

    def test_http_ok(self):
        """
        Test http pypi access with pip urlopener
        """
        response = urlopen.get_opener().open(pypi_http)
        assert response.getcode() == 200, str(dir(response))

    def test_https_opener_director_handlers(self):
        """
        Confirm the expected handlers in our https OpenerDirector instance
        We're specifically testing it does *not* contain the default http handler
        """
        o = urlopen.get_opener(scheme='https')
        handler_types = [h.__class__ for h in o.handlers]

        assert handler_types == [
            urllib2.UnknownHandler,
            urllib2.HTTPDefaultErrorHandler,
            urllib2.HTTPRedirectHandler,
            urllib2.FTPHandler,
            urllib2.FileHandler,
            VerifiedHTTPSHandler,  #our cert check handler
            urllib2.HTTPErrorProcessor
            ], str(handler_types)

    @patch('ssl.SSLSocket.getpeercert')
    def test_fails_with_no_cert_returning(self, mock_getpeercert):
        """
        Test get ValueError if pypi returns no cert.
        """
        mock_getpeercert.return_value = None
        o = urlopen.get_opener(scheme='https')
        assert_raises_regexp(ValueError, 'empty or no certificate', o.open, pypi_https)


    def test_bad_pem_fails(self):
        """
        Test ssl verification fails with bad pem file.
        Also confirms alternate --cert-path option works
        """
        bad_cert = os.path.join(here, 'packages', 'README.txt')
        os.environ['PIP_CERT_PATH'] = bad_cert
        o = urlopen.get_opener(scheme='https')
        assert_raises_regexp(URLError, '[sS][sS][lL]', o.open, pypi_https)

