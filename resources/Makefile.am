SUBDIRS = icons

desktopdir = $(datadir)/applications
desktop_in_files = ocrfeeder.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

appstreamdir = $(datadir)/metainfo
appstream_in_files = ocrfeeder.appdata.xml.in
appstream_DATA = $(appstream_in_files:.xml.in=.xml)
@INTLTOOL_XML_RULE@

ui_filesdir = $(datadir)/ocrfeeder
ui_files_DATA = spell-checker.ui menubar.ui

man_MANS = ocrfeeder.1 ocrfeeder-cli.1

EXTRA_DIST = $(desktop_in_files) $(appdata_in_files) $(man_MANS) $(ui_files_DATA)

CLEANFILES = $(desktop_DATA) $(appstream_DATA)
