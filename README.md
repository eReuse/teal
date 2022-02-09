# Teal

![teal-logo](docs/teal-logo.svg)

(An intent of an) opinionated RESTful Flask for big applications.

In development...


Logo and some icons made by [Freepik](http://www.freepik.com) from
[Flaticon](https://www.flaticon.com/), licensed by
[CC 3.0 BY](http://creativecommons.org/licenses/by/3.0/).

## How to run tests
```bash
# clone repository
git clone git@github.com:eReuse/teal.git

# prepare venv & install dependencies
export ENV_NAME='env'
python3 -m venv $ENV_NAME
source $ENV_NAME/bin/activate
pip install wheel pytest==3.7.2
pip install -r tests/requirements.txt

# run it
pytest --maxfail=5 tests/
```
