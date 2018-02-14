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

SUMMARY_RETMAX = 500
UID_RETMAX = int(1e5)

class Query(ABC): 
    """
    """
    query_key = None
    base_url = None
    fields = None
    
    class _SearchTerms(object): 
        def __init__(self, arg): 
            """
            Converts the arg into appropriate format. Should take iterable 
            or Soup object from which search terms e.g. Pubmed IDs can be 
            parsed. 
            """
            raise NotImplementedError('Implement in a child class.') 
            
    def __init__(self, retstart=0, api_key=None): 
        self.fields['retstart'] = retstart
        self.api_key = api_key
    
    def _load_h5(self, path): 
        raise NotImplementedError('Not implemented.')  
            
    def _save_h5(self, path): 
        raise NotImplementedError('Not implemented.')  
    
    @property
    def ret_start(self): 
        return int(self.fields['retstart'])
    @ret_start.setter
    def ret_start(self, val): 
        if isinstance(val, bytes): 
            self.fields['retstart'] = val.decode('utf-8')
        else: 
            self.fields['retstart'] = str(val)
    
    @property
    @abstractmethod
    def ret_max(self): 
        pass
    @ret_max.setter
    def ret_max(self, val): 
        pass
    
    def to_url(self): 
        url = self.base_url + self.search_terms.to_url() + '&' \
              + '&'.join(['{0}={1}'.format(k, v) for k, v in self.fields.items()])
        
        if not self.api_key is None: 
            url += '&api_key={0}'.format(self.api_key)
        
        return url, self.req_function
    
    @property
    def as_request(self): 
        fields = self.fields.copy() 
        fields.update(self.search_terms.to_dict()) 
        if not self.api_key is None: 
            fields.update({'api_key': self.api_key})
        return lambda: self.req_function(self.base_url, fields)
    
    def load(self, terms=None, path=None): 
        """
        Instantiates a _SearchTerms object directly from the passed-in has_uids
        instance or loads UIDs from file and converts them to _SearchTerms 
        object. 
        
        Parameters
        ------------
        has_uids : SimpleUIDList
            Anything that has a 'uid' attribute that, upon calling its next 
            method, generates a utf-8-encoded bytes object. 
            
        
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
                        read = f.read()
                    elif extension in ('pickle', 'pkl'): 
                        read = pickle.load(f, encoding='bytes')
                        
                result = [line.split(b',') for line in read.split(b'\n')] 
            
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
                                    ', '.join(self.extensions)))
    

class KeyWordQuery(Query): 
    base_url = r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
    fields = OrderedDict([('db', 'pubmed'), 
                          ('retmax', str(UID_RETMAX))]) 

    class _SearchTerms(dict): 
        """
        arg : list 
        [keyword for advanced search, seach words]
        """
        query_key = 'term'
        kw_conversion = {'':'', None:'', ' ':'', 'title':'ti', 'author':'au', 
                         'journal':'journal', 'affiliation':'affiliation', 
                         'language': 'language'} 
        def __init__(self, arg): 
#            Everything in SearchTerms is string not bytes. Conversion from bytes 
#            is done in __init__. 
            arg = {li[0].decode('utf-8'): [i.decode('utf-8') for i in li[1:]] 
                   for li in arg if li[0].decode('utf-8') 
                   in ('mindate', 'maxdate', *self.kw_conversion.keys())}
            
            super().__init__(arg) 
            self.baseurl = '&datetype=pdat'
            if 'mindate' in self.keys(): 
                self.mindate = self['mindate'][0]
                del self['mindate'] 
            else: 
                self.mindate = '1800'
            
            if 'maxdate' in self.keys(): 
                self.maxdate = self['maxdate'][0]
                del self['maxdate'] 
            else: 
                self.maxdate = '2100'
            self.baseurl += '&mindate={0}&maxdate={1}'.format(self.mindate, 
                                                              self.maxdate)
            
        @property
        def term(self): 
#            TODO: boolean logic in search 
            url = ''
            for k, v in self.items(): 
                url += ''.join(['{0}[{1}]'.format(term, self.kw_conversion[k]) for term in v])
            return url
        
        def to_url(self): 
            return self.query_key + "=" + self.term + self.baseurl
            
        
        def to_dict(self): 
            return OrderedDict([('term', self.term), 
                                ('datetype', 'pdat'), 
                                ('mindate', self.mindate), 
                                ('maxdate', self.maxdate)])
    
        @property
        def saveable_format(self): 
            li = [k + ',' + ','.join(v) if not k in (None, '') else 
                  ' ,' + ','.join(v) for k, v in self.items()]
            li.append('mindate,{0}'.format(self.mindate))
            li.append('maxdate,{0}'.format(self.maxdate))
            
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
                li.append([grp.name] + list(val))
        return terms 
    
    @property
    def ret_max(self): 
        return int(self.fields['retmax'])
    @ret_max.setter
    def ret_max(self, val): 
#        in case this is passed in directly from an XML parser 
        val = int(val)
        if val >= int(UID_RETMAX): #NCBI can't retreive more than 1e5 UIDs
            val = int(UID_RETMAX)
        self.fields['retmax'] = str(val)
    
    @property    
    def req_function(self): 
        return requests.get


class UIDQuery(Query): 
    """
    Holds PubMed IDs, and creates URLs for downloading PubMed Data (e.g. 
    titles, abstracts, etc.) 
    """
    base_url = r"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
    fields = OrderedDict([('db','pubmed'), #default is to search Pubmed
                          ('rettype', 'abstract'), 
                          ('retmode', 'xml'), 
                          ('version', '2.0'), 
                          ('retmax', str(SUMMARY_RETMAX)), 
                          ('retstart', '0'), ]) 
    searchable_db = ['pubmed']
    
    class _SearchTerms(list): 
        query_key = 'id'
        def __init__(self, terms): 
            try: 
                terms = terms.uid
            except AttributeError: 
                pass 
            terms = filter(lambda x: x.isdigit(), 
                           map(lambda x: x.decode('utf-8').replace(' ', ''), 
                               terms))

            super().__init__(terms)
        
        def to_url(self): 
            return ','.join(self) 
        
        @property
        def saveable_format(self): 
            return ','.join(self).encode('utf-8')
        
        def to_dict(self): 
            return OrderedDict([(self.query_key, self.to_url())])
    
    def _save_h5(self, path): 
        with h5py.File(path, mode='w') as f: 
            fields = self.fields.copy() 
            for k, v in fields.items(): 
                f.attrs[k] = v.encode('utf-8')
            f.create_dataset(name='uid',data=self.search_terms.saveable_format) 
            
    def _load_h5(self, path): 
        terms = [] 
        with h5py.File(path, 'r') as f: 
            for k, v in f.attrs.items(): 
                if k in self.fields.keys(): 
                    self.fields[k] = v
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
        return int(self.fields['retmax'])
    @ret_max.setter
    def ret_max(self, val): 
#        in case this is passed in directly from an XML parser 
        val = int(val)
        if val >= int(SUMMARY_RETMAX): #NCBI can't retreive more than 1e5 UIDs
            val = int(SUMMARY_RETMAX)
        self.fields['retmax'] = str(val)
    
    @property
    def req_function(self): 
        if self.ret_max >= 200: 
            return requests.post
        else: 
            return requests.get