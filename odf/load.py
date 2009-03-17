#!/usr/bin/python
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

# This script is to be embedded in opendocument.py later
# The purpose is to read an ODT/ODP/ODS file and create the datastructure
# in memory. The user should then be able to make operations and then save
# the structure again.

import zipfile
from xml.sax import make_parser,handler
from xml.sax.xmlreader import InputSource
import xml.sax.saxutils
import sys
from odf.opendocument import OpenDocument
from odf import element
from odf.namespaces import STYLENS, OFFICENS


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



#
# Parse the XML files
#
class ODFParser(handler.ContentHandler):
    """ Extract headings from content.xml of an ODT file """
    def __init__(self, document):
        self.doc = document
        self.data = []
        self.level = 0
        self.parse = False

    def characters(self, data):
        if self.parse == False:
            return
        self.data.append(data)

    def startElementNS(self, tag, qname, attrs):
        if tag in ((OFFICENS, 'body'), (OFFICENS, 'styles')):
            self.parse = True
        if self.parse == False:
            return

        self.level = self.level + 1
        # Add any accumulated text content
        content = ''.join(self.data).strip()
        if len(content) > 0:
            self.parent.addText(content)
            self.data = []
        # Create the element
        attrdict = {}
        for (att,value) in attrs.items():
            attrdict[att] = value
        try:
            e = element.Element(qname = tag, qattributes=attrdict)
            self.curr = e
        except AttributeError, v:
            print "Error: %s" % v

        if tag == (OFFICENS,'styles'):
            self.doc.styles = e
        elif tag == (OFFICENS, 'body'):
            self.doc.body = e
        else:
            self.parent.addElement(e)
        self.parent = e


    def endElementNS(self, tag, qname):
        if tag in ((OFFICENS, 'body'), (OFFICENS, 'styles')):
            self.parse = False
        if self.parse == False:
            return
        self.level = self.level - 1
        str = ''.join(self.data)
        self.data = []
        self.parent = self.curr.parentNode



def _getxmlpart(odffile, xmlfile):
    """ Get the content out of the ODT file"""
    z = zipfile.ZipFile(odffile)
    content = z.read(xmlfile)
    z.close()
    return content

def load(odtfile):
    mimetype = _getxmlpart(odtfile,'mimetype')
    d = OpenDocument(mimetype)

    for xmlfile in ('content.xml',):
        xmlpart = _getxmlpart(odtfile, xmlfile)

        parser = make_parser()
        parser.setFeature(handler.feature_namespaces, 1)
        parser.setContentHandler(ODFParser(d))
        parser.setErrorHandler(handler.ErrorHandler())

        inpsrc = InputSource()
        inpsrc.setByteStream(StringIO(xmlpart))
        parser.parse(inpsrc)
    return d
