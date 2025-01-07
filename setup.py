from setuptools import setup, find_packages

setup(
    name="ampf",
    version="0.1.8",
    packages=find_packages(),
    install_requires=["fastapi", "pydantic"],
    author="Marcin Leliwa",
    author_email="marcin.leliwa@gmail.com",
    description="Angular & Material & Python & FastAPI",
    long_description="#AMPF",
    long_description_content_type="text/markdown",
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
