#!/bin/bash -ex

pep8 --repeat --ignore=W391,E201 altai_api tests
rm -f .coverage
nosetests --with-coverage --cover-package=altai_api
pylint  -r n tests altai_api

