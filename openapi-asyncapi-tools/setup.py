from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

setup(
    name='sep-tools',
    version='0.0.4',
    description='',
    long_description=readme,
    author='Solace SE',
    url='https://github.com/solacese/openapi-asyncapi-tools',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'click',
        'PyYAML',
        'requests',
    ],
    entry_points={
        "console_scripts": [
            "sep=sep_tools.cmd:cli",
        ]
    },
)
