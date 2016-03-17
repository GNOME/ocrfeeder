#!/bin/sh
# Calls gnome-autogen to build Makefiles and run configure

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.

(test -f $srcdir/configure.ac) || {
    echo -n "**Error**: Directory "\`$srcdir\'" does not look like the"
    echo " top-level $PKG_NAME directory"
    exit 1
}

which gnome-autogen.sh || {
    echo "You need to install gnome-common module and make"
    echo "sure the gnome-autogen.sh script is in your \$PATH."
    exit 1
}

. gnome-autogen.sh
