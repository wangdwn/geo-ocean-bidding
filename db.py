# -*- coding: utf-8 -*-
"""
数据库模块 - SQLite 数据库操作
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ===== 建表SQL =====
SCHEMA_SQL = """
-- 招标公告主表
CREATE TABLE IF NOT EXISTS bidding_notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_id TEXT UNIQUE,              -- 公告编号(来自源站)
    title TEXT NOT NULL,                -- 公告标题
    source TEXT,                        -- 数据来源(gd_zbtb/gd_ggzy/gz_ggzy/national)
    source_url TEXT,                    -- 原文链接
    notice_type TEXT,                   -- 公告类型(招标公告/中标公告/变更公告等)
    project_name TEXT,                  -- 项目名称
    project_code TEXT,                  -- 项目编号
    region TEXT,                        -- 地区
    budget REAL,                        -- 预算金额(万元)
    publish_date TEXT,                  -- 发布日期
    deadline_date TEXT,                 -- 投标截止日期
    tenderer TEXT,                      -- 招标人
    agency TEXT,                        -- 招标代理机构
    winner TEXT,                        -- 中标人(中标公告)
    win_amount REAL,                    -- 中标金额(万元)
    content TEXT,                       -- 公告正文摘要
    raw_html TEXT,                      -- 原始HTML(可选)
    
    -- 分析字段
    chain_position TEXT,                -- 产业链位置(upstream/midstream/downstream/investment)
    matched_keywords TEXT,              -- 匹配到的关键词(JSON数组)
    relevance_score REAL DEFAULT 0,     -- 相关度评分(0-100)
    opportunity_score REAL DEFAULT 0,   -- 商机评分(0-100)
    is_investment_related INTEGER DEFAULT 0,  -- 是否与招商引资相关
    is_new INTEGER DEFAULT 1,           -- 是否为新发现
    
    collected_at TEXT,                  -- 采集时间
    analyzed_at TEXT,                   -- 分析时间
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 企业主体表
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,                   -- 企业名称
    entity_type TEXT,                   -- 类型(tenderer/agency/winner)
    chain_position TEXT,                -- 产业链位置
    region TEXT,                        -- 所在地区
    appear_count INTEGER DEFAULT 0,     -- 出现次数
    total_budget REAL DEFAULT 0,        -- 涉及总金额(万元)
    first_seen TEXT,                    -- 首次出现时间
    last_seen TEXT,                     -- 最后出现时间
    notes TEXT,                         -- 备注
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 产业链关系表
CREATE TABLE IF NOT EXISTS chain_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upstream_entity TEXT,               -- 上游企业
    downstream_entity TEXT,             -- 下游企业
    relation_type TEXT,                 -- 关系类型(supply/cooperate/compete)
    notice_id TEXT,                     -- 关联公告
    strength INTEGER DEFAULT 1,         -- 关系强度
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 分析报告表
CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,          -- 报告日期
    report_type TEXT DEFAULT 'weekly',  -- 报告类型(weekly/monthly)
    period_start TEXT,                  -- 统计周期开始
    period_end TEXT,                    -- 统计周期结束
    total_notices INTEGER,              -- 本期公告总数
    new_notices INTEGER,                -- 新增公告数
    total_budget REAL,                  -- 涉及总金额
    chain_summary TEXT,                 -- 产业链摘要(JSON)
    top_opportunities TEXT,             -- 商机推荐(JSON)
    entity_summary TEXT,                -- 企业摘要(JSON)
    region_summary TEXT,                -- 地区摘要(JSON)
    report_path TEXT,                   -- 报告文件路径
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 采集日志表
CREATE TABLE IF NOT EXISTS collection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,                        -- 数据源
    keyword TEXT,                       -- 搜索关键词
    status TEXT,                        -- 状态(success/failed/partial)
    items_collected INTEGER DEFAULT 0,  -- 采集条数
    error_msg TEXT,                     -- 错误信息
    started_at TEXT,                    -- 开始时间
    finished_at TEXT,                   -- 结束时间
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_notices_source ON bidding_notices(source);
CREATE INDEX IF NOT EXISTS idx_notices_date ON bidding_notices(publish_date);
CREATE INDEX IF NOT EXISTS idx_notices_chain ON bidding_notices(chain_position);
CREATE INDEX IF NOT EXISTS idx_notices_score ON bidding_notices(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_notices_region ON bidding_notices(region);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_reports_date ON analysis_reports(report_date);
"""


class Database:
    """数据库操作类"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def get_conn(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=MEMORY")
        except sqlite3.OperationalError:
            pass
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表结构"""
        with self.get_conn() as conn:
            conn.executescript(SCHEMA_SQL)
            logger.info(f"数据库初始化完成: {self.db_path}")

    def upsert_notice(self, notice: dict) -> bool:
        """插入或更新招标公告(基于notice_id去重)"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            # 检查是否已存在
            existing = cursor.execute(
                "SELECT id FROM bidding_notices WHERE notice_id = ?",
                (notice.get("notice_id"),)
            ).fetchone()

            if existing:
                # 更新
                notice["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                notice.pop("is_new", None)
                set_clause = ", ".join([f"{k} = ?" for k in notice.keys() if k != "notice_id"])
                values = list(notice.values())
                values.append(notice.get("notice_id"))
                cursor.execute(
                    f"UPDATE bidding_notices SET {set_clause} WHERE notice_id = ?",
                    values
                )
                return False  # 更新而非新增
            else:
                # 插入
                cols = ", ".join(notice.keys())
                placeholders = ", ".join(["?"] * len(notice))
                cursor.execute(
                    f"INSERT INTO bidding_notices ({cols}) VALUES ({placeholders})",
                    list(notice.values())
                )
                return True  # 新增

    def batch_upsert_notices(self, notices: list) -> tuple:
        """批量插入公告, 返回 (新增数, 更新数)"""
        new_count = 0
        update_count = 0
        for notice in notices:
            if self.upsert_notice(notice):
                new_count += 1
            else:
                update_count += 1
        logger.info(f"批量写入完成: 新增{new_count}条, 更新{update_count}条")
        return new_count, update_count

    def upsert_entity(self, name: str, entity_type: str, chain_position: str = None,
                      region: str = None, budget: float = 0):
        """插入或更新企业实体"""
        if not name:
            return
        with self.get_conn() as conn:
            cursor = conn.cursor()
            existing = cursor.execute(
                "SELECT id, appear_count, total_budget FROM entities WHERE name = ?",
                (name,)
            ).fetchone()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if existing:
                cursor.execute(
                    """UPDATE entities SET 
                       appear_count = appear_count + 1,
                       total_budget = total_budget + ?,
                       last_seen = ?,
                       updated_at = ?
                       WHERE name = ?""",
                    (budget, now, now, name)
                )
            else:
                cursor.execute(
                    """INSERT INTO entities 
                       (name, entity_type, chain_position, region, appear_count, 
                        total_budget, first_seen, last_seen)
                       VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
                    (name, entity_type, chain_position, region, budget, now, now)
                )

    def update_analysis(self, notice_id: str, chain_position: str,
                        matched_keywords: str, relevance_score: float,
                        opportunity_score: float, is_investment_related: int):
        """更新公告的分析结果"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_conn() as conn:
            conn.execute(
                """UPDATE bidding_notices SET 
                   chain_position = ?, matched_keywords = ?, relevance_score = ?,
                   opportunity_score = ?, is_investment_related = ?,
                   analyzed_at = ?, is_new = 0
                   WHERE notice_id = ?""",
                (chain_position, matched_keywords, relevance_score,
                 opportunity_score, is_investment_related, now, notice_id)
            )

    def get_recent_notices(self, days: int = 7, limit: int = 500) -> list:
        """获取最近N天的公告"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM bidding_notices 
                   WHERE publish_date >= ? 
                   ORDER BY publish_date DESC, opportunity_score DESC 
                   LIMIT ?""",
                (cutoff, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_top_opportunities(self, limit: int = 20) -> list:
        """获取商机评分最高的公告"""
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM bidding_notices 
                   WHERE opportunity_score > 0
                   ORDER BY opportunity_score DESC 
                   LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats_by_chain(self, days: int = 7) -> dict:
        """按产业链位置统计"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT chain_position, 
                          COUNT(*) as count,
                          SUM(budget) as total_budget,
                          AVG(opportunity_score) as avg_score
                   FROM bidding_notices 
                   WHERE publish_date >= ? AND chain_position IS NOT NULL
                   GROUP BY chain_position""",
                (cutoff,)
            ).fetchall()
            return {r["chain_position"]: dict(r) for r in rows}

    def get_stats_by_region(self, days: int = 7) -> dict:
        """按地区统计"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT region, 
                          COUNT(*) as count,
                          SUM(budget) as total_budget
                   FROM bidding_notices 
                   WHERE publish_date >= ? AND region IS NOT NULL
                   GROUP BY region
                   ORDER BY count DESC""",
                (cutoff,)
            ).fetchall()
            return {r["region"]: dict(r) for r in rows}

    def get_top_entities(self, entity_type: str = None, limit: int = 20) -> list:
        """获取活跃企业"""
        with self.get_conn() as conn:
            if entity_type:
                rows = conn.execute(
                    """SELECT * FROM entities 
                       WHERE entity_type = ?
                       ORDER BY appear_count DESC, total_budget DESC 
                       LIMIT ?""",
                    (entity_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM entities 
                       ORDER BY appear_count DESC, total_budget DESC 
                       LIMIT ?""",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    def log_collection(self, source: str, keyword: str, status: str,
                       items: int = 0, error: str = None):
        """记录采集日志"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_conn() as conn:
            conn.execute(
                """INSERT INTO collection_logs 
                   (source, keyword, status, items_collected, error_msg, 
                    started_at, finished_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (source, keyword, status, items, error, now, now)
            )

    def get_unanalyzed_notices(self, limit: int = 100) -> list:
        """获取未分析的公告"""
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM bidding_notices 
                   WHERE analyzed_at IS NULL 
                   ORDER BY publish_date DESC 
                   LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def save_report(self, report_date: str, period_start: str, period_end: str,
                    total_notices: int, new_notices: int, total_budget: float,
                    chain_summary: str, top_opportunities: str,
                    entity_summary: str, region_summary: str, report_path: str):
        """保存报告记录"""
        with self.get_conn() as conn:
            conn.execute(
                """INSERT INTO analysis_reports 
                   (report_date, period_start, period_end, total_notices, 
                    new_notices, total_budget, chain_summary, top_opportunities,
                    entity_summary, region_summary, report_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (report_date, period_start, period_end, total_notices,
                 new_notices, total_budget, chain_summary, top_opportunities,
                 entity_summary, region_summary, report_path)
            )

    def get_all_notices_count(self) -> int:
        """获取总公告数"""
        with self.get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM bidding_notices").fetchone()[0]

    def get_new_notices_count(self) -> int:
        """获取新公告数"""
        with self.get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM bidding_notices WHERE is_new = 1"
            ).fetchone()[0]
