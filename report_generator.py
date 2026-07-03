# -*- coding: utf-8 -*-
"""
报告生成器 - HTML 格式周度分析报告
"""

import os
import json
import logging
from datetime import datetime
from jinja2 import Template

logger = logging.getLogger(__name__)

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省地质海洋企业招投标情报周报 - {{ report_date }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { 
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
    background: #f0f2f5; color: #333; line-height: 1.8; padding: 20px;
  }
  .container { max-width: 1200px; margin: 0 auto; background: #fff; 
    border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden; }
  
  /* 头部 */
  .header { 
    background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%); 
    color: #fff; padding: 40px; position: relative; overflow: hidden;
  }
  .header::after {
    content: ''; position: absolute; right: -50px; top: -50px;
    width: 300px; height: 300px; border-radius: 50%;
    background: rgba(255,255,255,0.05);
  }
  .header h1 { font-size: 28px; margin-bottom: 8px; }
  .header .subtitle { font-size: 15px; opacity: 0.85; }
  .header .meta { margin-top: 16px; font-size: 13px; opacity: 0.7; }
  
  /* 统计卡片 */
  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px; }
  .stat-card { 
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 10px; padding: 20px; text-align: center;
    border-left: 4px solid #2d6a9f;
  }
  .stat-card.highlight { border-left-color: #e74c3c; background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%); }
  .stat-card.invest { border-left-color: #27ae60; background: linear-gradient(135deg, #f0fff4 0%, #e0f8e8 100%); }
  .stat-card .label { font-size: 13px; color: #666; margin-bottom: 8px; }
  .stat-card .value { font-size: 32px; font-weight: 700; color: #1a3a5c; }
  .stat-card.highlight .value { color: #e74c3c; }
  .stat-card.invest .value { color: #27ae60; }
  .stat-card .unit { font-size: 14px; color: #999; }
  
  /* 区块 */
  .section { padding: 24px; border-top: 1px solid #eee; }
  .section-title { 
    font-size: 20px; font-weight: 700; color: #1a3a5c; 
    margin-bottom: 16px; padding-left: 12px; border-left: 4px solid #2d6a9f;
  }
  
  /* 产业链卡片 */
  .chain-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
  .chain-card { 
    border: 1px solid #e0e0e0; border-radius: 10px; padding: 20px; 
    transition: box-shadow 0.3s;
  }
  .chain-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .chain-card.upstream { border-top: 3px solid #3498db; }
  .chain-card.midstream { border-top: 3px solid #e67e22; }
  .chain-card.downstream { border-top: 3px solid #2ecc71; }
  .chain-card.investment { border-top: 3px solid #9b59b6; }
  .chain-card h3 { font-size: 16px; margin-bottom: 8px; color: #333; }
  .chain-card .chain-stat { display: flex; gap: 20px; margin-bottom: 12px; }
  .chain-card .chain-stat div { flex: 1; }
  .chain-card .chain-stat .num { font-size: 24px; font-weight: 700; color: #1a3a5c; }
  .chain-card .chain-stat .desc { font-size: 12px; color: #999; }
  
  /* 表格 */
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th { background: #f8f9fa; padding: 12px; text-align: left; 
    font-size: 13px; color: #666; border-bottom: 2px solid #dee2e6; }
  td { padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }
  tr:hover { background: #f8f9fa; }
  .score-badge { 
    display: inline-block; padding: 2px 10px; border-radius: 12px; 
    font-size: 12px; font-weight: 600;
  }
  .score-high { background: #e8f5e9; color: #2e7d32; }
  .score-medium { background: #fff3e0; color: #e65100; }
  .score-low { background: #fce4ec; color: #c62828; }
  
  /* 商机推荐 */
  .opportunity-item { 
    border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; 
    margin-bottom: 12px; display: flex; gap: 16px; align-items: start;
  }
  .opportunity-rank { 
    min-width: 36px; height: 36px; border-radius: 50%; 
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 16px; color: #fff;
  }
  .rank-1 { background: #e74c3c; }
  .rank-2 { background: #e67e22; }
  .rank-3 { background: #f39c12; }
  .rank-other { background: #95a5a6; }
  .opportunity-content { flex: 1; }
  .opportunity-title { font-weight: 600; font-size: 15px; margin-bottom: 4px; }
  .opportunity-meta { font-size: 13px; color: #888; }
  .opportunity-kw { margin-top: 6px; }
  .opportunity-kw span { 
    display: inline-block; background: #e8f4fd; color: #1976d2; 
    padding: 1px 8px; border-radius: 4px; font-size: 12px; margin-right: 4px;
  }
  
  /* 产业链缺口 */
  .gap-item { 
    background: #fff8e1; border-left: 4px solid #ffc107; 
    padding: 14px 18px; border-radius: 6px; margin-bottom: 10px;
  }
  .gap-item .gap-type { font-size: 12px; color: #e65100; font-weight: 600; margin-bottom: 4px; }
  .gap-item .gap-desc { font-size: 14px; color: #555; }
  .gap-item .gap-opp { font-size: 13px; color: #27ae60; margin-top: 4px; }
  
  /* 关键词云 */
  .keyword-cloud { display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 0; }
  .keyword-tag { 
    display: inline-block; padding: 4px 12px; border-radius: 16px;
    font-size: 13px; background: #e3f2fd; color: #1565c0;
  }
  .keyword-tag.hot { background: #ffebee; color: #c62828; font-weight: 600; }
  .keyword-tag.warm { background: #fff3e0; color: #e65100; }
  
  /* 地区分布 */
  .region-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .region-name { min-width: 80px; font-size: 14px; }
  .region-progress { flex: 1; height: 24px; background: #f0f0f0; border-radius: 12px; overflow: hidden; }
  .region-fill { height: 100%; background: linear-gradient(90deg, #2d6a9f, #3498db); border-radius: 12px;
    display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: #fff; font-size: 12px; }
  
  /* 页脚 */
  .footer { 
    text-align: center; padding: 24px; color: #999; font-size: 13px;
    border-top: 1px solid #eee;
  }
  
  @media print {
    body { background: #fff; padding: 0; }
    .container { box-shadow: none; }
  }
</style>
</head>
<body>
<div class="container">
  
  <!-- 头部 -->
  <div class="header">
    <h1>广东省地质海洋企业招投标情报周报</h1>
    <div class="subtitle">上下游产业链动态 · 商机识别 · 招商引资节点追踪</div>
    <div class="meta">
      报告周期: {{ period_start }} ~ {{ period_end }} | 生成时间: {{ generated_at }} | 数据库: {{ db_path }}
    </div>
  </div>

  <!-- 概览统计 -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">本期公告总数</div>
      <div class="value">{{ overview.total_notices }}</div>
      <div class="unit">条</div>
    </div>
    <div class="stat-card highlight">
      <div class="label">涉及总金额</div>
      <div class="value">{{ "%.1f"|format(overview.total_budget) }}</div>
      <div class="unit">万元</div>
    </div>
    <div class="stat-card">
      <div class="label">平均项目金额</div>
      <div class="value">{{ "%.1f"|format(overview.avg_budget) }}</div>
      <div class="unit">万元</div>
    </div>
    <div class="stat-card invest">
      <div class="label">招商引资相关</div>
      <div class="value">{{ overview.investment_related_count }}</div>
      <div class="unit">条</div>
    </div>
  </div>

  <!-- 产业链分析 -->
  <div class="section">
    <div class="section-title">产业链分布分析</div>
    <div class="chain-grid">
      {% for chain_key, chain_info in chain_display.items() %}
      <div class="chain-card {{ chain_key }}">
        <h3>{{ chain_info.name }}</h3>
        <p style="font-size:13px;color:#888;margin-bottom:10px;">{{ chain_info.description }}</p>
        <div class="chain-stat">
          <div>
            <div class="num">{{ chain_info.count }}</div>
            <div class="desc">公告数(条)</div>
          </div>
          <div>
            <div class="num">{{ "%.0f"|format(chain_info.budget) }}</div>
            <div class="desc">总金额(万)</div>
          </div>
          <div>
            <div class="num">{{ "%.1f"|format(chain_info.avg_score) }}</div>
            <div class="desc">平均商机分</div>
          </div>
        </div>
        {% if chain_info.notice_items %}
        <table>
          <thead>
            <tr><th>项目名称</th><th>金额(万)</th><th>评分</th></tr>
          </thead>
          <tbody>
            {% for item in chain_info.notice_items[:5] %}
            <tr>
              <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                <a href="{{ item.source_url }}" target="_blank" style="color:#1976d2;text-decoration:none;">{{ item.title[:50] }}</a>
              </td>
              <td>{{ item.budget or '-' }}</td>
              <td><span class="score-badge {{ 'score-high' if item.opportunity_score >= 70 else ('score-medium' if item.opportunity_score >= 40 else 'score-low') }}">{{ item.opportunity_score or 0 }}</span></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% endif %}
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- 商机推荐 TOP -->
  <div class="section">
    <div class="section-title">商机推荐 TOP {{ top_opportunities|length }}</div>
    {% for opp in top_opportunities %}
    <div class="opportunity-item">
      <div class="opportunity-rank {{ 'rank-1' if loop.index == 1 else ('rank-2' if loop.index == 2 else ('rank-3' if loop.index == 3 else 'rank-other')) }}">
        {{ loop.index }}
      </div>
      <div class="opportunity-content">
        <div class="opportunity-title">
          <a href="{{ opp.source_url }}" target="_blank" style="color:#1a3a5c;text-decoration:none;">{{ opp.title[:80] }}</a>
        </div>
        <div class="opportunity-meta">
          {{ opp.region or '广东' }} | {{ opp.publish_date or '-' }} | 
          金额: {{ opp.budget or '-' }}万 | 
          来源: {{ opp.source }} | 
          类型: {{ opp.notice_type or '招标公告' }}
        </div>
        {% if opp.matched_keywords %}
        <div class="opportunity-kw">
          {% for kw in opp.keywords_list %}
          <span>{{ kw }}</span>
          {% endfor %}
        </div>
        {% endif %}
        <div style="margin-top:6px;">
          <span class="score-badge {{ 'score-high' if opp.opportunity_score >= 70 else ('score-medium' if opp.opportunity_score >= 40 else 'score-low') }}">
            商机评分: {{ opp.opportunity_score or 0 }}
          </span>
          {% if opp.is_investment_related %}
          <span class="score-badge score-high">招商引资相关</span>
          {% endif %}
        </div>
      </div>
    </div>
    {% endfor %}
    {% if not top_opportunities %}
    <p style="color:#999;padding:20px;">暂无商机数据,请先执行数据采集。</p>
    {% endif %}
  </div>

  <!-- 产业链缺口分析 -->
  <div class="section">
    <div class="section-title">产业链衔接缺口分析</div>
    {% for gap in chain_gaps %}
    <div class="gap-item">
      <div class="gap-type">{{ gap.type }}</div>
      <div class="gap-desc">{{ gap.description }}</div>
      <div class="gap-opp">→ {{ gap.opportunity }}</div>
    </div>
    {% endfor %}
  </div>

  <!-- 关键词热度 -->
  <div class="section">
    <div class="section-title">关键词热度排行</div>
    <div class="keyword-cloud">
      {% for kw, freq in keyword_freq %}
      <span class="keyword-tag {{ 'hot' if freq >= 5 else ('warm' if freq >= 3 else '') }}">{{ kw }} ({{ freq }})</span>
      {% endfor %}
    </div>
    {% if not keyword_freq %}
    <p style="color:#999;">暂无关键词数据。</p>
    {% endif %}
  </div>

  <!-- 地区分布 -->
  <div class="section">
    <div class="section-title">地区分布</div>
    {% for region, data in region_stats.items() %}
    <div class="region-bar">
      <div class="region-name">{{ region }}</div>
      <div class="region-progress">
        <div class="region-fill" style="width: {{ (data.count / max_region_count * 100)|round(1) }}%;">
          {{ data.count }}
        </div>
      </div>
    </div>
    {% endfor %}
    {% if not region_stats %}
    <p style="color:#999;">暂无地区数据。</p>
    {% endif %}
  </div>

  <!-- 活跃企业 -->
  <div class="section">
    <div class="section-title">活跃招标主体</div>
    <table>
      <thead>
        <tr><th>企业名称</th><th>类型</th><th>出现次数</th><th>涉及金额(万)</th><th>产业链</th></tr>
      </thead>
      <tbody>
        {% for entity in top_entities %}
        <tr>
          <td>{{ entity.name }}</td>
          <td>{{ entity.entity_type or '-' }}</td>
          <td>{{ entity.appear_count }}</td>
          <td>{{ "%.1f"|format(entity.total_budget) }}</td>
          <td>{{ entity.chain_position or '-' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% if not top_entities %}
    <p style="color:#999;">暂无企业数据。</p>
    {% endif %}
  </div>

  <!-- 页脚 -->
  <div class="footer">
    <p>广东省地质海洋企业招投标情报系统 | 自动生成 | 数据来源: 广东省招标投标监管网、广州公共资源交易中心、中国招标投标公共服务平台</p>
    <p style="margin-top:6px;">本报告由系统自动采集公开招标信息并分析生成,仅供参考。投资决策请以官方公告为准。</p>
  </div>

</div>
</body>
</html>"""


class ReportGenerator:
    """报告生成器"""

    def __init__(self, report_dir: str, db_path: str):
        self.report_dir = report_dir
        self.db_path = db_path
        os.makedirs(report_dir, exist_ok=True)

    def generate(self, summary: dict, chain_gaps: list = None) -> str:
        """生成HTML报告"""
        if chain_gaps is None:
            chain_gaps = []

        # 准备模板数据
        chain_display = {}
        for chain_key, chain_info in {
            "upstream": {"name": "上游·勘探与装备", "description": "地质勘探、海洋调查、装备制造"},
            "midstream": {"name": "中游·工程与施工", "description": "海洋工程、地质施工、港口航道"},
            "downstream": {"name": "下游·监测与服务", "description": "环境监测、技术服务、数据信息"},
            "investment": {"name": "招商引资", "description": "产业园区、投资合作、特许经营"},
        }.items():
            stats = summary.get("chain_stats", {}).get(chain_key, {})
            items = summary.get("chain_details", {}).get(chain_key, [])
            chain_display[chain_key] = {
                "name": chain_info["name"],
                "description": chain_info["description"],
                "count": stats.get("count", 0),
                "budget": stats.get("total_budget", 0) or 0,
                "avg_score": stats.get("avg_score", 0) or 0,
                "notice_items": items,
            }

        # 计算地区最大值(用于进度条)
        region_stats = summary.get("region_stats", {})
        max_region_count = max((v["count"] for v in region_stats.values()), default=1) if region_stats else 1

        # 合并企业列表
        top_entities = (summary.get("top_tenderers", []) or [])[:10] + \
                       (summary.get("top_winners", []) or [])[:5]

        # 预处理商机数据: 解析 matched_keywords JSON 为列表
        top_opps = summary.get("top_opportunities", []) or []
        for opp in top_opps:
            raw_kws = opp.get("matched_keywords", "")
            if raw_kws:
                try:
                    opp["keywords_list"] = json.loads(raw_kws)[:8]
                except (json.JSONDecodeError, TypeError):
                    opp["keywords_list"] = []
            else:
                opp["keywords_list"] = []

        # 渲染
        from jinja2 import Environment
        env = Environment()
        env.filters["from_json"] = lambda s: json.loads(s) if s else []
        template = env.from_string(REPORT_TEMPLATE)
        
        html = template.render(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            period_start=summary.get("period", {}).get("start", ""),
            period_end=summary.get("period", {}).get("end", ""),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            db_path=self.db_path,
            overview=summary.get("overview", {}),
            chain_display=chain_display,
            top_opportunities=top_opps,
            chain_gaps=chain_gaps,
            keyword_freq=summary.get("keyword_freq", []),
            region_stats=region_stats,
            max_region_count=max_region_count,
            top_entities=top_entities,
        )

        # 保存
        filename = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.html"
        filepath = os.path.join(self.report_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"报告已生成: {filepath}")
        return filepath
