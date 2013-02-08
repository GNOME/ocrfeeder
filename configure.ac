AC_PREREQ([2.63])
AC_INIT([ocrfeeder],
        [0.7.11],
        [https://bugzilla.gnome.org/enter_bug.cgi?product=ocrfeeder],
        [ocrfeeder])

AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE([1.11])
AM_MAINTAINER_MODE([enable])
# Support silent build rules. Disable by either passing --disable-silent-rules
# to configure or passing V=1 to make
AM_SILENT_RULES([yes])

dnl == check for python ==
AM_PATH_PYTHON(2.5)

dnl == Python dependencies ==
AX_PYTHON_MODULE([gtk],[needed])
AX_PYTHON_MODULE([pygtk],[needed])
AX_PYTHON_MODULE([gtkspell],[needed])
AX_PYTHON_MODULE([goocanvas],[needed])
AX_PYTHON_MODULE([enchant],[needed])
AX_PYTHON_MODULE([sane],[needed])
AX_PYTHON_MODULE([reportlab],[needed])

dnl == i18n ==
GETTEXT_PACKAGE=ocrfeeder
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])
AM_GLIB_GNU_GETTEXT

dnl == intltool check ==
IT_PROG_INTLTOOL([0.35.0])

dnl == Documentation ==
GNOME_DOC_INIT

dnl == generate makefiles ==
AC_OUTPUT([
Makefile
po/Makefile.in
bin/Makefile
bin/ocrfeeder
bin/ocrfeeder-cli
src/Makefile
src/ocrfeeder/Makefile
src/ocrfeeder/feeder/Makefile
src/ocrfeeder/odf/Makefile
src/ocrfeeder/studio/Makefile
src/ocrfeeder/util/Makefile
src/ocrfeeder/util/constants.py
help/Makefile
resources/Makefile
resources/icons/Makefile
])
