
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

        #unable to get ssl backport to install on travis.
        raise SkipTest()

        # allow_no_ssl=True so we can install ssl first
        env = reset_env(allow_no_ssl=True)
        #expect error because ssl's setup.py is hard coded to install test data to global prefix
        result = run_pip('install', 'ssl', expect_error=True)

        #set it back to false
        env.environ['PIP_ALLOW_NO_SSL'] = ''
        result = run_pip('install', 'INITools', expect_error=True)
        result.assert_installed('initools', editable=False)


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
