from setuptools import find_packages, setup

with open("README.md", "r+") as f:
    readme = f.read()

setup(
    name="fastbot",
    version="1.0.0",
    description="A Lightweight BOT Framework",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Oi",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ],
    install_requires=["fastapi", "ujson", "uvicorn", "websockets"],
)
