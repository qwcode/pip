# coding: utf-8
import os
from pip.backwardcompat import urllib, get_http_message_param
from pip.index import (package_to_requirement, HTMLPage, get_mirrors,
        DEFAULT_MIRROR_HOSTNAME, PackageFinder, Link, InfLink, PageGetter,
        PageCache)
from tests.lib import (reset_env, run_pip, pyversion, path_to_url,
                       assert_raises_regexp, find_links, tests_data)
from string import ascii_lowercase
from mock import patch, Mock
import threading
import time


def test_package_name_should_be_converted_to_requirement():
    """
    Test that it translates a name like Foo-1.2 to Foo==1.3
    """
    assert package_to_requirement('Foo-1.2') == 'Foo==1.2'
    assert package_to_requirement('Foo-dev') == 'Foo==dev'
    assert package_to_requirement('Foo') == 'Foo'


def test_html_page_should_be_able_to_scrap_rel_links():
    """
    Test scraping page looking for url in href
    """
    page = HTMLPage("""
        <!-- The <th> elements below are a terrible terrible hack for setuptools -->
        <li>
        <strong>Home Page:</strong>
        <!-- <th>Home Page -->
        <a href="http://supervisord.org/">http://supervisord.org/</a>
        </li>""", "supervisor")

    links = list(page.scraped_rel_links())
    assert len(links) == 1
    assert links[0].url == 'http://supervisord.org/'

@patch('socket.gethostbyname_ex')
def test_get_mirrors(mock_gethostbyname_ex):
    # Test when the expected result comes back
    # from socket.gethostbyname_ex
    mock_gethostbyname_ex.return_value = ('g.pypi.python.org', [DEFAULT_MIRROR_HOSTNAME], ['129.21.171.98'])
    mirrors = get_mirrors()
    # Expect [a-g].pypi.python.org, since last mirror
    # is returned as g.pypi.python.org
    assert len(mirrors) == 7
    for c in "abcdefg":
        assert c + ".pypi.python.org" in mirrors

@patch('socket.gethostbyname_ex')
def test_get_mirrors_no_cname(mock_gethostbyname_ex):
    # Test when the UNexpected result comes back
    # from socket.gethostbyname_ex
    # (seeing this in Japan and was resulting in 216k
    #  invalid mirrors and a hot CPU)
    mock_gethostbyname_ex.return_value = (DEFAULT_MIRROR_HOSTNAME, [DEFAULT_MIRROR_HOSTNAME], ['129.21.171.98'])
    mirrors = get_mirrors()
    # Falls back to [a-z].pypi.python.org
    assert len(mirrors) == 26
    for c in ascii_lowercase:
        assert c + ".pypi.python.org" in mirrors


def test_sort_locations_file_find_link():
    """
    Test that a file:// find-link dir gets listdir run
    """
    finder = PackageFinder([find_links], [])
    files, urls = finder._sort_locations([find_links])
    assert files and not urls, "files and not urls should have been found at find-links url: %s" % find_links


def test_sort_locations_file_not_find_link():
    """
    Test that a file:// url dir that's not a find-link, doesn't get a listdir run
    """
    index_url = path_to_url(os.path.join(tests_data, 'indexes', 'empty_with_pkg'))
    finder = PackageFinder([], [])
    files, urls = finder._sort_locations([index_url])
    assert urls and not files, "urls, but not files should have been found"


def test_inflink_greater():
    """Test InfLink compares greater."""
    assert InfLink > Link("some link")


def test_mirror_url_formats():
    """
    Test various mirror formats get transformed properly
    """
    formats = [
        'some_mirror',
        'some_mirror/',
        'some_mirror/simple',
        'some_mirror/simple/'
        ]
    for scheme in ['http://', 'https://', 'file://', '']:
        result = (scheme or 'http://') + 'some_mirror/simple/'
        scheme_formats = ['%s%s' % (scheme, format) for format in formats]
        finder = PackageFinder([], [])
        urls = finder._get_mirror_urls(mirrors=scheme_formats, main_mirror_url=None)
        for url in urls:
            assert url == result, str([url, result])


def test_non_html_page_should_not_be_scraped():
    """
    Test that a url whose content-type is not text/html
    will never be scraped as an html page.
    """
    # Content-type is already set
    # no need to monkeypatch on response headers
    url = path_to_url(os.path.join(tests_data, 'indexes', 'empty_with_pkg', 'simple-1.0.tar.gz'))
    page = HTMLPage.get_page(Link(url), None, cache=None)
    assert page == None


