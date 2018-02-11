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
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from bs4 import BeautifulSoup, Tag, SoupStrainer
import numpy as np
import h5py

from query import UIDQuery

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
                    li = article.find_all(**tag_name)
                    if not li == []: 
                        yield ' '.join([element.string for element in 
                                        li]).encode('utf-8')
                    else: 
                        yield ''.encode('utf-8')
                except AttributeError: # if article is of type NavigableString
                    pass 
        
        def nested_generator(self): 
            for article in self: 
                name = tag_name[0] 
                keys = tag_name[1] 
                if isinstance(article, Tag): 
                    yield {key: [c.string.encode('utf-8') for contents in  \
                                 article(name) for c in contents(key)] for \
                                 key in keys} 
                    

#                tag = article.find_all(tag_name[0])   
#                yield [{k: [t.string.encode('utf-8') for t in item.find_all(k)]\
#                            for k in rest if not (item.__getattr__(k) is None)} 
#                        for item in tag if isinstance(item, Tag)]
                        
        if isinstance(tag_name, (str, bytes, dict)): 
            generator = single_generator 
        elif np.iterable(tag_name): 
            generator = nested_generator
        else: 
            raise TypeError("")
        
        return property(generator)
    
    def __new__(metacls, name, bases, namespace, **kwds): 
        namespace['_data_attrs'] = []
        for k, v in kwds.items(): 
            namespace[k] = NCBISoupABC.add_generator_property(v)
            namespace['_data_attrs'].append(k) 
            
        return type.__new__(metacls, name, bases, namespace)

    def __subclasscheck__(cls, subclass):
#        https://stackoverflow.com/questions/40764347/python-subclasscheck-subclasshook
        required_attrs = ['uid']
        for attr in required_attrs:
            if any(attr in sub.__dict__ for sub in subclass.__mro__):
                continue
            return False
        return True

uid_kwargs = {'_uid': ('idlist', ('id',))}
class UIDSoup(BeautifulSoup, metaclass=NCBISoupABC, **uid_kwargs): 
    """
    Parses Pubmed IDs from XML resulting from a keyword search 
    (https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?)
    """
    def __init__(self, markup='', features='lxml', builder=None, parse_only=None, 
                       from_encoding=None, excude_encodings=None, **kwargs): 
        super().__init__(markup, features, builder, parse_only, from_encoding, 
                         excude_encodings, **kwargs)
        
    def __iter__(self): 
        for i in self.body: 
            yield i 
    
    @property
    def uid(self): 
        uid = list(self._uid)[0]['id'].copy()
        for i in uid: 
            yield i
    
    def save(self, folder): 
        with h5py.File(folder + '\\uids.h5', 'w') as f: 
            data = [i for i in self.uid]
            f.create_dataset(name='uid', data=data)
#            keep similar h5 save format as UIDQuery
            fields = UIDQuery.fields.copy() 
            del fields[UIDQuery.query_key]
            for k, v in fields.items(): 
                f.attrs[k] = v.encode('utf-8')

summary_kwargs = {'abstract': {'name': 'abstracttext'}, 
                  'uid': {'idtype':'pubmed'}, 
                  'doi': {'idtype':'doi'}, 
                  'pmc': {'idtype':'pmc'}, 
                  'title':{'name': 'articletitle'}, 
                  'authors': ('author', ('lastname', 'forename', 'affiliation')), 
                  'date': ('pubdate', ('year', 'month', 'day')), 
                  'journal': {'name':'isoabbreviation'}, 
                  'grant': ('grant', ('grantid', 'agency'))
                  }
class SummarySoup(BeautifulSoup, metaclass=NCBISoupABC, **summary_kwargs): 
    """
    Parses the info of a Pubmed summary -- things like article abstract, 
    title, authors, etc. We probably get this XML using 
    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi? 
    """
    strainer = SoupStrainer('pubmedarticle')
    def __init__(self, markup='', features='lxml', builder=None, parse_only=strainer, 
                       from_encoding=None, excude_encodings=None, **kwargs): 
        super().__init__(markup, features, builder, parse_only, from_encoding, 
                         excude_encodings, **kwargs)


    def __iter__(self): 
        for summary in self.children: 
            if isinstance(summary, Tag) and summary.medlinecitation.attrs['status'] == 'MEDLINE': 
                yield summary 
        
                
    def save(self, folder): 
        with h5py.File(folder + '\\pubmed_summary.h5', 'w') as f: 
            for i, info in enumerate(zip(*[self.__getattribute__(attr) for 
                                          attr in self._data_attrs])): 
                grp = f.create_group(name=str(i)) 
                for name, data in zip(self._data_attrs, info): 
                    if isinstance(data, dict) and len(data) > 1: 
                        subgrp = grp.create_group(name)
                        for k, v in data.items(): 
                            subgrp.create_dataset(k, data=v)
                    elif isinstance(data, dict): 
                        grp.create_dataset(name=name, data=data[data.keys()[0]])
                    else: 
                        grp.create_dataset(name=name, data=data)

class ProteinSoup(BeautifulSoup, metaclass=NCBISoupABC): 
#    TODO: 
    pass 

class GeneSoup(BeautifulSoup, metaclass=NCBISoupABC): 
#    TODO: 
    pass 

class SimpleUIDList(metaclass=NCBISoupABC): 
    """
    Fake UIDSoup. 
    """
    _data_attrs = ['uid']
    
    def __init__(self, uids): 
        self.uid = iter(uids)
        
    @property
    def uid(self): 
        for i in self._uid: 
            yield i
    
    @uid.setter
    def uid(self, val): 
        self._uid = val 


