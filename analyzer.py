# -*- coding: utf-8 -*-
"""
分析引擎 - 产业链映射、商机评分、投资机会识别
"""

import json
import re
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from config import INDUSTRY_CHAIN_MAP, ANALYSIS_CONFIG, KEYWORDS_UPSTREAM, \
    KEYWORDS_MIDSTREAM, KEYWORDS_DOWNSTREAM, KEYWORDS_INVESTMENT
from db import Database

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """分析引擎"""

    def __init__(self, db: Database):
        self.db = db
        # 构建关键词到产业链位置的映射
        self.keyword_to_chain = {}
        for chain_key, chain_info in INDUSTRY_CHAIN_MAP.items():
            for kw in chain_info["keywords"]:
                self.keyword_to_chain[kw] = chain_key

    def analyze_notice(self, notice: dict) -> dict:
        """分析单条公告: 产业链定位 + 商机评分"""
        text = " ".join(filter(None, [
            notice.get("title", ""),
            notice.get("project_name", ""),
            notice.get("content", ""),
            notice.get("tenderer", ""),
        ]))

        # 1. 关键词匹配与产业链定位
        matched_keywords = []
        chain_hits = Counter()

        for kw, chain_key in self.keyword_to_chain.items():
            if kw in text:
                matched_keywords.append(kw)
                chain_hits[chain_key] += 1

        # 产业链位置: 取命中最多的
        if chain_hits:
            chain_position = chain_hits.most_common(1)[0][0]
        else:
            chain_position = None

        # 2. 相关度评分 (0-100)
        relevance_score = self._calc_relevance(text, matched_keywords)

        # 3. 商机评分 (0-100)
        opportunity_score = self._calc_opportunity_score(notice, matched_keywords, chain_hits)

        # 4. 招商引资关联判断
        is_investment = any(kw in text for kw in KEYWORDS_INVESTMENT)

        return {
            "notice_id": notice["notice_id"],
            "chain_position": chain_position,
            "matched_keywords": json.dumps(matched_keywords, ensure_ascii=False),
            "relevance_score": round(relevance_score, 1),
            "opportunity_score": round(opportunity_score, 1),
            "is_investment_related": 1 if is_investment else 0,
        }

    def _calc_relevance(self, text: str, matched_keywords: list) -> float:
        """计算相关度评分"""
        if not matched_keywords:
            return 0
        # 基础分: 每个关键词5分, 上限60
        base = min(len(matched_keywords) * 5, 60)
        # 加分: 核心关键词加权
        core_keywords = ["海洋地质", "海洋工程", "地质勘探", "海上风电", 
                         "地质灾害", "海洋调查", "港口建设", "海底隧道"]
        core_bonus = sum(8 for kw in matched_keywords if kw in core_keywords)
        return min(base + core_bonus, 100)

    def _calc_opportunity_score(self, notice: dict, matched_keywords: list,
                                chain_hits: Counter) -> float:
        """计算商机综合评分"""
        weights = ANALYSIS_CONFIG["score_weights"]
        score = 0

        # 预算金额评分 (0-100)
        budget = notice.get("budget", 0) or notice.get("win_amount", 0) or 0
        thresholds = ANALYSIS_CONFIG["budget_thresholds"]
        if budget >= thresholds["high"]:
            budget_score = 100
        elif budget >= thresholds["medium"]:
            budget_score = 70
        elif budget >= thresholds["low"]:
            budget_score = 40
        elif budget > 0:
            budget_score = 20
        else:
            budget_score = 30  # 未知金额给中等偏低分
        score += budget_score * weights["budget"]

        # 关键词相关度评分
        relevance = self._calc_relevance("", matched_keywords)
        score += relevance * weights["keyword_relevance"]

        # 产业链覆盖度评分
        if chain_hits:
            coverage = min(sum(chain_hits.values()) * 10, 100)
        else:
            coverage = 0
        score += coverage * weights["chain_coverage"]

        # 时效性评分
        pub_date_str = notice.get("publish_date", "")
        try:
            pub_date = datetime.strptime(pub_date_str[:10], "%Y-%m-%d")
            days_ago = (datetime.now() - pub_date).days
            recency_score = max(0, 100 - days_ago * 5)
        except (ValueError, TypeError):
            recency_score = 50
        score += recency_score * weights["recency"]

        # 招商引资潜力评分
        text = " ".join(filter(None, [notice.get("title", ""), notice.get("content", "")]))
        investment_kws_found = sum(1 for kw in KEYWORDS_INVESTMENT if kw in text)
        invest_score = min(investment_kws_found * 25, 100)
        score += invest_score * weights["investment_potential"]

        return score

    def analyze_all_unanalyzed(self, batch_size: int = 100):
        """分析所有未分析的公告"""
        while True:
            notices = self.db.get_unanalyzed_notices(limit=batch_size)
            if not notices:
                break
            logger.info(f"分析批次: {len(notices)} 条")
            for notice in notices:
                try:
                    result = self.analyze_notice(notice)
                    self.db.update_analysis(**result)

                    # 更新企业实体
                    if notice.get("tenderer"):
                        self.db.upsert_entity(
                            notice["tenderer"], "tenderer",
                            result.get("chain_position"),
                            notice.get("region"),
                            notice.get("budget", 0)
                        )
                    if notice.get("agency"):
                        self.db.upsert_entity(
                            notice["agency"], "agency",
                            result.get("chain_position"),
                            notice.get("region")
                        )
                    if notice.get("winner"):
                        self.db.upsert_entity(
                            notice["winner"], "winner",
                            result.get("chain_position"),
                            notice.get("region"),
                            notice.get("win_amount", 0)
                        )
                except Exception as e:
                    logger.error(f"分析公告失败 {notice.get('notice_id')}: {e}")
            logger.info(f"批次分析完成")

    def generate_weekly_summary(self, days: int = 7) -> dict:
        """生成周度分析摘要"""
        recent = self.db.get_recent_notices(days=days)
        if not recent:
            return {"error": "无最近公告数据"}

        # 产业链统计
        chain_stats = self.db.get_stats_by_chain(days=days)

        # 地区统计
        region_stats = self.db.get_stats_by_region(days=days)

        # 商机TOP
        top_opportunities = self.db.get_top_opportunities(limit=ANALYSIS_CONFIG["max_items_per_category"])

        # 活跃企业
        top_tenderers = self.db.get_top_entities("tenderer", limit=10)
        top_winners = self.db.get_top_entities("winner", limit=10)

        # 产业链明细
        chain_details = defaultdict(list)
        for n in recent:
            if n.get("chain_position"):
                chain_details[n["chain_position"]].append(n)

        # 关键词频率
        all_keywords = []
        for n in recent:
            if n.get("matched_keywords"):
                try:
                    all_keywords.extend(json.loads(n["matched_keywords"]))
                except json.JSONDecodeError:
                    pass
        keyword_freq = Counter(all_keywords).most_common(20)

        # 金额统计
        total_budget = sum(n.get("budget", 0) or 0 for n in recent)
        avg_budget = total_budget / len(recent) if recent else 0

        # 金额分布
        budget_ranges = {"high (>5000万)": 0, "medium (1000-5000万)": 0,
                         "low (100-1000万)": 0, "micro (<100万)": 0, "unknown": 0}
        for n in recent:
            b = n.get("budget", 0) or 0
            if b >= 5000:
                budget_ranges["high (>5000万)"] += 1
            elif b >= 1000:
                budget_ranges["medium (1000-5000万)"] += 1
            elif b >= 100:
                budget_ranges["low (100-1000万)"] += 1
            elif b > 0:
                budget_ranges["micro (<100万)"] += 1
            else:
                budget_ranges["unknown"] += 1

        # 招商引资相关
        investment_related = [n for n in recent if n.get("is_investment_related")]

        summary = {
            "period": {
                "start": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "days": days,
            },
            "overview": {
                "total_notices": len(recent),
                "total_budget": round(total_budget, 2),
                "avg_budget": round(avg_budget, 2),
                "investment_related_count": len(investment_related),
            },
            "chain_stats": chain_stats,
            "chain_details": {
                k: sorted(v, key=lambda x: x.get("opportunity_score", 0), reverse=True)[:10]
                for k, v in chain_details.items()
            },
            "region_stats": region_stats,
            "top_opportunities": top_opportunities,
            "top_tenderers": top_tenderers,
            "top_winners": top_winners,
            "keyword_freq": keyword_freq,
            "budget_distribution": budget_ranges,
            "investment_opportunities": investment_related[:10],
        }

        return summary

    def identify_chain_gaps(self) -> list:
        """识别产业链缺口 - 分析上下游衔接机会"""
        gaps = []
        recent = self.db.get_recent_notices(days=30, limit=500)

        # 按产业链位置分组
        chain_items = defaultdict(list)
        for n in recent:
            if n.get("chain_position"):
                chain_items[n["chain_position"]].append(n)

        # 分析上游-中游衔接
        upstream_kw = set()
        for n in chain_items.get("upstream", []):
            if n.get("matched_keywords"):
                try:
                    upstream_kw.update(json.loads(n["matched_keywords"]))
                except json.JSONDecodeError:
                    pass

        midstream_kw = set()
        for n in chain_items.get("midstream", []):
            if n.get("matched_keywords"):
                try:
                    midstream_kw.update(json.loads(n["matched_keywords"]))
                except json.JSONDecodeError:
                    pass

        # 上游有勘探需求但中游缺少对应工程
        if "地质勘探" in upstream_kw and "岩土工程" not in midstream_kw:
            gaps.append({
                "type": "upstream-midstream gap",
                "description": "上游有地质勘探需求,但中游岩土工程施工项目偏少,存在衔接缺口",
                "opportunity": "可关注岩土工程企业的市场机会",
            })

        # 中游有海洋工程但下游缺少监测
        downstream_kw = set()
        for n in chain_items.get("downstream", []):
            if n.get("matched_keywords"):
                try:
                    downstream_kw.update(json.loads(n["matched_keywords"]))
                except json.JSONDecodeError:
                    pass

        if "海上风电" in midstream_kw and "海洋监测" not in downstream_kw:
            gaps.append({
                "type": "midstream-downstream gap",
                "description": "中游海上风电项目活跃,但下游海洋环境监测配套项目偏少",
                "opportunity": "海上风电后期运维和海洋环境监测服务存在商机",
            })

        if not gaps:
            gaps.append({
                "type": "balanced",
                "description": "当前产业链上下游衔接基本平衡,暂未发现明显缺口",
                "opportunity": "持续监测动态变化",
            })

        return gaps
