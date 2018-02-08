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
import requests 
import numpy as np
from collections import OrderedDict
from abc import ABC, abstractmethod
import pickle
import h5py

class Query(ABC): 
    """
    """
    query_key = None
    base_url = None
    fields = None
    soup_sources = None
    
    class _SearchTerms(object): 
        def __init__(self, arg): 
            """
            Converts the arg into appropriate format. Should take iterable 
            or Soup object from which search terms e.g. Pubmed IDs can be 
            parsed. 
            """
            raise NotImplementedError('Implement in a child class.') 
    
    def _load_h5(self, path): 
        raise NotImplementedError('Not implemented.')  
            
    def _save_h5(self, path): 
        raise NotImplementedError('Not implemented.')  
    
    def _to_url(self, base): 
        query = self.fields
        query[self.query_key] = self.search_terms.to_url()
        
        url = base + '&'.join(['{0}={1}'.format(k, v) for k, v in query.items()])
        return url
    
    @abstractmethod
    def to_url(self): 
        raise NotImplementedError('Implement in a child class.') 
    
    def load(self, terms=None, path=None): 
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
        if not terms is None: 
            self.search_terms = self._SearchTerms(terms) 
        elif not path is None: 
            extension = path.split('.')[-1]
            if extension in ('h5', 'hd5', 'hf5'): 
                result = self._load_h5(path)
                    
            elif extension in ('txt', 'pickle', 'pkl'): 
                read = None 
                with open(path, 'rb') as f: 
                    if extension == 'txt': 
                        read = f.read().decode('utf-8')
                    elif extension in ('pickle', 'pkl'): 
                        read = pickle.load(f, encoding='utf-8')
                        
                result = [line.split(',') for line in read.split('\n')] 
            
            self.search_terms = self._SearchTerms(result) 
    
    def save(self, path): 
#        TODO: save to file from which UIDs were loaded 
        extension = path.split('.')[-1] 
        if extension == 'txt': 
            with open(path, 'wb') as f: 
                f.write(self.search_terms.saveable_format)
        elif extension in ('pickle', 'pkl'): 
            with open(path, 'wb') as f: 
                pickle.dump(self.search_terms.saveable_format, f)
        elif extension in ('h5', 'hd5', 'hf5'): 
            self._save_h5(path) 

        else: 
            raise IOError('Incompatible file type; use one of {0}.'.format(
                                    ', '.join(self.extensions)) 
                                                                           )
    

class KeyWordQuery(Query): 
    query_key = 'term'
    base_url = r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
    fields = OrderedDict([('db', 'pubmed'), 
                          (query_key, '')]) 
    soup_sources = None
    
    class _SearchTerms(dict): 
        kw_conversion = {'':'', ' ':'', 'title':'ti', 'journal':'journal', 
                         'affiliation':'affiliation'} 
        def __init__(self, arg): 
            arg = {li[0]: li[1:] for li in arg if \
                                            li[0] in self.kw_conversion.keys()}
            super().__init__(arg)
        
        def to_url(self): 
#            TODO: boolean logic in search 
            url = ''
            for k, v in self.items(): 
                url += '+'.join([self[v]+'[{0}]'.format(self.kw_conversion[k])])
            return url
        
        @property
        def saveable_format(self): 
            li = [k + ',' + ','.join(v) for k, v in self.items()]
            return '\n'.join(li).encode('utf-8')
    
    def _save_h5(self, path): 
        with h5py.File(path, mode='w') as f: 
            for k, v in self.fields.items(): 
                f.attrs[k] = v.encode('utf-8')
            for grp, val in f.items(): 
                f.create_dataset(grp.name, np.array(val, dtype=bytes))
            
    def _load_h5(self, path): 
        terms = [] 
        with h5py.File(path, 'r') as f: 
            for k, v in f.attrs.items(): 
                if k in self.fields.keys(): 
                    self.fields[k] = v.decode('utf-8')
            li = []
            for grp, val in f.items(): 
                li.append([grp.name] + list(map(lambda x: x.decode('utf-8'), 
                                                val)))
        return terms 
    
    def to_url(self): 
        base = self.base_url
        req_function = requests.get
        
        return self._to_url(base), req_function


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
        def __init__(self, terms): 
            try: 
                terms = terms.uid
            except AttributeError: 
                pass 
            terms = filter(lambda x: x.isdigit(), 
                           map(lambda x: str(x).replace(' ', ''), 
                               np.concatenate(terms)))

            super().__init__(terms)
        
        def to_url(self): 
            return ','.join(self) 
        
        @property
        def saveable_format(self): 
            return ','.join(self).encode('utf-8')
    
    def _save_h5(self, path): 
        with h5py.File(path, mode='w') as f: 
            fields = self.fields.copy() 
            del fields[self.query_key]
            for k, v in fields.items(): 
                f.attrs[k] = v.encode('utf-8')
            f.create_dataset('uid',data=np.array(self.search_terms, dtype=int)) 
            
    def _load_h5(self, path): 
        terms = [] 
        with h5py.File(path, 'r') as f: 
            for k, v in f.attrs.items(): 
                if k in self.fields.keys(): 
                    self.fields[k] = v.decode('utf-8')
            terms = f['uid']
        return terms 
    
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
    
    def to_url(self): 
        if len(self.fields['id']) >= 200: 
            base = self.base_url['high'] 
            req_function = requests.get
        else: 
            base = self.base_url['low'] 
            req_function = requests.post

        return self._to_url(base), req_function