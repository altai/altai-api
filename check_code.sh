#!/bin/bash -ex

pep8 --ignore=W391,E201 altai_api tests
nosetests --with-coverage --cover-package=altai_api
pylint  -r n tests altai_api

