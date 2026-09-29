"""模拟搜索接口，检查请求、结果处理和失败回退。"""

import io
import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from src.config import AgentConfig
from src.tavily_search import SEARCH_URL, TavilySearch


class TavilySearchTests(unittest.TestCase):
    def test_search_results(self):
        data = {"results": [{"title": "标题", "url": "https://example.com", "content": "中" * 900, "score": 0.9}]}
        response = io.BytesIO(json.dumps(data).encode())
        with patch("src.tavily_search.urlopen", return_value=response) as request_mock, patch("builtins.print"):
            results = TavilySearch("test-key").search("关键词", max_results=3)
        request = request_mock.call_args.args[0]
        self.assertEqual(request.full_url, SEARCH_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(json.loads(request.data), {
            "query": "关键词", "max_results": 3, "search_depth": "basic",
            "include_answer": False, "include_raw_content": False,
        })
        self.assertEqual(results[0].title, "标题")
        self.assertEqual(results[0].url, "https://example.com")
        self.assertEqual(results[0].content, "中" * 800)
        self.assertEqual(results[0].score, 0.9)

    def test_empty_and_invalid_response(self):
        for body in (b'{"results": []}', b'{}', b'not json'):
            with self.subTest(body=body), patch("src.tavily_search.urlopen", return_value=io.BytesIO(body)), patch("builtins.print"):
                self.assertEqual(TavilySearch("test-key").search("test"), [])

    def test_request_failure(self):
        for error in (HTTPError(SEARCH_URL, 401, "Unauthorized", {}, None), URLError("offline"), TimeoutError()):
            with self.subTest(error=error), patch("src.tavily_search.urlopen", side_effect=error), patch("builtins.print"):
                self.assertEqual(TavilySearch("test-key").search("test"), [])

    def test_api_key(self):
        config = AgentConfig(api_key="model-key", tavily_api_key="search-key")
        with patch("src.tavily_search.get_config", return_value=config):
            self.assertEqual(TavilySearch().api_key, "search-key")
        with self.assertRaises(ValueError):
            TavilySearch(" ")


if __name__ == "__main__":
    unittest.main()
