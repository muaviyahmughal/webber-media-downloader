from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="webber-downloader",
    version="2.1.1",
    author="Sufyan Mughal",
    author_email="sufyanmughal522@gmail.com",
    description="A powerful tool to download images, vectors, and videos from websites",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sufyanmughal/webber-website-downloader",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "webber=webber.webber_downloader:main",
        ],
    },
)
