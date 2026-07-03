# -*- coding: utf-8 -*-
"""
数据采集模块 - 多源招标信息爬虫
支持: 广东省招标投标监管网、广州公共资源交易中心、中国招标投标公共服务平台
"""

import requests
import json
import time
import re
import logging
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from config import SOURCES, CRAWLER_CONFIG, ALL_KEYWORDS, REGIONS, INDUSTRY_CHAIN_MAP

logger = logging.getLogger(__name__)


class BaseScraper:
    """爬虫基类"""

    def __init__(self, source_key: str):
        self.source_key = source_key
        self.source_config = SOURCES[source_key]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CRAWLER_CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.delay = CRAWLER_CONFIG["request_delay"]
        self.timeout = CRAWLER_CONFIG["timeout"]
        self.max_retries = CRAWLER_CONFIG["max_retries"]

    def _request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """带重试的请求"""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.delay)
                kwargs.setdefault("timeout", self.timeout)
                resp = self.session.request(method, url, **kwargs)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp
            except Exception as e:
                logger.warning(f"请求失败(第{attempt+1}次): {url} - {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.delay * (attempt + 1))

    def _make_notice_id(self, title: str, date: str, source: str) -> str:
        """生成唯一公告ID"""
        raw = f"{source}_{title}_{date}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]

    def _detect_region(self, text: str) -> str:
        """从文本中检测地区"""
        for code, name in REGIONS.items():
            if name in text:
                return name
        return "广东省"

    def search(self, keyword: str, days: int = 7) -> list:
        """搜索接口(子类实现)"""
        raise NotImplementedError

    def close(self):
        self.session.close()


class GdZbtbScraper(BaseScraper):
    """广东省招标投标监管网爬虫"""

    def __init__(self):
        super().__init__("gd_zbtb")

    def search(self, keyword: str, days: int = 7) -> list:
        """通过搜索接口获取公告"""
        results = []
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # 尝试API搜索接口
        api_url = "https://www.gdzwfw.gov.cn/ztbjg-portal/api/xxgggs/getXxgggsList"
        for page in range(1, CRAWLER_CONFIG["max_pages"] + 1):
            try:
                payload = {
                    "pageNo": page,
                    "pageSize": 20,
                    "title": keyword,
                    "startDate": cutoff_date,
                    "endDate": datetime.now().strftime("%Y-%m-%d"),
                }
                resp = self._request(api_url, method="POST", json=payload,
                                     headers={"Content-Type": "application/json"})
                data = resp.json()
                items = data.get("data", {}).get("list", [])
                if not items:
                    break
                for item in items:
                    notice = self._parse_item(item, keyword)
                    if notice:
                        results.append(notice)
                if len(items) < 20:
                    break
            except Exception as e:
                logger.debug(f"API搜索失败, 尝试备用方式: {e}")
                break

        return results

    def _parse_item(self, item: dict, keyword: str) -> dict:
        try:
            title = item.get("title", "")
            pub_date = item.get("publishDate", item.get("publishTime", ""))
            notice_id = self._make_notice_id(title, str(pub_date), self.source_key)
            return {
                "notice_id": notice_id,
                "title": title,
                "source": self.source_key,
                "source_url": item.get("url", ""),
                "notice_type": item.get("noticeType", "招标公告"),
                "project_name": title,
                "project_code": item.get("projectCode", ""),
                "region": self._detect_region(title + str(item.get("region", ""))),
                "budget": self._parse_budget(item.get("budget", item.get("amount", ""))),
                "publish_date": str(pub_date)[:10] if pub_date else datetime.now().strftime("%Y-%m-%d"),
                "deadline_date": item.get("deadline", ""),
                "tenderer": item.get("tenderer", item.get("tenderee", "")),
                "agency": item.get("agency", ""),
                "winner": item.get("winner", ""),
                "win_amount": self._parse_budget(item.get("winAmount", "")),
                "content": item.get("content", item.get("summary", "")),
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.debug(f"解析条目失败: {e}")
            return None

    def _parse_budget(self, val) -> float:
        if not val:
            return 0
        if isinstance(val, (int, float)):
            return float(val) / 10000  # 元转万元
        s = str(val)
        nums = re.findall(r"[\d.]+", s)
        if nums:
            amount = float(nums[0])
            if "亿" in s:
                amount *= 10000
            elif "万" not in s:
                amount /= 10000
            return amount
        return 0


class GzGgzyScraper(BaseScraper):
    """广州公共资源交易中心爬虫 (HTML解析)"""

    def __init__(self):
        super().__init__("gz_ggzy")

    def search(self, keyword: str, days: int = 7) -> list:
        results = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for page in range(1, CRAWLER_CONFIG["max_pages"] + 1):
            try:
                url = f"{self.source_config['search_url']}?{page}.jhtml" if page > 1 else self.source_config['search_url']
                resp = self._request(url)
                soup = BeautifulSoup(resp.text, "lxml")

                items = soup.select("ul.news-list li, table tr, .list-content li, .zbgg-list li")
                if not items:
                    # 尝试通用选择器
                    items = soup.find_all("a", href=re.compile(r"/jyywjsgcfwjzzbgg/\d+\.jhtml"))

                found_any = False
                for item in items:
                    link = item if item.name == "a" else item.find("a", href=re.compile(r"\d+\.jhtml"))
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    if not title:
                        continue

                    # 日期提取
                    date_text = ""
                    date_span = item.find(text=re.compile(r"\d{4}-\d{2}-\d{2}"))
                    if date_span:
                        date_text = date_span.strip()
                    else:
                        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", str(item))
                        if date_match:
                            date_text = date_match.group(1)

                    if date_text:
                        try:
                            item_date = datetime.strptime(date_text, "%Y-%m-%d")
                            if item_date < cutoff_date:
                                continue
                        except ValueError:
                            pass

                    # 关键词过滤
                    if keyword.lower() not in title.lower():
                        continue

                    href = link.get("href", "")
                    full_url = urljoin(self.source_config["base_url"], href)

                    notice_id = self._make_notice_id(title, date_text, self.source_key)
                    results.append({
                        "notice_id": notice_id,
                        "title": title,
                        "source": self.source_key,
                        "source_url": full_url,
                        "notice_type": "招标公告",
                        "project_name": title,
                        "region": self._detect_region(title),
                        "budget": 0,
                        "publish_date": date_text or datetime.now().strftime("%Y-%m-%d"),
                        "deadline_date": "",
                        "tenderer": "",
                        "agency": "",
                        "winner": "",
                        "win_amount": 0,
                        "content": "",
                        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    found_any = True

                if not found_any:
                    break
                if len(items) < 10:
                    break

            except Exception as e:
                logger.warning(f"广州公共资源交易中心第{page}页解析失败: {e}")
                break

        return results


class NationalCebScraper(BaseScraper):
    """中国招标投标公共服务平台爬虫"""

    def __init__(self):
        super().__init__("national")

    def search(self, keyword: str, days: int = 7) -> list:
        results = []
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        api_url = "http://www.cebpubservice.com/ctpsp_iiss/acceptdefault/acceptinfo/acceptinfoserachbypage.do"
        for page in range(1, min(CRAWLER_CONFIG["max_pages"] + 1, 10)):
            try:
                payload = {
                    "pageNo": page,
                    "pageSize": 20,
                    "keyword": keyword,
                    "province": "440000",  # 广东省
                    "startDate": cutoff_date,
                    "endDate": datetime.now().strftime("%Y-%m-%d"),
                }
                resp = self._request(api_url, method="POST", data=payload)
                data = resp.json()
                items = data.get("rows", data.get("data", []))
                if not items:
                    break
                for item in items:
                    notice = self._parse_item(item, keyword)
                    if notice:
                        results.append(notice)
                if len(items) < 20:
                    break
            except Exception as e:
                logger.debug(f"国家平台搜索失败: {e}")
                break

        return results

    def _parse_item(self, item: dict, keyword: str) -> dict:
        try:
            title = item.get("title", item.get("noticename", ""))
            pub_date = item.get("publishdate", item.get("noticesendtime", ""))
            notice_id = self._make_notice_id(title, str(pub_date), self.source_key)
            return {
                "notice_id": notice_id,
                "title": title,
                "source": self.source_key,
                "source_url": item.get("url", item.get("noticehref", "")),
                "notice_type": item.get("noticetype", "招标公告"),
                "project_name": title,
                "project_code": item.get("projectcode", ""),
                "region": self._detect_region(title + str(item.get("region", ""))),
                "budget": self._parse_budget(item.get("budget", "")),
                "publish_date": str(pub_date)[:10] if pub_date else datetime.now().strftime("%Y-%m-%d"),
                "deadline_date": item.get("enddate", ""),
                "tenderer": item.get("tenderee", ""),
                "agency": item.get("agency", ""),
                "winner": item.get("winner", ""),
                "win_amount": 0,
                "content": item.get("summary", ""),
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.debug(f"解析条目失败: {e}")
            return None

    def _parse_budget(self, val) -> float:
        if not val:
            return 0
        if isinstance(val, (int, float)):
            return float(val) / 10000
        s = str(val)
        nums = re.findall(r"[\d.]+", s)
        if nums:
            amount = float(nums[0])
            if "亿" in s:
                amount *= 10000
            elif "万" not in s:
                amount /= 10000
            return amount
        return 0


class BidCenterScraper(BaseScraper):
    """广东招标网(bidcenter.com.cn)爬虫 - 聚合数据源"""

    def __init__(self):
        super().__init__("national")
        self.base_url = "https://gd.bidcenter.com.cn"

    def search(self, keyword: str, days: int = 7) -> list:
        results = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for page in range(1, min(CRAWLER_CONFIG["max_pages"] + 1, 8)):
            try:
                url = f"{self.base_url}/search?keywords={quote_plus(keyword)}&page={page}"
                resp = self._request(url)
                soup = BeautifulSoup(resp.text, "lxml")

                items = soup.select(".list-item, .result-item, .content-item, li.clearfix")
                if not items:
                    items = soup.find_all("a", text=re.compile(keyword))

                found = False
                for item in items:
                    link = item if item.name == "a" else item.find("a")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    if not title or keyword not in title:
                        continue

                    date_text = ""
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", str(item))
                    if date_match:
                        date_text = date_match.group(1)
                        try:
                            item_date = datetime.strptime(date_text, "%Y-%m-%d")
                            if item_date < cutoff_date:
                                continue
                        except ValueError:
                            pass

                    href = link.get("href", "")
                    full_url = urljoin(self.base_url, href)
                    notice_id = self._make_notice_id(title, date_text, "bidcenter")

                    results.append({
                        "notice_id": notice_id,
                        "title": title,
                        "source": "bidcenter",
                        "source_url": full_url,
                        "notice_type": "招标公告",
                        "project_name": title,
                        "region": self._detect_region(title),
                        "budget": 0,
                        "publish_date": date_text or datetime.now().strftime("%Y-%m-%d"),
                        "deadline_date": "",
                        "tenderer": "",
                        "agency": "",
                        "winner": "",
                        "win_amount": 0,
                        "content": "",
                        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    found = True

                if not found:
                    break
            except Exception as e:
                logger.debug(f"广东招标网搜索失败: {e}")
                break

        return results


class DataCollector:
    """数据采集协调器"""

    def __init__(self):
        self.scrapers = []
        if SOURCES["gd_zbtb"]["enabled"]:
            self.scrapers.append(GdZbtbScraper())
        if SOURCES["gz_ggzy"]["enabled"]:
            self.scrapers.append(GzGgzyScraper())
        if SOURCES["national"]["enabled"]:
            self.scrapers.append(NationalCebScraper())
            self.scrapers.append(BidCenterScraper())

    def collect_all(self, keywords: list = None, days: int = 7) -> list:
        """执行全量采集"""
        if keywords is None:
            # 使用核心关键词去重
            keywords = list(set(ALL_KEYWORDS))

        all_results = []
        seen_ids = set()

        for scraper in self.scrapers:
            logger.info(f"--- 开始采集: {scraper.source_config['name']} ---")
            for kw in keywords:
                try:
                    logger.info(f"  搜索关键词: {kw}")
                    items = scraper.search(kw, days=days)
                    for item in items:
                        if item["notice_id"] not in seen_ids:
                            seen_ids.add(item["notice_id"])
                            all_results.append(item)
                except Exception as e:
                    logger.error(f"  关键词 '{kw}' 采集失败: {e}")
                    scraper.source_config  # log
            scraper.close()

        logger.info(f"全量采集完成: 共获取 {len(all_results)} 条公告")
        return all_results

    def collect_quick(self, days: int = 7) -> list:
        """快速采集(使用高优先级关键词)"""
        priority_keywords = [
            "海洋地质", "海洋工程", "海上风电", "地质勘探", "地质调查",
            "海洋调查", "港口建设", "海底隧道", "地质灾害", "海洋监测",
            "航道疏浚", "海洋装备", "岩土工程", "海洋牧场", "海域使用论证",
        ]
        return self.collect_all(keywords=priority_keywords, days=days)

    def close(self):
        for s in self.scrapers:
            try:
                s.close()
            except Exception:
                pass
