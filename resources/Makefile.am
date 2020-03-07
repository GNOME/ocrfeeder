SUBDIRS = icons

appicondir = $(datadir)/icons/hicolor/scalable/apps
appicon_DATA = icons/org.gnome.OCRFeeder.svg

desktopdir = $(datadir)/applications
desktop_in_files = org.gnome.OCRFeeder.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

appstreamdir = $(datadir)/metainfo
appstream_in_files = org.gnome.OCRFeeder.appdata.xml.in
appstream_DATA = $(appstream_in_files:.xml.in=.xml)
@INTLTOOL_XML_RULE@


ui_filesdir = $(datadir)/ocrfeeder
ui_files_DATA = spell-checker.ui menubar.ui

man_MANS = ocrfeeder.1 ocrfeeder-cli.1

EXTRA_DIST = 			\
	$(appicon_DATA) 	\
	$(desktop_in_files)	\
	$(appdata_in_files)	\
	$(man_MANS)		\
	$(ui_files_DATA)	\
	$(appstream_in_files)

CLEANFILES = $(desktop_DATA) $(appstream_DATA)
