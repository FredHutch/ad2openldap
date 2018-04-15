from setuptools import setup

__version__ = "1.0.1.4"

CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Intended Audience :: Customer Service",
    "Intended Audience :: Developers",
    "Intended Audience :: Education",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Science/Research",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: Apache Software License",
    "Natural Language :: English",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX",
    "Operating System :: POSIX :: Linux",
    "Operating System :: POSIX :: Other",
    "Operating System :: Unix",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Unix Shell",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Systems Administration",
    "Topic :: Utilities"
]

setup(
    name='ad2openldap',
    version=__version__,
    description='ad2openldap is a lighweight Active Directory to Openldap replicator that helps replacing an IAM solution such as Centrify',
    long_description=open('README.rst', 'r').read(),
    packages=['ad2openldap'],
    #scripts=['ad2openldap/ad2openldap','ad2openldap/ad2openldap3'],
    scripts=['ad2openldap/ad2openldap3'],
    author = 'Jeff Katcher, Brian Hodges',
    author_email = 'dp@nowhere.com',
    url = 'https://github.com/FredHutch/ad2openldap',
    download_url = 'https://github.com/FredHutch/ad2openldap/tarball/%s' % __version__,
    keywords = ['ldap', 'active directory', 'IAM'], # arbitrary keywords
    classifiers = CLASSIFIERS,
    # yaml is apparently default now?
    # wheel is not default
    install_requires=[
        'ldap3',
        'wheel'
        ],
    entry_points={
        # we use console_scripts here to allow virtualenv to rewrite shebangs
        # to point to appropriate python and allow experimental python 2.X
        # support.
        'console_scripts': [
            'ad2openldap3.py=ad2openldap3.ad2openldap3:main',
        ]
    }
)
