# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007 Søren Roug, European Environment Agency
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Contributor(s):
#

__doc__="""Use OpenDocument to generate your documents."""

import zipfile, time, sys, mimetypes, copy
import cStringIO
from namespaces import *
import manifest, meta
from office import *
from element import Node

__version__= TOOLSVERSION

_XMLPROLOGUE = "<?xml version='1.0' encoding='UTF-8'?>\n"

# We need at least Python 2.2
assert sys.version_info[0]>=2 and sys.version_info[1] >= 2

sys.setrecursionlimit=50
#The recursion limit is set conservative so mistakes like s=content() s.addElement(s)
#won't eat up too much processor time.

odmimetypes = {
 'application/vnd.oasis.opendocument.text':                  '.odt',
 'application/vnd.oasis.opendocument.text-template':         '.ott',
 'application/vnd.oasis.opendocument.graphics':              '.odg',
 'application/vnd.oasis.opendocument.graphics-template':     '.otg',
 'application/vnd.oasis.opendocument.presentation':          '.odp',
 'application/vnd.oasis.opendocument.presentation-template': '.otp',
 'application/vnd.oasis.opendocument.spreadsheet':           '.ods',
 'application/vnd.oasis.opendocument.spreadsheet-template':  '.ots',
 'application/vnd.oasis.opendocument.chart':                 '.odc',
 'application/vnd.oasis.opendocument.chart-template':        '.otc',
 'application/vnd.oasis.opendocument.image':                 '.odi',
 'application/vnd.oasis.opendocument.image-template':        '.oti',
 'application/vnd.oasis.opendocument.formula':               '.odf',
 'application/vnd.oasis.opendocument.formula-template':      '.otf',
 'application/vnd.oasis.opendocument.text-master':           '.odm',
 'application/vnd.oasis.opendocument.text-web':              '.oth',
}

