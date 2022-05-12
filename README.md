# edea python libary and tool

This is the edea commandline tool and kicad parser python library.


## Running the tool

To run the tool for test & development purposes either enter a venv or use poetry to run it:

```sh
# when outside the poetry environment, just run
poetry run python -m edea
# or
poetry shell
# now we're inside the venv and can run
python -m edea
```


## Running the tests

The tests should run in the venv to make sure the development tools are there:

```sh
# outside the poetry environment:
poetry run pytest
# or
poetry shell
# now we're inside the venv and can run like before, but now with test coverage
pytest --cov-report term-missing --cov=edea

# it's also possible to run a single test or a test class
pytest -k TestMetadata
```
