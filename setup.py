from setuptools import find_packages, setup

setup(
    name="git-context",
    version="1.0.0",
    description="Generate AI-friendly git repo context in one command",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/promptpolish-ai/git-context",
    author="gitcontext",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={"console_scripts": ["git-context=git_context:main"]},
)
