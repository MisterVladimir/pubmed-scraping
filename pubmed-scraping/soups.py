# -*- coding: utf-8 -*-
"""
@author: Vladimir Shteyn
@email: vladimir.shteyn@googlemail.com

Copyright Vladimir Shteyn, 2018

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from bs4 import BeautifulSoup
import numpy as np

#TODO: add class-specific SoupStrainers to only parse the necessary parts of 
#      the XML file 

class NCBISoupABC(type): 
    """
    Abstract base class for Soup objects, which parse XML requested from 
    NCBI. 
    """
    @classmethod
    def add_generator_property(cls, tag_name): 
        """
        Generator that help iterate through tags of an XML file. 
        
        Parameters
        ------------
        tag_name : str or tuple
            If string, returns a single_generator; if tuple, returns nested 
            generator. 
        
            We use a string if we know there's only one of a particular tag in 
            the XML. For example, there'll only be one "title" tag for a
            Pubmed article. Alternatively, we use this to fetch one tag at 
            a time. 
            
            Otherwise, if we know there'll be many instances of a particular 
            tag, e.g. an author name, we pass in a tuple. For example, to 
            retrieve the author list, we pass in 
            ('author', ('forename', 'lastname', 'affiliation')). This searches
            the XML for tags named 'author', and returns a dictionary whose 
            keys are 'forename', 'lastname', and 'affiliation', and whose 
            values are tagged as such under a 'author' parent tag. For example, 
            passing in ('author', ('forename', 'lastname')) to this XML

            <authorlist completeyn="Y">
            <author validyn="Y">
            <lastname>Doe</lastname>
            <forename>John</forename>
            <initials>J</initials> 
            <authorlist completeyn="Y">
            <author validyn="Y">
            <lastname>Smith</lastname>
            <forename>Jane</forename>
            <initials>J</initials> 
            
            returns 
            
            {'lastname': [b'Doe', b'Smith'], 
             'forename': [b'John', b'Jane'] }
        """
        def single_generator(self): 
            for article in self: 
                try: 
                    li = article.find_all(tag_name) 
                    for element in li: 
                        yield element.string.encode('utf-8') 
                except AttributeError: 
                    pass 
        
        def nested_generator(self): 
            for article in self: 
                name = tag_name[0] 
                keys = tag_name[1]
                yield {key: [c.string.encode('utf-8') for contents in  \
                             article(name) for c in contents(key)] for \
                             key in keys}

#                tag = article.find_all(tag_name[0])   
#                yield [{k: [t.string.encode('utf-8') for t in item.find_all(k)]\
#                            for k in rest if not (item.__getattr__(k) is None)} 
#                        for item in tag if isinstance(item, Tag)]
                        
        if isinstance(tag_name, (str, bytes)): 
            generator = single_generator 
        elif np.iterable(tag_name): 
            generator = nested_generator
        else: 
            raise TypeError("")
        
        return property(generator)
    
    def __new__(metacls, name, bases, namespace, **kwds):
        for k, v in kwds.items(): 
            namespace[k] = NCBISoupABC.add_generator_property(v)
        result = type.__new__(metacls, name, bases, namespace)
        return result

    def __subclasscheck__(cls, subclass):
#        https://stackoverflow.com/questions/40764347/python-subclasscheck-subclasshook
        required_attrs = ['uid']
        for attr in required_attrs:
            if any(attr in sub.__dict__ for sub in subclass.__mro__):
                continue
            return False
        return True

uid_kwargs = {'uid': 'id'}
class UIDSoup(BeautifulSoup, metaclass=NCBISoupABC, **uid_kwargs): 
    """
    Parses Pubmed IDs from XML resulting from a keyword search 
    (https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?)
    """
    def __iter__(self): 
        for i in self.body: 
            yield i 

summary_kwargs = {'title':'articletitle', 
                  'authors': ('author', ('lastname', 'forename', 'affiliation')), 
                  'date': ('pubdate', ('year', 'month', 'day')), 
                  'journal': ('journal', ('title',)), 
                  'grant': ('grant', ('grantid',))
                  }
class SummarySoup(BeautifulSoup, metaclass=NCBISoupABC, **summary_kwargs): 
    """
    Parses the info of a Pubmed summary -- things like article abstract, 
    title, authors, etc. We probably get this XML using 
    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi? 
    """
    def __iter__(self): 
        for summary in self.body.pubmedarticleset('pubmedarticle'): 
            yield summary
    
#    it's this kind of copying that we (mostly) avoid by using the metaclass
#    in the case of pmids and doi, it's unavoidable -- as far as I can figure out 
    @property
    def uid(self): 
        for article in self: 
            yield article.articleidlist.find(idtype="pubmed").string.encode('utf-8') 
    @property
    def doi(self): 
        for article in self: 
            yield article.articleidlist.find(idtype="doi").string.encode('utf-8') 
    @property
    def pmc(self): 
        for article in self: 
            yield article.articleidlist.find(idtype="pmc").string.encode('utf-8') 
    
    @property 
    def abstract(self): 
#        the tricky thing about extracting abstracts is that some come in 
#        multiple sections labeled by attributes like "summary" and "materials 
#        and methods" such that there is occasionally more than one 
#        'abstracttext' tag per article summary 
#        this inconsistency makes it impossible to use the boilerplate 
#        nested_generator or single_generator of the metaclass
        for article in self: 
            ab = [ab for ab in article('abstracttext').string] 
            yield ' '.join(ab).encode('utf-8')
    
    def reset_iterator(self): 
        pass 

class ProteinSoup(metaclass=NCBISoupABC): 
#    TODO: 
    pass 

class GeneSoup(metaclass=NCBISoupABC): 
#    TODO: 
    pass 

class SimpleUIDList(metaclass=NCBISoupABC): 
    """
    Fake UIDSoup. 
    """
    def __init__(self, uids): 
        self.uid = iter(uids)
        
    @property
    def uid(self): 
        for i in self._uid: 
            yield i
    
    @uid.setter
    def uid(self, val): 
        self._uid = val