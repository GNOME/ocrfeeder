AC_PREREQ([2.63])
AC_INIT([ocrfeeder],
        [0.8.5],
        [https://gitlab.gnome.org/GNOME/ocrfeeder/issues],
        [ocrfeeder])

AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE([1.11 foreign])
AM_MAINTAINER_MODE([enable])
# Support silent build rules. Disable by either passing --disable-silent-rules
# to configure or passing V=1 to make
AM_SILENT_RULES([yes])

dnl == define if sandbox mode is enabled ==
AC_ARG_ENABLE([sandbox],
	AS_HELP_STRING([--enable-sandbox], [Enable sandbox mode]),
	[enable_sandbox="$enableval"],
	[enable_sandbox="no"])

AS_IF([test "x$enable_sandbox" = "xyes"], [
	AC_SUBST([SANDBOX], [True])
], [
	AC_SUBST([SANDBOX], [False])
])

dnl == check for python ==
AM_PATH_PYTHON(3.5)

dnl == Python dependencies ==
AX_PYTHON_MODULE([enchant],[needed])
AX_PYTHON_MODULE([sane],[needed])
AX_PYTHON_MODULE([PIL],[needed])
AX_PYTHON_MODULE([reportlab],[needed])
AX_PYTHON_MODULE([odf],[needed])

dnl == Introspection Dependencies ==

PYTHON_GI_MODULES="Gtk GooCanvas"

for i in $PYTHON_GI_MODULES;
do
AC_MSG_CHECKING(gobject introspection module $i)
$PYTHON -c "from gi.repository import $i" 2>/dev/null;

if test $? -eq 0;
then
	AC_MSG_RESULT(yes)
else
	AC_MSG_RESULT(no)
	AC_MSG_ERROR(failed to find required GObject Introspection module $i)
	exit 1
fi
done

dnl == i18n ==
GETTEXT_PACKAGE=ocrfeeder
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])
AM_GLIB_GNU_GETTEXT

dnl == intltool check ==
IT_PROG_INTLTOOL([0.35.0])

dnl == Documentation ==
YELP_HELP_INIT

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
src/ocrfeeder/studio/Makefile
src/ocrfeeder/util/Makefile
src/ocrfeeder/util/constants.py
help/Makefile
resources/Makefile
resources/icons/Makefile
])
