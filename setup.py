from setuptools import setup, find_packages

setup(
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    packages=find_packages(where="src"),
    package_dir={"": "src"})
