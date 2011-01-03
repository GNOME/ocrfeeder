SUBDIRS = icons

desktopdir = $(datadir)/applications
desktop_in_files = ocrfeeder.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

spellchecker_uidir = $(datadir)/ocrfeeder
spellchecker_ui_DATA = spell-checker.ui

man_MANS = ocrfeeder.1 ocrfeeder-cli.1

EXTRA_DIST = $(desktop_in_files) $(man_MANS) $(spellchecker_ui_DATA)

CLEANFILES = $(desktop_DATA)
