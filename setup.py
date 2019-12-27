import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="VCU Pro UI",
    version="0.0.1",
    author="Rene Straub",
    author_email="straub@see5.com",
    description="VCU Pro Basic UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/renestraub/vcu-ui",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=['bottle'],
    package_data={
        '': ['*.css', '*.tpl'],
    }
)
