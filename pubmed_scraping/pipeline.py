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
from requests.exceptions import ConnectionError
import time

import query
import soups 

class Pipeline(object): 
    def __init__(self, kw, api_key=None): 
        self.api_key = api_key
        self.kw_query = query.KeyWordQuery(retstart=0, api_key=api_key)
        self.uid_query = query.UIDQuery(retstart=0, api_key=api_key) 
        if isinstance(kw, str): 
            self.kw_query.load(path=kw)
        else: 
            self.kw_query.load(terms=kw) 
    
    @staticmethod
    def _request(query, Soup): 
        raw = None
        with query.as_request() as req: 
            if not req.status_code == 200: 
                print (req.status_code)
                print
                raise ConnectionError(response=req, request=req.request)
            else: 
                raw = req.text
        return Soup(raw) 
    
    @staticmethod
    def _n_or_max(n, max_): 
        if n >= max_:
            return max_
        else: 
            return n 
    
    def request(self, n, save_folder=''): 
        """
        Parameters
        --------------
        n: int
            Maximum number of Pubmed article summaries to retrieve. 

        save_folder: str
            Where to save results as an h5 file. If we don't want to save the 
            results to disk, enter default argument. 
        """
        self.kw_query.ret_max = self._n_or_max(n, query.UID_RETMAX)
        self.uid_query.ret_max = self._n_or_max(n, query.SUMMARY_RETMAX)
        n = int(n)
        
        prev_time = time.monotonic()
        try: 
            for i in range((n-1)//query.UID_RETMAX + 1): 
                print('i: ', i, ' elapsed: ', time.monotonic() - prev_time)
                if not time.monotonic() - prev_time > 0.334: 
    #                    NCBI cannot accept more than three requests per second 
                        time.sleep(0.334 - time.monotonic() + prev_time)
                prev_time = time.monotonic()
                self.kw_query.ret_start = i*self.kw_query.ret_max
                uid_soup = self._request(self.kw_query, soups.UIDSoup)
                if save_folder: 
                    uid_soup.save(save_folder) 
                
                self.uid_query.load(terms=uid_soup)
                for j in range((self.kw_query.ret_max-1)//query.SUMMARY_RETMAX + 1): 
                    print('j: ', j, ' elapsed: ', time.monotonic() - prev_time)
                    if not time.monotonic() - prev_time > 0.334: 
    #                    NCBI cannot accept more than three requests per second 
                        time.sleep(0.334 - time.monotonic() + prev_time)
                    prev_time = time.monotonic()
                    self.uid_query.ret_start = j*self.uid_query.ret_max
                    summary_soup = self._request(self.uid_query, soups.SummarySoup)
                    if save_folder: 
                        summary_soup.save(save_folder)
        except ConnectionError as e: 
            print(e.response.reason)
            raise ConnectionError(response=e.response, request=e.request)
        
            
            
            