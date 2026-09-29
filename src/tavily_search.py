"""Tavily 搜索：返回标题、链接、摘要和相关性分数。"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.config import get_config

SEARCH_URL = "https://api.tavily.com/search"


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float


class TavilySearch:
    def __init__(self, api_key: str | None = None):
        """默认读取已有配置，也可直接传入 Tavily API Key。"""
        self.api_key = api_key if api_key is not None else get_config().tavily_api_key.get_secret_value()
        if not self.api_key.strip():
            raise ValueError("缺少 TAVILY_API_KEY，请在 src/.env 中配置")

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """同步搜索，默认最多 5 条；摘要截取前 800 字，失败返回空列表。"""
        print(f"[TavilySearch] 搜索：{query}")
        try:
            request = Request(
                SEARCH_URL,
                data=json.dumps({
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_raw_content": False,
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
            results = []
            for item in data["results"]:
                results.append(SearchResult(
                    title=item["title"],
                    url=item["url"],
                    content=(item["content"] or "")[:800],
                    score=float(item["score"]),
                ))
            print(f"[TavilySearch] 获取到 {len(results)} 条结果")
            return results
        except HTTPError as error:
            print(f"[TavilySearch] 请求失败：HTTP {error.code}")
        except (OSError, ValueError, KeyError, TypeError):
            print("[TavilySearch] 搜索失败：网络异常或返回数据无效")
        return []
