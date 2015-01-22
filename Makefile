######################################################################
#
# $Id$
#
######################################################################
#
# Copyright 2011-2014 KoreLogic, Inc. All Rights Reserved.
#
# This software, having been partly or wholly developed and/or
# sponsored by KoreLogic, Inc., is hereby released under the terms
# and conditions set forth in the project's "README.LICENSE" file.
# For a list of all contributors and sponsors, please refer to the
# project's "README.CREDITS" file.
#
######################################################################
#
# Purpose: Build the Giles compiler.
#
######################################################################

DESTDIR	=
PREFIX  =   /usr/local
MANPATH	=	$(DESTDIR)$(PREFIX)/man

all: build

build:
	@python3 setup.py build

clean:
	@python3 setup.py clean --all
	@rm -rf dist giles.egg-info giles/__pycache__ tests/__pycache__ examples/*/*.yml.sql

dist sdist:
	@python3 setup.py sdist

install: build
	@python3 setup.py install --root "/$(DESTDIR)"
	@mkdir -p "$(MANPATH)/man1" && install -m 0644 doc/giles.1 "$(MANPATH)/man1/giles.1"

check test tests: build
	@python3 setup.py test

check-clean: clean

test-clean: clean

lint flake:
	@which flake8 > /dev/null
	@python3 `which flake8` -v --max-line-length=140 setup.py
	@cd giles && python3 `which flake8` -v --max-line-length=140 *.py

sign: dist
	@version_number=`egrep '^version = 0x' giles/__init__.py | awk '{print $$3}'` ; \
	version_string=`utils/version2string -t tar -v $${version_number}` ; \
	dist_file="dist/giles-$${version_string}.tar.gz" ; \
	gpg --default-key giles-project@korelogic.com -s -b $${dist_file}

