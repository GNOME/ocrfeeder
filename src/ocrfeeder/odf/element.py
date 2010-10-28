#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007 Søren Roug, European Environment Agency
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

import xml.dom
from namespaces import nsdict
import grammar
from attrconverters import AttrConverters

# The following code is pasted form xml.sax.saxutils
# Tt makes it possible to run the code without the xml sax package installed
# To make it possible to have <rubbish> in your text elements, it is necessary to escape the texts
def _escape(data, entities={}):
    """ Escape &, <, and > in a string of data.

        You can escape other strings of data by passing a dictionary as
        the optional entities parameter.  The keys and values must all be
        strings; each key will be replaced with its corresponding value.
    """
    data = data.replace("&", "&amp;")
    data = data.replace("<", "&lt;")
    data = data.replace(">", "&gt;")
    for chars, entity in entities.items():
        data = data.replace(chars, entity)
    return data

def _quoteattr(data, entities={}):
    """ Escape and quote an attribute value.

        Escape &, <, and > in a string of data, then quote it for use as
        an attribute value.  The \" character will be escaped as well, if
        necessary.

        You can escape other strings of data by passing a dictionary as
        the optional entities parameter.  The keys and values must all be
        strings; each key will be replaced with its corresponding value.
    """
    data = _escape(data, entities)
    if '"' in data:
        if "'" in data:
            data = '"%s"' % data.replace('"', "&quot;")
        else:
            data = "'%s'" % data
    else:
        data = '"%s"' % data
    return data

def _nssplit(qualifiedName):
    """ Split a qualified name into namespace part and local part.  """
    fields = qualifiedName.split(':', 1)
    if len(fields) == 2:
        return fields
    else:
        return (None, fields[0])

def _nsassign(namespace):
    return nsdict.setdefault(namespace,"ns" + str(len(nsdict)))

# Exceptions
class IllegalChild(StandardError):
    """ Complains if you add an element to a parent where it is not allowed """
class IllegalText(StandardError):
    """ Complains if you add text or cdata to an element where it is not allowed """

class Node(xml.dom.Node):
    """ super class for more specific nodes """

class Text(Node):
    nodeType = Node.TEXT_NODE

    def __init__(self, data):
        self.data = data

    def toXml(self,level,f):
        if self.data:
            f.write(_escape(unicode(self.data).encode('utf-8')))
    
class CDATASection(Text):
    nodeType = Node.CDATA_SECTION_NODE

    def toXml(self,level,f):
        if self.data:
            f.write('<![CDATA[%s]]>' % self.data)

