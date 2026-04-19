import time
import os
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.logger import get_logger, log_tool_call

load_dotenv()

logger = get_logger("tools.niuke")

BASE_URL = "https://www.nowcoder.com"
REQUEST_INTERVAL = 1.0
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
NOWCODER_COOKIE = os.getenv("NOWCODER_COOKIE", "")


def _get_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.nowcoder.com/",
    }
    if NOWCODER_COOKIE:
        headers["Cookie"] = NOWCODER_COOKIE
    return headers


def search_interview_exps(position: str, count: int, company: str = None) -> List[Dict[str, str]]:
    assert 1 <= count <= 50, "count must be between 1 and 50"
    assert position, "position is required"

    start_time = time.time()
    try:
        search_url = f"{BASE_URL}/discuss"
        params = {
            "type": 2,
            "order": 0,
            "tag": position,
        }
        if company:
            params["company"] = company

        resp = requests.get(
            search_url,
            params=params,
            headers=_get_headers(),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            allow_redirects=True,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()

        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            title = link.get_text(strip=True)

            if "/discuss/" in href and href not in seen:
                seen.add(href)
                if title and len(title) > 10:
                    full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    results.append({
                        "url": full_url,
                        "title": title[:100],
                        "date": "",
                    })
                    if len(results) >= count:
                        break

        time.sleep(REQUEST_INTERVAL)

        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "search_interview_exps", duration_ms, "success")
        return results[:count]

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "search_interview_exps", duration_ms, "failed", str(e))
        raise


def search_interview_exps_by_urls(urls: List[str]) -> List[Dict[str, str]]:
    return [{"url": url, "title": "", "date": ""} for url in urls]


def fetch_interview_content(url: str) -> Dict[str, Any]:
    start_time = time.time()
    try:
        resp = requests.get(
            url,
            headers=_get_headers(),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        title_tag = soup.find("h1") or soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""

        content_div = (
            soup.find("div", class_="post-topic-des")
            or soup.find("div", class_="rich-text")
            or soup.find("div", {"data-see-more": "true"})
        )

        if not content_div:
            divs = soup.find_all("div", class_=True)
            for div in divs:
                text = div.get_text(strip=True)
                if len(text) > 500:
                    content_div = div
                    break

        content_text = content_div.get_text(strip=True) if content_div else ""

        questions = []
        if content_div:
            for p in content_div.find_all(["p", "li"]):
                text = p.get_text(strip=True)
                if "?" in text or "？" in text or "面试" in text:
                    questions.append(text)

        author_tag = (
            soup.find("span", class_="author-name")
            or soup.find("a", class_="user-name")
            or soup.find("div", class_="author-info")
        )
        author = author_tag.get_text(strip=True) if author_tag else None

        date_tag = soup.find("span", class_="post-time") or soup.find("div", class_="post-time")
        date = date_tag.get_text(strip=True) if date_tag else None

        time.sleep(REQUEST_INTERVAL)

        result = {
            "title": title_text,
            "content": content_text,
            "questions": questions,
            "author": author,
            "date": date,
        }

        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "fetch_interview_content", duration_ms, "success")
        return result

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "fetch_interview_content", duration_ms, "failed", str(e))
        return {"error": str(e), "url": url}
