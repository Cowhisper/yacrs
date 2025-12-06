from setuptools import setup

setup(
    name="yacrs",  # Replace with your package name
    version="0.0.2",
    author="Cowhisper",
    author_email="niu1187203155@gmail.com",
    description="Yet Anothor Configuration and Registration System",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Cowhisper/yacrs",  # Replace with your repo URL
    packages=['yacrs'],  # Automatically find packages in the directory
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    setup_requires=['wheel']
)
