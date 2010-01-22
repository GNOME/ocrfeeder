PYTHON=`which python`
DESTDIR=/
BUILDIR=$(CURDIR)/debian/ocrfeeder
PROJECT=ocrfeeder
PO_DIR=po
VERSION=0.6

all:
	@echo "make source   - Create source package"
	@echo "make install  - Install on local system"
	@echo "make buildrpm - Generate a rpm package"
	@echo "make builddeb - Generate a deb package"
	@echo "make clean    - Get rid of scratch and byte files"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

buildrpm:
	$(PYTHON) setup.py bdist_rpm --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall

builddeb:
	# build the source package in the parent directory
	# then rename it to project_version.orig.tar.gz
	$(PYTHON) setup.py sdist $(COMPILE) --dist-dir=../ 
	rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*
	# build the package
	dpkg-buildpackage -i -I -rfakeroot

clean:
	$(PYTHON) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean
	rm -rf build/ MANIFEST
	find . -name '*.pyc' -delete

compilemessages:
	@# Compile .po to .mo
	@# Use it such as: make compilemessages L=pt_PT
	@if [ ! -z $(L) ]; then \
	  if [ -f "$(PO_DIR)/$(L).po" ]; then \
	    mkdir -p locale/$(L)/LC_MESSAGES; \
	    msgfmt --output-file=locale/$(L)/LC_MESSAGES/$(PROJECT).mo $(PO_DIR)/$(L).po; \
	    echo Generated locale/$(L)/LC_MESSAGES/$(PROJECT).mo; \
	  else \
	    echo $(PO_DIR)/$(L).po was not found.;\
	  fi \
	else \
	    echo Please provide the L argument. E.g.: make compilemessages L=pt_PT; \
	fi

generatepot:
	@# After this, use the following command to initiate an empty po: msginit --input=po/ocrfeeder.pot --locale=en_US
	@# To update an existing po, do this: msgmerge -U po/en_US.po new_en_US.po        the po/en_US.po will be updated.
	xgettext --language=Python --keyword=_ --output=$(PO_DIR)/$(PROJECT).pot studio/*.py feeder/*.py util/*.py ocrfeeder ocrfeeder-cli