class OpenDocument:
    """ Use the toXml method to write the XML
        source to the screen or to a file
        d = OpenDocument(mimetype)
        d.toXml(optionalfilename)
    """
    thumbnail = None

    def __init__(self, mimetype):
        self.mimetype = mimetype
        self.childobjects = []
        self.folder = "" # Always empty for toplevel documents

        self.Pictures = {}
        self.meta = Meta()
        self.meta.addElement(meta.Generator(text=TOOLSVERSION))
        self.scripts = Scripts()
        self.fontfacedecls = FontFaceDecls()
        self.settings = Settings()
        self.styles = Styles()
        self.automaticstyles = AutomaticStyles()
        self.masterstyles = MasterStyles()
        self.body = Body()

    def toXml(self, filename=''):
        import cStringIO
        xml=cStringIO.StringIO()
        xml.write(_XMLPROLOGUE)
        self.body.toXml(0, xml)
        if not filename:
            return xml.getvalue()
        else:
            f=file(filename,'w')
            f.write(xml.getvalue())
            f.close()

    def contentxml(self):
        """ Generates the content.xml file """
        x = DocumentContent()
        if self.scripts.hasChildren():
            x.addElement(self.scripts)
        if self.fontfacedecls.hasChildren():
            x.addElement(self.fontfacedecls)
        x.addElement(self.automaticstyles)
        x.addElement(self.body)
        xml=cStringIO.StringIO()
        xml.write(_XMLPROLOGUE)
        x.toXml(0,xml)
        return xml.getvalue()

    def manifestxml(self):
        """ Generates the manifest.xml file """
        xml=cStringIO.StringIO()
        xml.write(_XMLPROLOGUE)
        self.manifest.toXml(0,xml)
        return xml.getvalue()

    def metaxml(self):
        """ Generates the meta.xml file """
        x = DocumentMeta()
        x.addElement(self.meta)
        xml=cStringIO.StringIO()
        xml.write(_XMLPROLOGUE)
        x.toXml(0,xml)
        return xml.getvalue()

    def settingsxml(self):
        """ Generates the settings.xml file """
        x = DocumentSettings()
        x.addElement(self.settings)
        xml=cStringIO.StringIO()
        xml.write(_XMLPROLOGUE)
        x.toXml(0,xml)
        return xml.getvalue()

    def _parseoneelement(self, top, stylelist):
        """ Finds references to style objects in master-styles """
        for e in top.elements:
            if e.nodeType == Node.ELEMENT_NODE:
                for styleref in ( (DRAWNS,u'style-name'), (DRAWNS,u'text-style-name'),
                        (PRESENTATIONNS,u'style-name'),
                        (STYLENS,u'style-name'), (STYLENS,u'page-layout-name'),
                        (TEXTNS,u'style-name')):
                    if e.getAttr(styleref[0],styleref[1]):
                        stylename = e.getAttr(styleref[0],styleref[1])
                        stylelist.append(stylename)
                stylelist = self._parseoneelement(e, stylelist)
        return stylelist

    def _getmasterstyles(self):
        """ Loop through the masterstyles elements, and find the automatic
            styles that are used. These will be added to the automatic-styles
            element in styles.xml
        """
        stylelist = self._parseoneelement(self.masterstyles, [])
        automaticmasterstyles = AutomaticStyles()
        for e in self.automaticstyles.elements:
            if e.getAttr(STYLENS,u'name') in stylelist:
                automaticmasterstyles.addElement(copy.deepcopy(e))
        return automaticmasterstyles

    def stylesxml(self):
        """ Generates the styles.xml file """
        x = DocumentStyles()
        if self.fontfacedecls.hasChildren():
            x.addElement(self.fontfacedecls)
        x.addElement(self._getmasterstyles())
        x.addElement(self.styles)
        if self.masterstyles.hasChildren():
            x.addElement(self.masterstyles)
        xml=cStringIO.StringIO()
        xml.write(_XMLPROLOGUE)
        x.toXml(0,xml)
        return xml.getvalue()

    def addPicture(self, filename):
        """ Add a picture
            It uses the same convention as OOo, in that it saves the picture in
            the zipfile in the subdirectory 'Pictures'
        """
        mediatype, encoding = mimetypes.guess_type(filename)
        if mediatype is None:
            mediatype = ''
            try: ext = filename[filename.rindex('.'):]
            except: ext=''
        else:
            ext = mimetypes.guess_extension(mediatype)
        manifestfn = "Pictures/%0.0f%s" % ((time.time()*10000000000), ext)

        self.Pictures[manifestfn] = (filename, mediatype)
        return manifestfn

    def addThumbnail(self):
        """ Add a fixed thumbnail
            The thumbnail in the library is pretty big, so this is pretty useless.
        """
        import thumbnail
        self.thumbnail = thumbnail.thumbnail()

    def addObject(self, document):
        """ Add an object. The object must be an OpenDocument class
            The return value will be the folder in the zipfile the object is stored in
        """
        self.childobjects.append(document)
        document.folder = "%s/Object %d" % (self.folder, len(self.childobjects))
        return ".%s" % document.folder

    def _savePictures(self, object, folder):
        hasPictures = False
        for arcname, picturerec in object.Pictures.items():
            filename, mediatype = picturerec
            self.manifest.addElement(manifest.FileEntry(fullpath="%s%s" % ( folder ,arcname), mediatype=mediatype))
            hasPictures = True
            self._z.write(filename, arcname, zipfile.ZIP_STORED)
        if hasPictures:
            self.manifest.addElement(manifest.FileEntry(fullpath="%sPictures/" % folder,mediatype=""))
        # Look in subobjects
        subobjectnum = 1
        for subobject in object.childobjects:
            self._savePictures(subobject,'%sObject %d/' % (folder, subobjectnum))
            subobjectnum += 1

    def save(self, outputfile, addsuffix=False):
        """ Save the document under the filename """
        self.manifest = manifest.Manifest()
        mimetype = self.mimetype
        suffix = odmimetypes.get(mimetype,'.xxx')

        if outputfile == '-':
            self._z = zipfile.ZipFile(sys.stdout,"w")
        else:
            if addsuffix:
                outputfile = outputfile + suffix
            self._z = zipfile.ZipFile(outputfile,"w")

        self._now = time.localtime()[:6]

        # Write mimetype
        zi = zipfile.ZipInfo('mimetype', self._now)
        zi.compress_type = zipfile.ZIP_STORED
        self._z.writestr(zi, self.mimetype)

        self._saveXmlObjects(self,"")

        # Write pictures
        self._savePictures(self,"")

        # Write the thumbnail
        if self.thumbnail is not None:
            self.manifest.addElement(manifest.FileEntry(fullpath="Thumbnails/", mediatype=''))
            self.manifest.addElement(manifest.FileEntry(fullpath="Thumbnails/thumbnail.png", mediatype=''))
            zi = zipfile.ZipInfo("Thumbnails/thumbnail.png", self._now)
            zi.compress_type = zipfile.ZIP_DEFLATED
            self._z.writestr(zi, self.thumbnail)

        # Write manifest
        zi = zipfile.ZipInfo("META-INF/manifest.xml", self._now)
        zi.compress_type = zipfile.ZIP_DEFLATED
        self._z.writestr(zi, self.manifestxml() )
        self._z.close()
        del self._z
        del self._now
        del self.manifest


    def _saveXmlObjects(self, object, folder):
        if self == object:
            self.manifest.addElement(manifest.FileEntry(fullpath="/", mediatype=object.mimetype))
        else:
            self.manifest.addElement(manifest.FileEntry(fullpath=folder, mediatype=object.mimetype))
        # Write styles
        self.manifest.addElement(manifest.FileEntry(fullpath="%sstyles.xml" % folder, mediatype="text/xml"))
        zi = zipfile.ZipInfo("%sstyles.xml" % folder, self._now)
        zi.compress_type = zipfile.ZIP_DEFLATED
        self._z.writestr(zi, object.stylesxml() )

        # Write content
        self.manifest.addElement(manifest.FileEntry(fullpath="%scontent.xml" % folder, mediatype="text/xml"))
        zi = zipfile.ZipInfo("%scontent.xml" % folder, self._now)
        zi.compress_type = zipfile.ZIP_DEFLATED
        self._z.writestr(zi, object.contentxml() )

        # Write settings
        if self == object and self.settings.hasChildren():
            self.manifest.addElement(manifest.FileEntry(fullpath="settings.xml",mediatype="text/xml"))
            zi = zipfile.ZipInfo("%ssettings.xml" % folder, self._now)
            zi.compress_type = zipfile.ZIP_DEFLATED
            self._z.writestr(zi, object.settingsxml() )

        # Write meta
        if self == object:
            self.manifest.addElement(manifest.FileEntry(fullpath="meta.xml",mediatype="text/xml"))
            zi = zipfile.ZipInfo("meta.xml", self._now)
            zi.compress_type = zipfile.ZIP_DEFLATED
            self._z.writestr(zi, object.metaxml() )

        # Write subobjects
        # FIXME: Make it recursive
        subobjectnum = 1
        for subobject in object.childobjects:
            self._saveXmlObjects(subobject, '%sObject %d/' % (folder, subobjectnum))
            subobjectnum += 1

