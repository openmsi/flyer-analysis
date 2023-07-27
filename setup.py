""" Setup for flyer-analysis """
# imports
import setuptools

VERSION = "1.0.0"

LONG_DESCRIPTION = ""
with open("README.md", "r") as readme:
    for il, line in enumerate(readme.readlines(), start=1):
        LONG_DESCRIPTION += line

setupkwargs = dict(
    name="flyeranalysis",
    packages=setuptools.find_packages(include=["flyeranalysis*"]),
    include_package_data=True,
    version=VERSION,
    description="""Python application for detecting and analyzing flyer properties in 
                   laser shock lab high speed video frames""",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Alakarthika Ulaganathan, Maggie Eminizer",
    url="https://github.com/openmsi/flyer-analysis",
    download_url=f"https://github.com/openmsi/flyer-analysis/archive/refs/tags/v{VERSION}.tar.gz",
    license="GNU GPLv3",
    entry_points={
        "console_scripts": [
            "FlyerAnalysisStreamProcessor=flyeranalysis.flyer_analysis_stream_processor:main",
        ],
    },
    python_requires=">=3.9",
    install_requires=[
        "imageio",
        "matplotlib",
        "numpy",
        "opencv-python",
        "openmsistream>=1.5.3",
        "pandas",
        "pymssql",
        "pytest-shutil",
        "python-fmrest>=1.6.0",
        "scikit-image",
        "scipy",
        "sqlalchemy",
    ],
    extras_require={
        "dev": [
            "twine",
        ],
    },
    keywords=["data_streaming", "stream_processing", "materials", "data_science"],
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)

setupkwargs["extras_require"]["all"] = sum(setupkwargs["extras_require"].values(), [])

setuptools.setup(**setupkwargs)
