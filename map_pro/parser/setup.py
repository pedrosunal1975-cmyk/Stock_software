"""
XBRL Parser package setup.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="xbrl-parser",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Production-grade XBRL parser with component reusability",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/xbrl-parser",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "mypy>=1.0",
            "black>=23.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "xbrl-parse=xbrl_parser.cli:main",
        ],
    },
)
