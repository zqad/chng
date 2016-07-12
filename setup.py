from distutils.core import setup

setup(
    name='chng',
    version='0.1',
    packages=['chng'],
    scripts=['bin/chng'],
    install_requires=['requests', 'requests-cache', 'unshortenit'],
    license='AGPL',
    url='https://github.com/zqad/chng',
    author='Jonas Eriksson',
    long_description=open('README.md').read(),
)
