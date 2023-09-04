# -*- coding: utf-8 -*-

import asyncio
import os
import re
import socket
from collections import namedtuple
from datetime import datetime

from fake_useragent import UserAgent
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from search_engines.config import TIMEOUT, PROXY
from search_engines.utils import *

ua = UserAgent()
FAKE_USER_AGENT = ua.edge

def get_local_ip() -> str|None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except socket.error as e:
        print(f"Oops! Something went wrong: {e}")
    return None


def is_valid_url(url: str) -> bool:
    pattern = r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)$"
    return bool(re.match(pattern, url))


class PersistentBrowser(object):

    def __init__(self, timeout=TIMEOUT, proxy=PROXY):
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, 'libs/stealth.min.js')

        self.browser = None
        self.page = None
        self.timeout = timeout
        self.proxy = self._set_proxy(proxy)
        self.user_Agent = FAKE_USER_AGENT
        with open(file_path, 'r') as f:
            self.js = f.read()
        self.response = namedtuple('response', ['http', 'html'])

    async def start(self):
        if self.browser is None:
            playwright = await async_playwright().start()
            chromium = playwright.chromium
            self.browser = await chromium.launch(
                proxy={'server': self.proxy} if self.proxy else None,
                headless=True
            )

    async def stop(self):
        if self.browser is not None:
            await self.browser.close()
            self.browser = None
            self.page = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    @staticmethod
    def _set_proxy(proxy:str) -> str|None:
        """Returns HTTP or SOCKS proxies dictionary."""
        if proxy is not None:
            if not is_valid_url(proxy):
                raise ValueError('Invalid proxy format!')
            return proxy
        return None

    @staticmethod
    def _quote(url: str) -> str:
        """URL-encodes URLs."""
        if decode_bytes(unquote_url(url)) == decode_bytes(url):
            url = quote_url(url)
        print(url)
        return url

    async def get_raw_html(self, request_url: str) -> namedtuple:
        request_url = self._quote(request_url)

        if not is_valid_url(request_url):
            return self.response(http=400, html='Invalid URL')

        if not self.browser:
            raise RuntimeError("Browser context is not initialized")

        context = await self.browser.new_context(user_agent=self.user_Agent, locale='zh-CN')
        try:
            page = await context.new_page()
            # await page.add_init_script(self.js)
            await stealth_async(page)
            response = await page.goto(request_url)
            raw_html = await page.content()
            await page.screenshot(path=f'screenshot_{datetime.now().strftime("%Y%m%d%H%M%S")}.png')
            return self.response(http=response.status, html=raw_html)
        finally:
            await context.close()

    async def search_main_page(self, base_url: str, query: str) -> namedtuple:
        if not self.browser:
            raise RuntimeError("Browser context is not initialized")

        context = await self.browser.new_context(user_agent=self.user_Agent, locale='zh-CN')

        try:
            page = await context.new_page()
            await page.add_init_script(self.js)
            response = await page.goto(base_url)
            await page.get_by_role("searchbox").fill(query)
            await page.get_by_role("searchbox").press('Enter')
            await page.wait_for_load_state(state='load', timeout=500)
            raw_html = await page.content()
            page.screenshot(path=f'screenshot_{datetime.now().strftime("%Y%m%d%H%M%S")}.png')

            response = self.response(http=response.status, html=raw_html)
            return response

        finally:
            await context.close()


if __name__ == "__main__":
    async def get_html(request_url: str):
        async with PersistentBrowser() as pbrowser:
            return await pbrowser.get_raw_html(request_url)

    url = 'https://bot.sannysoft.com/'
    html = asyncio.run(get_html(url))
    print(html)
