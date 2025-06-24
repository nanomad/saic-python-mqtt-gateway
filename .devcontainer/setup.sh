#!/usr/bin/env bash
set -ex


# install system dependencies
pip install poetry


# install python dependencies
poetry install --no-interaction


# fix dubious ownership warning
git config --global --add safe.directory $(pwd)

# install pre-commit git hooks

#pre-commit install
#pre-commit install --hook-type commit-msg
