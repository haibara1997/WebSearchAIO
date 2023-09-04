#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fake_useragent import UserAgent

from ..config import PROXY, TIMEOUT
from ..engine import SearchEngine

ua = UserAgent()
FAKE_USER_AGENT = ua.edge


class Baidu(SearchEngine):
    """Searches bing.com"""

    def __init__(self, proxy=PROXY, timeout=TIMEOUT):
        super(Baidu, self).__init__(proxy, timeout)
        self._base_url = u'https://www.bing.com'
        self.set_headers({'User-Agent': FAKE_USER_AGENT})

    def _selectors(self, element):
        # 'links': 'ol#b_results > li.b_algo', -> 'links': 'li.b_algo',
        # 没有指定上层的ol元素，ol#b_results的选择器可能是多余的。在答案中出现聚合搜索的时候还会出现问题。
        """Returns the appropriate CSS selector."""
        selectors = {
            'url': 'a[href]',
            'title': 'h2',
            'text': 'p',
            'links': 'li.b_algo',
            'next': 'a.sb_pagN'
        }
        return selectors[element]

    def _first_page(self):
        """Returns the initial page and query."""
        self._get_page(self._base_url)
        url = u'{}/search?q={}&qs=n&form=QBRE'.format(self._base_url, self._query)
        return {'url': url, 'data': None}

    def _next_page(self, tags):
        """Returns the next page URL and post data (if any)"""
        selector = self._selectors('next')
        next_page = self._get_tag_item(tags.select_one(selector), 'href')
        url = None
        if next_page:
            url = (self._base_url + next_page)
        return {'url': url, 'data': None}
