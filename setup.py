from setuptools import setup, find_namespace_packages

setup(
    name="proxy-finder",
    version="1.1.0",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    install_requires=[
        "requests>=2.25.1",
        "beautifulsoup4>=4.9.3",
        "rich>=10.0.0",
        "selenium>=4.0.0",
        "urllib3>=1.26.0"
    ],
    entry_points={
        'console_scripts': [
            'proxy-finder=proxy_finder.cli:main',
        ],
    },
    author="Abbaloch",
    description="A robust proxy finding and management system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires='>=3.8',
)