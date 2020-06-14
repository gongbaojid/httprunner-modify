import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="httprunner-modified", # Replace with your own username
    version="3.0.9.2",
    author="gongbaojiding",
    author_email="gongbao_jiding@163.com",
    description="httprunner addition files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gongbaojid/httprunner-modify",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)