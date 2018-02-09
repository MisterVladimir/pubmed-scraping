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

import unittest

from py3_modules.pubmed_scraping.pubmed_scraping import query


#https://stackoverflow.com/questions/11399148/how-to-mock-an-http-request-in-a-unit-testing-scenario-in-python

class KeyWordQueryTest(unittest.TestCase): 
    def setUp(self):
        self.test_load_list = [['','shteyn']]
        self.query = query.KeyWordQuery() 
        self.query.load(terms=self.test_load_list)

    def test_kw_load(self): 
        self.assertIsInstance(self.query.search_terms, dict)

    def test_kw_terms(self): 
        saveable = self.query.search_terms.saveable_format
        self.assertEqual(saveable, ' ,shteyn'.encode('utf-8'))
        url = self.query.search_terms.to_url() 
        self.assertIsInstance(url, str)
    
    def test_make_whole_url(self): 
        url, method = self.query.to_url() 
        self.assertIsInstance(url, str) 
        self.assertIs(method, get) 


class UIDQueryTest(unittest.TestCase):
    def setUp(self):
        self.test_uid = [b'28852740',b'29350911']
        self.query = query.UIDQuery() 
        self.query.load(terms=self.test_uid)

    def test_kw_load(self): 
        self.assertIsInstance(self.query.search_terms, list)

    def test_uid_terms(self): 
        saveable = self.query.search_terms.saveable_format
        print('saveable: {0}'.format(saveable))
        self.assertEqual(saveable, '28852740,29350911'.encode('utf-8'))
        url = self.query.search_terms.to_url() 
        self.assertIsInstance(url, str)
    
    def test_make_whole_url(self): 
        url, method = self.query.to_url() 
        print('url is {0}'.format(url))
        self.assertIsInstance(url, str) 
        
if __name__ == '__main__': 
    unittest.main() 