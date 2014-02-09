.. _`Installation`:

Installation
============

Python & OS Support
-------------------

pip works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3, 3.4 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.


.. _`get-pip`:

Install or Upgrade pip
----------------------

To install pip, securely download `get-pip.py
<https://raw.github.com/pypa/pip/master/contrib/get-pip.py>`_. [1]_

Then run the following (which may require administrator access):

::

 $ python get-pip.py

.. note::

    Beginning with v1.5.1, pip does not require `setuptools`_ prior to running
    `get-pip.py`. Additionally, if `setuptools`_ (or `distribute`_) is not
    already installed, `get-pip.py` will install `setuptools`_ for you.


Using Package Managers
----------------------

On Linux, pip will generally be available for the system install of python using
the system package manager, although often the latest version will be
unavailable.

On Debian and Ubuntu::

   $ sudo apt-get install python-pip

On Fedora::

   $ sudo yum install python-pip


.. [1] "Secure" in this context means using a modern browser or a
       tool like `curl` that verifies SSL certificates when downloading from
       https URLs.

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute


Upgrading from distribute to setuptools
---------------------------------------

`distribute`_ has now been merged into `setuptools`_, and it is recommended to upgrade to setuptools when possible.

To upgrade from `distribute`_ to `setuptools`_ using pip, run::

  pip install --upgrade setuptools

"ImportError: No module named setuptools"
+++++++++++++++++++++++++++++++++++++++++

Although using the upgrade command above works in isolation, it's possible to get
"ImportError: No module named setuptools" when using pip<1.4 to upgrade a
package that depends on setuptools or distribute.

e.g. when running a command like this:  `pip install --upgrade pyramid`

Solution
~~~~~~~~

To prevent the problem in *new* environments (that aren't broken yet):

* Option 1:

 * *First* run `pip install -U setuptools`,
 * *Then* run the command to upgrade your package (e.g. `pip install --upgrade pyramid`)

* Option 2:

 * Upgrade pip using :ref:`get-pip <get-pip>`
 * *Then* run the command to upgrade your package (e.g. `pip install --upgrade pyramid`)

To fix the problem once it's occurred, you'll need to manually install the new
setuptools, then rerun the upgrade that failed.

1. Download `ez_setup.py` (https://bitbucket.org/pypa/setuptools/downloads/ez_setup.py)
2. Run `python ez_setup.py`
3. Then rerun your upgrade (e.g. `pip install --upgrade pyramid`)


Cause
~~~~~

distribute-0.7.3 is just an empty wrapper that only serves to require the new
setuptools (setuptools>=0.7) so that it will be installed. (If you don't know
yet, the "new setuptools" is a merge of distribute and setuptools back into one
project).

distribute-0.7.3 does its job well, when the upgrade is done in isolation.
E.g. if you're currently on distribute-0.6.X, then running `pip install -U
setuptools` works fine to upgrade you to setuptools>=0.7.

The problem occurs when:

1. you are currently using an older distribute (i.e. 0.6.X)
2. and you try to use pip to upgrade a package that *depends* on setuptools or
   distribute.

As part of the upgrade process, pip builds an install list that ends up
including distribute-0.7.3 and setuptools>=0.7 , but they can end up being
separated by other dependencies in the list, so what can happen is this:

1.  pip uninstalls the existing distribute
2.  pip installs distribute-0.7.3 (which has no importable setuptools, that pip
    *needs* internally to function)
3.  pip moves on to install another dependency (before setuptools>=0.7) and is
    unable to proceed without the setuptools package

Note that pip v1.4 has fixes to prevent this.  distribute-0.7.3 (or
setuptools>=0.7) by themselves cannot prevent this kind of problem.

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute
.. _PyPI: https://pypi.python.org
