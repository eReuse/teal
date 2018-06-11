from setuptools import find_packages, setup

setup(
    name="teal",
    version='0.2.0a1',
    packages=find_packages(),
    url='https://github.com/bustawin/teal',
    license='BSD',
    author='Xavier Bustamante Talavera',
    author_email='xavier@bustawin.com',
    description='RESTful Flask for big applications.',
    install_requires=[
        'anytree',
        'apispec',
        'boltons',
        'ereuse-utils',
        'ereuse-utils[naming]',
        'ereuse-utils[test]',
        'flasgger',
        'flask>=1.0',
        'flask-sqlalchemy',
        'marshmallow-jsonschema',
        'marshmallow==3.0.0b9',
        'webargs'
    ],
    tests_requires=[
        'pytest',
        'pytest-datadir'
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