@patch("pip.index.urlopen")
@patch("pip.util.get_http_message_param")
def test_page_charset_encoded(get_http_message_param_mock, urlopen_mock):
    """
    Test that pages that have charset specified in content-type are decoded
    """
    if pyversion >= '3':
        utf16_content_before = 'á'
    else:
        utf16_content_before = 'á'.decode('utf-8')
    utf16_content = utf16_content_before.encode('utf-16')
    fake_url = 'http://example.com'
    mocked_response = Mock()
    mocked_response.read = lambda: utf16_content
    mocked_response.geturl = lambda: fake_url
    mocked_response.info = lambda: {'Content-Type': 'text/html; charset=utf-16'}

    urlopen_mock.return_value = mocked_response
    get_http_message_param_mock.return_value = 'utf-16' # easier to mock charset here

    page = HTMLPage.get_page(Link(fake_url), None, cache=None)

    assert page.content == utf16_content_before


@patch("pip.index.urlopen")
@patch("pip.util.get_http_message_param")
def test_get_page_fallbacks_to_utf8_if_no_charset_is_given(get_http_message_param_mock, urlopen_mock):
    """
    Test that pages that have no charset specified in content-type are decoded with utf-8
    """
    if pyversion >= '3':
        utf8_content_before = 'á'
    else:
        utf8_content_before = 'á'.decode('utf-8')
    utf8_content = utf8_content_before.encode('latin-1')

    fake_url = 'http://example.com'
    mocked_response = Mock()
    mocked_response.read = lambda: utf8_content
    mocked_response.geturl = lambda: fake_url
    mocked_response.info = lambda: {'Content-Type': 'text/html'}

    urlopen_mock.return_value = mocked_response
    get_http_message_param_mock.return_value = None # no charset given

    page = HTMLPage.get_page(Link(fake_url), None, cache=None)

    assert page.content == utf8_content_before

@patch("pip.index.urlopen")
@patch("pip.util.get_http_message_param")
def test_get_page_fallbacks_to_latin1_if_utf8_fails(get_http_message_param_mock, urlopen_mock):
    """
    Test that pages that have no charset specified in content-type are decoded with utf-8
    """
    if pyversion >= '3':
        latin1_content_before = 'á'
    else:
        latin1_content_before = 'á'.decode('utf-8')
    latin1_content = latin1_content_before.encode('latin-1')

    fake_url = 'http://example.com'
    mocked_response = Mock()
    mocked_response.read = lambda: latin1_content
    mocked_response.geturl = lambda: fake_url
    mocked_response.info = lambda: {'Content-Type': 'text/html'}

    urlopen_mock.return_value = mocked_response
    get_http_message_param_mock.return_value = None # no charset given

    page = HTMLPage.get_page(Link(fake_url), None, cache=None)

    assert page.content == latin1_content_before

def test_threaded_page_getter():
    """
    Test that page getting is done in a threaded fashion
    """
    thread_ids = set()

    def mocked_get_page(self, link, req):
        time.sleep(.1)
        this_thread = threading.current_thread()
        thread_ids.add(this_thread.ident)

    with patch.object(PageGetter, '_get_page', mocked_get_page):
        dummy_cache = PageCache()
        getter = PageGetter(dummy_cache)
        locations = ['http://foo%s.com' % i for i in range(15)]
        result = getter.get_pages(locations, 'some-req')
        # check that the page queue was emptied
        assert getter._pending_queue.empty()

    assert len(thread_ids) == 10


def test_thread_reraise():
    """
    Test threaded page getter reraises unhandled exceptions in main thread
    """
    def mocked_get_page(self, link, req):
        raise ValueError("ThreadError")

    with patch.object(PageGetter, '_get_page', mocked_get_page):
        dummy_cache = PageCache()
        getter = PageGetter(dummy_cache)
        locations = ['http://foo%s.com' % i for i in range(15)]
        assert_raises_regexp(ValueError, 'ThreadError', getter.get_pages,
                locations, 'some-req')


def test_seen_pages():
    """
    Tests that PageGetter manages seen pages
    """
    gotten_pages = []

    def mocked_get_page(self, link, req):
        gotten_pages.append(link)
        return HTMLPage('', link)

    with patch.object(PageGetter, '_get_page', mocked_get_page):
        dummy_cache = PageCache()
        getter = PageGetter(dummy_cache)
        locations = ['http://foo%s.com' % i for i in range(5)]
        result = getter.get_pages(locations, 'some-req')
        ct_pages_gotten = len(gotten_pages)
        assert len(result) == ct_pages_gotten
        # put seen locations into the work queue
        for l in locations:
            getter._pending_queue.put(l)
        getter._pending_queue.join()
        # check that the queue was in fact drained again
        assert getter._pending_queue.empty()
        # check that no seen pages were re-fetched
        assert ct_pages_gotten == len(gotten_pages)
        # confirm no pages were added to done list
        assert len(getter._pages_done) == ct_pages_gotten

