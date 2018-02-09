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

from query import KeyWordQuery, UIDQuery
from soups import UIDSoup, SummarySoup

def request(search_terms, type_): 
    """
    Parameters
    -------------
    
    """
    d = {'keyword': (KeyWordQuery, UIDSoup), 
         'uids': (UIDQuery, SummarySoup)} 
    Query, Soup = d[type_]
    
    query = Query()
    if isinstance(search_terms, str): 
        query.load(path=search_terms)
    else: 
        query.load(terms=search_terms) 
    
    url, req_function = query.to_url()
    raw = None
    with req_function(url) as req: 
        raw = req.text
    
    return Soup(raw, 'lxml') 
        

def save(saveable, save_folder): 
    """
    Parameters
    ------------
    soup : 
        raw text received by 
        
    attrs : 
    """
    try: 
        saveable.save(folder=save_folder) 
    except AttributeError: 
        print('{0} does not have a "save" method.'.format(str(saveable)))


if __name__ == '__main__': 
#    kw = input('Enter search terms: ') 
    terms=[[' ', 'shteyn']]
    uid_soup = request(terms, 'keyword')
    summary_soup = request(uid_soup, 'uids')
    save(uid_soup, r"C:\Users\v\Anaconda3\envs\py3\py3_modules\pubmed_scraping\test\test_data")
    save(summary_soup, r"C:\Users\v\Anaconda3\envs\py3\py3_modules\pubmed_scraping\test\test_data")