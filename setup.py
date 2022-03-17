import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sqlparse_helper",
    version="0.0.1",
    author="Shigetoshi Hirano",
    author_email="hirano.shigetoshi@classmethod.jp",
    description="A helper for sqlparse.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cm-hirano-shigetoshi/sqlparse-helper",
    project_urls={
        "Bug Tracker": "https://github.com/cm-hirano-shigetoshi/sqlparse-helper",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.7",
)
