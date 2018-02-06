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
import requests 
import csv
import numpy as np
from collections import OrderedDict
from abc import ABC, abstractmethod
import pickle

from soups import SimpleUIDList


class Query(ABC): 
    """
    """
    query_key = None
    base_url = None
    fields = None
    soup_sources = None
    
    class _SearchTerms(object): 
        def __init__(self, arg): 
            raise NotImplementedError('Implement in a child class.') 
    
    def _to_url(self, base): 
        query = self.fields.copy()
        query[self.query_key] = self.search_terms.to_url()
        
        return base + ''.join(['{0}={1}&'.format(k, v) for \
                               k, v in query.items()])[:-1] 
    @abstractmethod
    def to_url(self): 
        raise NotImplementedError('Implement in a child class.') 

class KeyWordQuery(Query): 
    query_key = 'entry'
    kw_conversion = {'':'', 'title':'ti', 'journal':'journal', 
                     'affiliation':'affiliation'} 
    base_url = r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    fields = OrderedDict([('db', 'pubmed'), 
                          (query_key, '')]) 
    soup_sources = None
    
    class _SearchTerms(dict): 
        def __init__(self, arg): 
            arg = filter(lambda k: k[0] in KeyWordQuery.kw_conversion.keys(), arg.items())
            super().__init__(arg)
        
        def to_url(self): 
#            TODO: boolean logic in search 
            url = '&term='
            for k in KeyWordQuery.query_fields: 
                url += '+'.join([str(self[k])+'[{0}]'.format(KeyWordQuery.kw_conversion[k])]) + '+'
            return url[:-1]
        
        def save(self, path): 
            with open(path, 'w', newline='') as f: 
                writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_NONE)
                for k, v in self.search_terms.items(): 
                    writer.writerow([k] + v) 
        
    def __init__(self): 
        super().__init__()
    
    def load(self, items=None, path=None): 
        """
        Load query entries from a dictionary, csv or text file. 
        """
        if not items is None: 
            self.search_terms = self._SearchTerms(items) 
        elif path is None: 
            terms = {} 
            extension = path.split('.')[-1] 
            if extension == 'csv': 
                with open(path, 'r', newline='') as f: 
                    reader = csv.reader(f, quoting=csv.QUOTE_NONE) 
                    for line in reader: 
                        terms[line[0]] = line[1:]
            
                self.search_terms = self._SearchTerms(terms) 
            
            elif extension == 'txt': 
                pass 
    
    def save(self, path): 
        self.search_terms.save(path) 
    
    def to_url(self): 
        pass 

class UIDQuery(Query): 
    """
    Holds PubMed IDs, and creates URLs for downloading PubMed Data (e.g. 
    titles, abstracts, etc.) 
    """
    
    query_key = 'id'
    base_url = {'low': r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?", 
                'high': r"efetch.fcgi?"} 
    fields = OrderedDict([('db','pubmed'), #default is to search Pubmed
                          (query_key, ''), 
                          ('rettype', 'abstract'), 
                          ('retmode', 'xml'), 
                          ('version', '2.0'), 
                          ('retmax', '1000')]) 
    searchable_db = ['pubmed']
    
    class _SearchTerms(list): 
        extensions = ['txt', 'csv', 'pickle', 'pkl']
        def __init__(self, arg): 
            arg = map(str, arg.uid)
            super().__init__(arg)
        
        def to_url(self): 
            return ','.join(self)
        
        def save(self, path): 
            extension = path.split('.')[-1] 
            if extension == 'csv': 
                with open(path, 'w', newline='') as f: 
                    writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_NONE)
                    writer.writerow(self)  
            elif extension == 'txt': 
                with open(path, 'wb', newline='') as f: 
                    f.write(','.join(self).encode('utf-8'))
            elif extension in ('pickle', 'pkl'): 
                with open(path, 'wb', newline='') as f: 
                    pickle.dump(','.join(self).encode('utf-8'), f)
            else: 
                raise IOError('Incompatible file type; use one of {0}.'.format(
                                        ', '.join(self.extensions)) 
                                                                               )
            
    def __init__(self): 
        super().__init__()
     
    @property
    def database(self): 
        return self.fields['db'] 
    @database.setter
    def database(self, db): 
        assert db in self.searchable_db 
        if db == 'pubmed': 
            self.fields['rettype'] = 'abstract' 
        self.fields['db'] = db
    
    @property
    def ret_max(self): 
        return self._ret_max
    @ret_max.setter
    def ret_max(self, val): 
#        in case this is passed in directly from an XML parser 
        val = int(val)
        if val >= 1e5: #NCBI can't retreive more than 1e5 UIDs
            val = 1e5
        self.fields['retmax'] = str(val)
        
    
    def load(self, has_uids=None, path=None): 
        """
        Instantiates a _SearchTerms object directly from the passed-in has_uids
        instance or loads UIDs from file and converts them to _SearchTerms 
        object. 
        
        Parameters
        ------------
        has_uids : SimpleUIDList
            Anything that has a 'uid' attribute. This is parsed into a list 
            of integers. 
        
        path: str
            Path to file. 
            
        """
        if not has_uids is None: 
            self.search_terms = self._SearchTerms(has_uids) 
        elif not path is None: 
            terms = [] 
            extension = path.split('.')[-1] 
            with open(path, 'rb') as f: 
                if extension == 'csv': 
                    reader = csv.reader(f, quoting=csv.QUOTE_NONE) 
                    for line in reader: 
                        terms.append(line) 
            
                elif extension == 'txt': 
                    terms = f.read().decode('utf-8').replace(' ', '').split(',')
            
                elif extension in ('pickle', 'pkl'): 
                    p = pickle.load(f, encoding='utf-8')
                    terms = p.split(',')
                    
            terms = SimpleUIDList(filter(lambda x: x.isdigit(), 
                                         map(str, np.concatenate(terms))))
            self.search_terms = self._SearchTerms(terms) 
    
    def save(self, path): 
        self.search_terms.save(path)
    
    def to_url(self): 
        if len(self.fields['id']) >= 200: 
            base = self.base_url['high'] 
            return self._to_url(base), requests.get
        else: 
            base = self.base_url['low'] 
            return self._to_url(base), requests.post