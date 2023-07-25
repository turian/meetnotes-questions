from setuptools import find_packages, setup

setup(
    name="meetnotes_questions",
    version="0.1.10",
    description="GPT plugin for asking intelligent questions on live meeting notes",
    author="Joseph Turian",
    author_email="lastname@gmail.com",
    url="https://github.com/pypa/meetnotes-questions",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv",
        "watchdog",
        "tiktoken",
        "openai",
        "asyncio",
    ],
    entry_points={
        "console_scripts": [
            "meetnotes_questions=meetnotes_questions.main:main",
        ],
    },
)
