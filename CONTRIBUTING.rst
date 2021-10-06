.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/hbldh/bleak/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

bleak could always use more documentation, whether as part of the
official bleak docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at
https://github.com/hbldh/bleak/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `bleak` for local development.

1. Fork the `bleak` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/bleak.git

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ mkvirtualenv bleak
    $ cd bleak/
    $ python setup.py develop

4. Create a branch for local development, originating from the `develop` branch::

    $ git checkout -b name-of-your-bugfix-or-feature develop

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass flake8 and the tests, including testing other Python versions with tox::

    $ flake8 bleak tests
    $ python setup.py test or py.test
    $ tox

   To get flake8 and tox, just pip install them into your virtualenv.

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. If the pull request adds functionality, the docs should be updated.
2. Modify the ``CHANGELOG.rst``, describing your changes as is specified by the
   guidelines in that document.
3. The pull request should work for Python 3.7+ on the following platforms:
    - Windows 10, version 16299 (Fall Creators Update) and greater
    - Linux distributions with BlueZ >= 5.43
    - OS X / macOS >= 10.11
4. Squash all your commits on your PR branch, if the commits are not solving
   different problems and you are committing them in the same PR. In that case,
   consider making several PRs instead.
5. Feel free to add your name as a contributor to the ``AUTHORS.rst`` file!