class Element(Node):
    """ Creates a arbitrary element and is intended to be subclassed not used on its own.
        This element is the base of every element it defines a class which resembles
        a xml-element. The main advantage of this kind of implementation is that you don't
        have to create a toXML method for every different object. Every element
        consists of an attribute, optional subelements, optional text and optional cdata.
    """

    nodeType = Node.ELEMENT_NODE
    parentNode = None
    namespaces = {}  # Due to shallow copy this is a static variable
    
    def __init__(self, attributes=None, elements=None, text=None, cdata=None, qname=None, qattributes=None, **args):
        if qname is not None:
            self.qname = qname
        assert(hasattr(self, 'qname'))
        self.elements=[]
        self.allowed_children = grammar.allowed_children.get(self.qname)
        namespace = self.qname[0]
        prefix = _nsassign(namespace)
        if not self.namespaces.has_key(namespace):
            self.namespaces[namespace] = prefix
        self.type= prefix + ":" + self.qname[1]
        if elements is not None:
           self.elements=elements
        if text is not None:
            self.addText(text)
        if cdata is not None:
            self.addCDATA(cdata)

        allowed_attrs = self.allowed_attributes()
        if allowed_attrs is not None:
            allowed_args = [ a[1].lower().replace('-','') for a in allowed_attrs]
        self.attributes={}
        # Load the attributes from the 'attributes' argument
        if attributes:
            for attr, value in attributes.items():
                self.addAttribute(attr, value)
        # Load the qualified attributes
        if qattributes:
            for attr, value in qattributes.items():
                self.addAttrNS(attr[0], attr[1], value)
        if allowed_attrs is not None:
            # Load the attributes from the 'args' argument
            for arg in args.keys():
                self.addAttribute(arg, args[arg])
        else:
            for arg in args.keys():  # If any attribute is allowed
                self.attributes[arg]=args[arg]
        # Test that all mandatory attributes have been added.
        required = grammar.required_attributes.get(self.qname)
        if required:
            for r in required:
                if self.getAttr(r[0],r[1]) is None:
                    raise AttributeError, "Required attribute missing: %s in <%s>" % (r[1].lower().replace('-',''), self.type)

    def allowed_attributes(self):
        return grammar.allowed_attributes.get(self.qname)

    def addElement(self, element):
        """ adds an element to an Element

            Element.addElement(Element)
        """
        if self.allowed_children is not None:
            if element.qname not in self.allowed_children:
                raise IllegalChild, "<%s> is not allowed in <%s>" % ( element.type, self.type)
        self.elements.append(element)
        element.parentNode = self

    def addText(self, text):
        if self.qname not in grammar.allows_text:
            raise IllegalText, "The <%s> element does not allow text" % self.type
        else:
            if text != '':
                self.elements.append(Text(text))

    def addCDATA(self, cdata):
        if self.qname not in grammar.allows_text:
            raise IllegalText, "The <%s> element does not allow text" % self.type
        else:
            self.elements.append(CDATASection(cdata))

    def addAttribute(self, attr, value):
        """ Add an attribute to the element
            This is sort of a convenience method. All attributes in ODF have
            namespaces. The library knows what attributes are legal and then allows
            the user to provide the attribute as a keyword argument and the
            library will add the correct namespace.
        """
        allowed_attrs = self.allowed_attributes()
        if allowed_attrs is None:
            if type(attr) == type(()):
                prefix, localname = attr
                self.addAttrNS(prefix, localname, value)
            else:
                raise AttributeError, "Unable to add simple attribute - use (namespace, localpart)"
        else:
            # Construct a list of allowed arguments
            allowed_args = [ a[1].lower().replace('-','') for a in allowed_attrs]
            if attr not in allowed_args:
                raise AttributeError, "Attribute %s is not allowed in <%s>" % ( attr, self.type)
            i = allowed_args.index(attr)
            self.addAttrNS(allowed_attrs[i][0], allowed_attrs[i][1], value)

    def addAttrNS(self, namespace, localpart, value):
        """ Add an attribute to the element
            In case you need to add an attribute the library doesn't know about
            then you must provide the full qualified name
            It will not check that the attribute is legal according to the schema.
        """
        allowed_attrs = self.allowed_attributes()
        prefix = _nsassign(namespace)
        if not self.namespaces.has_key(namespace):
            self.namespaces[namespace] = prefix
#       if allowed_attrs and (namespace, localpart) not in allowed_attrs:
#           raise AttributeError, "Attribute %s:%s is not allowed in element <%s>" % ( prefix, localpart, self.type)
        c = AttrConverters()
        self.attributes[prefix + ":" + localpart] = c.convert((namespace, localpart), value, self.qname)

    def getAttr(self, namespace, localpart):
        prefix = _nsassign(namespace)
        if not self.namespaces.has_key(namespace):
            self.namespaces[namespace] = prefix
        return self.attributes.get(prefix + ":" + localpart)

    def toXml(self,level,f):
        """ Generate XML stream out of the tree structure """
        f.write('<'+self.type)
        if self.parentNode is None:
            for namespace, prefix in self.namespaces.items():
                f.write(' xmlns:' + prefix + '="'+ _escape(str(namespace))+'"')
        for attkey in self.attributes.keys():
            f.write(' '+_escape(str(attkey))+'='+_quoteattr(unicode(self.attributes[attkey]).encode('utf-8')))
        if self.elements:
            f.write('>')
        for element in self.elements:
            element.toXml(level+1,f)
        if self.elements:
            f.write('</'+self.type+'>')
        else:
            f.write('/>')

    def hasChildren(self):
        """ Tells whether this element has any children; text nodes,
            subelements, whatever.
        """
        return len(self.elements) > 0
