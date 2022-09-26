from setuptools import find_packages, setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='teal',
    version='0.2.0a40',
    packages=find_packages(),
    url='https://github.com/ereuse/teal',
    license='BSD',
    author='Xavier Bustamante Talavera',
    author_email='xavier@bustawin.com',
    description='RESTful Flask for big applications.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'anytree',
        'apispec',
        'apispec-webframeworks',
        'boltons',
        'ereuse-utils[naming, test, session, cli]>=0.4.0b21',
        'flask>=1.0',
        'flask-sqlalchemy>=2.5.1',
        'sqlalchemy-utils[password, color, phone]',
        'marshmallow>=3.0.0',
        'marshmallow-enum',
        'webargs',
        'flask-cors',
        'click-spinner',
        'Werkzeug==2.0.3',  # https://stackoverflow.com/a/73476925/1538221
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
