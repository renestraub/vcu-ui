import setuptools
from vcuui._version import __version__ as version


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="vcu-ui",
    version=version,
    author="Rene Straub",
    author_email="straub@see5.com",
    description="NG800/VCU Pro Web UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/renestraub/vcu-ui",
    packages=setuptools.find_packages(exclude=("tests",)),
    classifiers=[
        'Programming Language :: Python :: 3.7',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        'tornado',
        'requests',
        'ping3',
        'ubxlib>=0.3.6'
    ],
    include_package_data=True,  # Use MANIFEST.in to add *.html, *.css files
    entry_points={
        'console_scripts': [
            'vcu-ui-start = vcuui.server:run_server'
        ]
    },
)