# Convenience functions
def OpenDocumentChart():
    doc = OpenDocument('application/vnd.oasis.opendocument.chart')
    doc.chart = Chart()
    doc.body.addElement(doc.chart)
    return doc

def OpenDocumentDrawing():
    doc = OpenDocument('application/vnd.oasis.opendocument.graphics')
    doc.drawing = Drawing()
    doc.body.addElement(doc.drawing)
    return doc

def OpenDocumentImage():
    doc = OpenDocument('application/vnd.oasis.opendocument.image')
    doc.image = Image()
    doc.body.addElement(doc.image)
    return doc

def OpenDocumentPresentation():
    doc = OpenDocument('application/vnd.oasis.opendocument.presentation')
    doc.presentation = Presentation()
    doc.body.addElement(doc.presentation)
    return doc

def OpenDocumentSpreadsheet():
    doc = OpenDocument('application/vnd.oasis.opendocument.spreadsheet')
    doc.spreadsheet = Spreadsheet()
    doc.body.addElement(doc.spreadsheet)
    return doc

def OpenDocumentText():
    doc = OpenDocument('application/vnd.oasis.opendocument.text')
    doc.text = Text()
    doc.body.addElement(doc.text)
    return doc

if __name__=='__main__':
    import style
    from text import H, P

    textdoc=OpenDocumentText()
    # Styles
    s = textdoc.styles
    h1style = style.Style(name="Heading 1",family="paragraph")
    h1style.addElement(style.TextProperties(attributes={'fontsize':"24pt",'fontweight':"bold" }))
    s.addElement(h1style)

    h=H(outlinelevel=1, stylename=h1style, text="Climate change impact in Europe")
    textdoc.text.addElement(h)
    p = P(text="The earth's climate has not changed many times in the course of its long history.")
    textdoc.text.addElement(p)
    textdoc.save("test.odt")

# vim: set expandtab sw=4 :
