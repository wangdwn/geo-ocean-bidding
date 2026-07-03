# -*- coding: utf-8 -*-
"""
报告生成器 - HTML 格式周度分析报告
海洋地质主题 · Chart.js 可视化 · 期号标注
"""

import os
import json
import logging
from datetime import datetime
from jinja2 import Environment

logger = logging.getLogger(__name__)

REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省地质海洋企业招投标情报周报 第{{ issue_number }}期 - {{ report_date }}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {
    --ocean-deep: #062040;
    --ocean-dark: #0a2f5a;
    --ocean-mid: #0d6b7d;
    --ocean-light: #14a085;
    --coral: #e07050;
    --coral-light: #fadbd8;
    --gold: #f0c040;
    --sand: #f5efe0;
    --surface: #f0f4f8;
    --surface-alt: #e8eef5;
    --text-primary: #1a2a3a;
    --text-secondary: #5a6d7e;
    --text-muted: #8a9bab;
    --border: #d8e0e8;
    --white: #ffffff;
    --upstream: #3498db;
    --midstream: #e67e22;
    --downstream: #27ae60;
    --investment: #8e44ad;
    --radius: 12px;
    --shadow-sm: 0 1px 3px rgba(6,32,64,0.06);
    --shadow-md: 0 4px 16px rgba(6,32,64,0.08);
    --shadow-lg: 0 8px 32px rgba(6,32,64,0.12);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { 
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
    background: linear-gradient(180deg, #e8eef5 0%, #f0f4f8 30%, #f7f9fb 100%);
    color: var(--text-primary); line-height: 1.8; 
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 0 16px 40px; }
  
  /* ===== 头部 ===== */
  .hero {
    position: relative;
    background: linear-gradient(160deg, #031528 0%, #062040 25%, #0a2f5a 60%, #0d4a6e 100%);
    color: var(--white); padding: 48px 40px 36px;
    margin: 0 -16px;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute; inset: 0;
    background: 
      radial-gradient(ellipse 80% 50% at 20% 80%, rgba(13,107,125,0.3) 0%, transparent 60%),
      radial-gradient(ellipse 60% 40% at 85% 20%, rgba(20,160,133,0.15) 0%, transparent 50%),
      radial-gradient(circle at 60% 90%, rgba(240,192,64,0.08) 0%, transparent 40%);
    pointer-events: none;
  }
  .hero-waves {
    position: absolute; bottom: -2px; left: 0; width: 100%;
    height: 60px; pointer-events: none;
  }
  .hero-waves svg { display: block; width: 100%; height: 100%; }
  .hero-inner { position: relative; z-index: 1; }
  
  /* 期号徽章 */
  .issue-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 50px;
    padding: 6px 20px 6px 8px;
    margin-bottom: 20px;
    font-size: 14px; color: rgba(255,255,255,0.85);
  }
  .issue-badge .num-circle {
    display: inline-flex; align-items: center; justify-content: center;
    width: 40px; height: 40px; border-radius: 50%;
    background: linear-gradient(135deg, var(--coral), #e88060);
    font-size: 18px; font-weight: 800; color: #fff;
    box-shadow: 0 2px 12px rgba(224,112,80,0.5);
  }
  
  .hero h1 { font-size: 30px; font-weight: 800; letter-spacing: 2px; margin-bottom: 6px; }
  .hero .subtitle { font-size: 15px; opacity: 0.8; margin-bottom: 4px; }
  .hero .period {
    display: inline-flex; align-items: center; gap: 8px;
    margin-top: 12px; padding: 6px 16px;
    background: rgba(255,255,255,0.08); border-radius: 20px;
    font-size: 13px; opacity: 0.75;
  }
  .hero .period .dot { width: 8px; height: 8px; border-radius: 50%; background: #4fc3f7; }
  
  /* ===== 统计卡片 ===== */
  .stats-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
    margin-top: -20px; position: relative; z-index: 2;
  }
  .stat-card {
    background: var(--white); border-radius: var(--radius);
    padding: 24px 20px; text-align: center;
    box-shadow: var(--shadow-md); transition: transform 0.2s, box-shadow 0.2s;
    position: relative; overflow: hidden;
  }
  .stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
  .stat-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px;
  }
  .stat-card.card-notices::before { background: var(--ocean-mid); }
  .stat-card.card-budget::before { background: var(--coral); }
  .stat-card.card-avg::before { background: var(--ocean-light); }
  .stat-card.card-invest::before { background: var(--gold); }
  
  .stat-card .stat-icon { font-size: 28px; margin-bottom: 8px; }
  .stat-card .stat-value {
    font-size: 34px; font-weight: 800; color: var(--ocean-deep);
    line-height: 1.2;
  }
  .stat-card.card-budget .stat-value { color: var(--coral); }
  .stat-card.card-invest .stat-value { color: #d4a017; }
  .stat-card .stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
  .stat-card .stat-unit { font-size: 14px; color: var(--text-muted); font-weight: 400; }
  
  /* ===== 区块通用 ===== */
  .section {
    background: var(--white); border-radius: var(--radius);
    padding: 28px; margin-top: 20px;
    box-shadow: var(--shadow-sm);
  }
  .section-header {
    display: flex; align-items: center; gap: 10px; margin-bottom: 20px;
    padding-bottom: 12px; border-bottom: 1px solid var(--border);
  }
  .section-header .section-icon {
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .section-header .section-icon.icon-chain { background: #e8f4fd; color: var(--upstream); }
  .section-header .section-icon.icon-star { background: #fff3e0; color: var(--midstream); }
  .section-header .section-icon.icon-map { background: #e8f5e9; color: var(--downstream); }
  .section-header .section-icon.icon-gap { background: #fce4ec; color: var(--coral); }
  .section-header .section-icon.icon-building { background: #f3e5f5; color: var(--investment); }
  .section-header h2 { font-size: 18px; font-weight: 700; color: var(--ocean-deep); }
  
  /* ===== 双栏布局 ===== */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  
  /* ===== 图表容器 ===== */
  .chart-wrap { position: relative; width: 100%; }
  .chart-wrap canvas { max-height: 320px; }
  
  /* ===== 产业链小卡片 ===== */
  .chain-mini-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .chain-mini {
    padding: 16px; border-radius: 10px; text-align: center;
    border: 1px solid var(--border); transition: transform 0.2s;
  }
  .chain-mini:hover { transform: translateY(-1px); }
  .chain-mini.upstream { border-left: 3px solid var(--upstream); background: #f5fafe; }
  .chain-mini.midstream { border-left: 3px solid var(--midstream); background: #fef9f4; }
  .chain-mini.downstream { border-left: 3px solid var(--downstream); background: #f4fdf7; }
  .chain-mini.investment { border-left: 3px solid var(--investment); background: #faf5fc; }
  .chain-mini .cm-count { font-size: 26px; font-weight: 800; color: var(--ocean-deep); }
  .chain-mini .cm-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
  
  /* ===== 商机推荐 ===== */
  .opp-list { display: flex; flex-direction: column; gap: 12px; }
  .opp-item {
    display: flex; gap: 16px; align-items: flex-start;
    padding: 18px; border-radius: 10px; border: 1px solid var(--border);
    transition: box-shadow 0.2s, border-color 0.2s;
    background: var(--white);
  }
  .opp-item:hover { box-shadow: var(--shadow-md); border-color: var(--ocean-mid); }
  .opp-rank {
    min-width: 44px; height: 44px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 20px; color: #fff; flex-shrink: 0;
  }
  .opp-rank.rank-1 { background: linear-gradient(135deg, #e74c3c, #c0392b); }
  .opp-rank.rank-2 { background: linear-gradient(135deg, #e67e22, #d35400); }
  .opp-rank.rank-3 { background: linear-gradient(135deg, #f39c12, #e67e22); }
  .opp-rank.rank-other { background: #b0bec5; }
  .opp-body { flex: 1; min-width: 0; }
  .opp-title {
    font-size: 15px; font-weight: 600; color: var(--ocean-deep); margin-bottom: 6px;
    line-height: 1.4;
  }
  .opp-title a { color: inherit; text-decoration: none; }
  .opp-title a:hover { color: var(--ocean-mid); }
  .opp-meta {
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
    font-size: 12px; color: var(--text-muted);
  }
  .opp-meta .meta-item {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 8px; border-radius: 12px; background: var(--surface);
  }
  .opp-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .opp-tag {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; background: #e8f4fd; color: #1976d2;
  }
  .opp-score-row { display: flex; flex-direction: column; align-items: center; gap: 4px; flex-shrink: 0; }
  .opp-score-circle {
    width: 52px; height: 52px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 800; color: #fff;
  }
  .opp-score-circle.high { background: linear-gradient(135deg, #27ae60, #2ecc71); }
  .opp-score-circle.medium { background: linear-gradient(135deg, #f39c12, #f1c40f); }
  .opp-score-circle.low { background: linear-gradient(135deg, #95a5a6, #bdc3c7); }
  .opp-score-label { font-size: 10px; color: var(--text-muted); }
  
  /* ===== 产业链缺口 ===== */
  .gap-list { display: flex; flex-direction: column; gap: 10px; }
  .gap-card {
    display: flex; gap: 14px; align-items: flex-start;
    padding: 16px 18px; border-radius: 10px;
    background: #fffdf5; border: 1px solid #f0e8c0;
    border-left: 4px solid var(--gold);
  }
  .gap-card .gap-icon { font-size: 22px; flex-shrink: 0; margin-top: 2px; }
  .gap-card .gap-type { font-size: 12px; color: #b8860b; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
  .gap-card .gap-desc { font-size: 14px; color: var(--text-primary); margin-top: 2px; }
  .gap-card .gap-opp { font-size: 13px; color: var(--ocean-light); margin-top: 4px; font-weight: 500; }
  
  /* ===== 关键词热度 ===== */
  .kw-cloud { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 0; }
  .kw-tag {
    display: inline-block; padding: 5px 14px; border-radius: 20px;
    font-size: 13px; transition: transform 0.15s;
  }
  .kw-tag:hover { transform: scale(1.08); }
  .kw-tag.xl { font-size: 20px; padding: 8px 20px; }
  .kw-tag.lg { font-size: 17px; padding: 7px 18px; }
  .kw-tag.md { font-size: 14px; }
  .kw-tag.sm { font-size: 12px; }
  .kw-tag.hot { background: #ffebee; color: #c62828; font-weight: 700; }
  .kw-tag.warm { background: #fff3e0; color: #e65100; font-weight: 600; }
  .kw-tag.normal { background: #e8eef5; color: #5a6d7e; }
  
  /* ===== 表格 ===== */
  .data-table { width: 100%; border-collapse: collapse; }
  .data-table thead th {
    background: var(--surface); padding: 12px 16px; text-align: left;
    font-size: 12px; color: var(--text-muted); font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 2px solid var(--border);
  }
  .data-table tbody td {
    padding: 12px 16px; border-bottom: 1px solid var(--surface-alt);
    font-size: 13px; color: var(--text-primary);
  }
  .data-table tbody tr:hover { background: #f8fafc; }
  .data-table tbody tr:last-child td { border-bottom: none; }
  
  /* 评分标签 */
  .score-tag {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 12px; font-weight: 600;
  }
  .score-tag.high { background: #e8f5e9; color: #2e7d32; }
  .score-tag.medium { background: #fff3e0; color: #e65100; }
  .score-tag.low { background: #fce4ec; color: #c62828; }
  
  /* 地区分布 - 简单条形图容器用于 Chart.js */
  .region-chart-wrap { height: 400px; }
  
  /* 产业链金额图 */
  .chain-bar-wrap { height: 300px; }
  
  /* ===== 页脚 ===== */
  .footer {
    text-align: center; padding: 32px 20px; margin-top: 24px;
    color: var(--text-muted); font-size: 13px;
    background: var(--white); border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
  }
  .footer .disclaimer {
    margin-top: 8px; padding: 10px 20px;
    background: #fef9f4; border-radius: 8px;
    display: inline-block; font-size: 12px; color: #b8860b;
  }
  
  /* ===== 响应式 ===== */
  @media (max-width: 768px) {
    .stats-row { grid-template-columns: repeat(2, 1fr); }
    .two-col { grid-template-columns: 1fr; }
    .chain-mini-cards { grid-template-columns: repeat(2, 1fr); }
    .hero h1 { font-size: 22px; }
    .hero { padding: 32px 20px 28px; }
  }
  
  @media print {
    body { background: #fff; }
    .container { padding: 0; }
    .section { box-shadow: none; border: 1px solid #ddd; break-inside: avoid; }
    .hero { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style>
</head>
<body>
<div class="container">

  <!-- ===== 头部 ===== -->
  <div class="hero">
    <div class="hero-inner">
      <div class="issue-badge">
        <span class="num-circle">{{ issue_number }}</span>
        <span>第 <strong>{{ issue_number }}</strong> 期 · 地质海洋招投标情报周报</span>
      </div>
      <h1>广东省地质海洋企业招投标情报周报</h1>
      <p class="subtitle">上下游产业链动态 · 商机识别 · 招商引资节点追踪</p>
      <div class="period">
        <span class="dot"></span>
        {{ period_start }} ~ {{ period_end }}
        <span style="margin:0 4px;opacity:0.5;">|</span>
        生成时间: {{ generated_at }}
      </div>
    </div>
    <div class="hero-waves">
      <svg viewBox="0 0 1440 60" preserveAspectRatio="none">
        <path d="M0,30 C240,50 480,10 720,25 C960,40 1200,15 1440,30 L1440,60 L0,60 Z" fill="#e8eef5" opacity="0.6"/>
        <path d="M0,40 C200,20 500,50 800,35 C1100,20 1300,45 1440,35 L1440,60 L0,60 Z" fill="#f0f4f8" opacity="0.8"/>
        <path d="M0,50 C300,35 600,55 900,45 C1200,35 1350,50 1440,48 L1440,60 L0,60 Z" fill="#f7f9fb"/>
      </svg>
    </div>
  </div>

  <!-- ===== 概览统计 ===== -->
  <div class="stats-row">
    <div class="stat-card card-notices">
      <div class="stat-icon">📋</div>
      <div class="stat-value">{{ overview.total_notices }}</div>
      <div class="stat-unit">条</div>
      <div class="stat-label">本期公告总数</div>
    </div>
    <div class="stat-card card-budget">
      <div class="stat-icon">💰</div>
      <div class="stat-value">{{ "%.1f"|format(overview.total_budget) }}</div>
      <div class="stat-unit">万元</div>
      <div class="stat-label">涉及总金额</div>
    </div>
    <div class="stat-card card-avg">
      <div class="stat-icon">📊</div>
      <div class="stat-value">{{ "%.1f"|format(overview.avg_budget) }}</div>
      <div class="stat-unit">万元</div>
      <div class="stat-label">平均项目金额</div>
    </div>
    <div class="stat-card card-invest">
      <div class="stat-icon">🏗️</div>
      <div class="stat-value">{{ overview.investment_related_count }}</div>
      <div class="stat-unit">条</div>
      <div class="stat-label">招商引资相关</div>
    </div>
  </div>

  <!-- ===== 产业链分布 ===== -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon icon-chain">🔗</div>
      <h2>产业链分布分析</h2>
    </div>
    
    <div class="chain-mini-cards">
      {% for ck in ['upstream','midstream','downstream','investment'] %}
      {% set ci = chain_display.get(ck, {}) %}
      <div class="chain-mini {{ ck }}">
        <div class="cm-count">{{ ci.count|default(0) }}</div>
        <div class="cm-label">{{ ci.name|default('') }}</div>
      </div>
      {% endfor %}
    </div>

    <div class="two-col">
      <!-- 产业链公告数饼图 -->
      <div class="chart-wrap">
        <canvas id="chainPieChart" height="280"></canvas>
      </div>
      <!-- 产业链金额柱状图 -->
      <div class="chart-wrap">
        <canvas id="chainBudgetChart" height="280"></canvas>
      </div>
    </div>

    <!-- 产业链详情表格 -->
    <table class="data-table" style="margin-top:20px;">
      <thead>
        <tr>
          <th>产业链环节</th>
          <th>公告数</th>
          <th>总金额(万)</th>
          <th>平均商机分</th>
          <th>代表项目</th>
        </tr>
      </thead>
      <tbody>
        {% for ck in ['upstream','midstream','downstream','investment'] %}
        {% set ci = chain_display.get(ck, {}) %}
        <tr>
          <td><strong>{{ ci.name|default('') }}</strong></td>
          <td>{{ ci.count|default(0) }}</td>
          <td>{{ "%.0f"|format(ci.budget|default(0)) }}</td>
          <td>
            <span class="score-tag {{ 'high' if ci.avg_score|default(0) >= 60 else ('medium' if ci.avg_score|default(0) >= 30 else 'low') }}">
              {{ "%.1f"|format(ci.avg_score|default(0)) }}
            </span>
          </td>
          <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {% set items = ci.notice_items|default([]) %}
            {{ items[0].title|default('-')|truncate(40) if items else '-' }}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- ===== 商机推荐 TOP ===== -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon icon-star">⭐</div>
      <h2>商机推荐 TOP {{ top_opportunities|length }}</h2>
    </div>
    
    {% if top_opportunities %}
    <div class="opp-list">
      {% for opp in top_opportunities %}
      <div class="opp-item">
        <div class="opp-rank {{ 'rank-1' if loop.index == 1 else ('rank-2' if loop.index == 2 else ('rank-3' if loop.index == 3 else 'rank-other')) }}">
          {{ loop.index }}
        </div>
        <div class="opp-body">
          <div class="opp-title">
            <a href="{{ opp.source_url }}" target="_blank">{{ opp.title[:80] }}</a>
          </div>
          <div class="opp-meta">
            <span class="meta-item">📍 {{ opp.region or '广东' }}</span>
            <span class="meta-item">📅 {{ opp.publish_date or '-' }}</span>
            <span class="meta-item">💵 {{ opp.budget or '-' }}万</span>
            <span class="meta-item">{{ opp.notice_type or '招标公告' }}</span>
            {% if opp.is_investment_related %}
            <span class="meta-item" style="background:#fef3e2;color:#b8860b;">🏗️ 招商引资</span>
            {% endif %}
          </div>
          {% if opp.keywords_list %}
          <div class="opp-tags">
            {% for kw in opp.keywords_list %}
            <span class="opp-tag">{{ kw }}</span>
            {% endfor %}
          </div>
          {% endif %}
        </div>
        <div class="opp-score-row">
          <div class="opp-score-circle {{ 'high' if opp.opportunity_score >= 70 else ('medium' if opp.opportunity_score >= 40 else 'low') }}">
            {{ opp.opportunity_score or 0 }}
          </div>
          <div class="opp-score-label">商机评分</div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p style="color:var(--text-muted);text-align:center;padding:30px;">暂无商机数据，请先执行数据采集。</p>
    {% endif %}
  </div>

  <!-- ===== 可视化分析区 ===== -->
  <div class="two-col">
    <!-- 地区分布 -->
    <div class="section">
      <div class="section-header">
        <div class="section-icon icon-map">🗺️</div>
        <h2>地区分布</h2>
      </div>
      <div class="region-chart-wrap">
        <canvas id="regionChart"></canvas>
      </div>
    </div>
    
    <!-- 评分分布 -->
    <div class="section">
      <div class="section-header">
        <div class="section-icon icon-star">📈</div>
        <h2>商机评分分布</h2>
      </div>
      <div class="chart-wrap">
        <canvas id="scoreDistChart" height="280"></canvas>
      </div>
    </div>
  </div>

  <!-- ===== 关键词热度 ===== -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:#e8f4fd;color:#1976d2;">🔥</div>
      <h2>关键词热度排行</h2>
    </div>
    {% if keyword_freq %}
    <div class="kw-cloud">
      {% for kw, freq in keyword_freq %}
      {% set size = 'xl' if freq >= 8 else ('lg' if freq >= 5 else ('md' if freq >= 3 else 'sm')) %}
      {% set heat = 'hot' if freq >= 5 else ('warm' if freq >= 3 else 'normal') %}
      <span class="kw-tag {{ size }} {{ heat }}">{{ kw }} <small>({{ freq }})</small></span>
      {% endfor %}
    </div>
    {% else %}
    <p style="color:var(--text-muted);text-align:center;">暂无关键词数据。</p>
    {% endif %}
  </div>

  <!-- ===== 产业链缺口分析 ===== -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon icon-gap">⚠️</div>
      <h2>产业链衔接缺口分析</h2>
    </div>
    {% if chain_gaps %}
    <div class="gap-list">
      {% for gap in chain_gaps %}
      <div class="gap-card">
        <div class="gap-icon">🔍</div>
        <div>
          <div class="gap-type">{{ gap.type }}</div>
          <div class="gap-desc">{{ gap.description }}</div>
          <div class="gap-opp">💡 商机建议: {{ gap.opportunity }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p style="color:var(--text-muted);text-align:center;">暂无缺口数据。</p>
    {% endif %}
  </div>

  <!-- ===== 活跃主体 ===== -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon icon-building">🏢</div>
      <h2>活跃招标/中标主体</h2>
    </div>
    {% if top_entities %}
    <table class="data-table">
      <thead>
        <tr><th>企业名称</th><th>类型</th><th>出现次数</th><th>涉及金额(万)</th><th>产业链</th></tr>
      </thead>
      <tbody>
        {% for entity in top_entities %}
        <tr>
          <td><strong>{{ entity.name }}</strong></td>
          <td>{{ entity.entity_type or '-' }}</td>
          <td>{{ entity.appear_count }}</td>
          <td>{{ "%.1f"|format(entity.total_budget) }}</td>
          <td>{{ entity.chain_position or '-' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p style="color:var(--text-muted);text-align:center;">暂无企业数据。</p>
    {% endif %}
  </div>

  <!-- ===== 页脚 ===== -->
  <div class="footer">
    <p>广东省地质海洋企业招投标情报系统 · 第{{ issue_number }}期 · 自动生成于 {{ generated_at }}</p>
    <p style="margin-top:4px;">数据来源: 广东省招标投标监管网 · 广州公共资源交易中心 · 中国招标投标公共服务平台 · 广东省公共资源交易平台</p>
    <p class="disclaimer">⚠️ 本报告由系统自动采集公开招标信息并分析生成，仅供参考。投资决策请以官方公告为准。</p>
  </div>

</div>

<!-- ===== Chart.js 初始化 ===== -->
<script>
(function() {
  const colors = {
    upstream: '#3498db',
    midstream: '#e67e22', 
    downstream: '#27ae60',
    investment: '#8e44ad',
  };
  const chainNames = {
    upstream: '上游·勘探与装备',
    midstream: '中游·工程与施工',
    downstream: '下游·监测与服务',
    investment: '招商引资',
  };

  // ===== 产业链公告数饼图 =====
  const chainData = {{ chain_chart_data|tojson }};
  (function() {
    const labels = chainData.map(d => chainNames[d.key] || d.key);
    const counts = chainData.map(d => d.count);
    const bgColors = chainData.map(d => colors[d.key] || '#95a5a6');
    const ctx = document.getElementById('chainPieChart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: counts,
          backgroundColor: bgColors,
          borderColor: '#ffffff',
          borderWidth: 3,
          hoverBorderWidth: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { padding: 20, usePointStyle: true, pointStyleWidth: 10, font: { size: 13 } }
          },
          title: {
            display: true,
            text: '公告数分布',
            font: { size: 15, weight: 'bold' },
            color: '#1a2a3a',
            padding: { bottom: 16 }
          }
        },
      }
    });
  })();

  // ===== 产业链金额柱状图 =====
  (function() {
    const labels = chainData.map(d => chainNames[d.key] || d.key);
    const budgets = chainData.map(d => Math.round(d.budget || 0));
    const bgColors = chainData.map(d => colors[d.key] || '#95a5a6');
    const ctx = document.getElementById('chainBudgetChart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '总金额(万元)',
          data: budgets,
          backgroundColor: bgColors.map(c => c + '99'),
          borderColor: bgColors,
          borderWidth: 2,
          borderRadius: 8,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: '各环节涉及金额',
            font: { size: 15, weight: 'bold' },
            color: '#1a2a3a',
            padding: { bottom: 16 }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#e8eef5' },
            ticks: { callback: v => v >= 10000 ? (v/10000).toFixed(1)+'亿' : v+'万' }
          }
        }
      }
    });
  })();

  // ===== 地区分布横向柱状图 =====
  const regionData = {{ region_chart_data|tojson }};
  (function() {
    if (!regionData || regionData.length === 0) return;
    const labels = regionData.map(d => d.name);
    const counts = regionData.map(d => d.count);
    const ctx = document.getElementById('regionChart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '公告数',
          data: counts,
          backgroundColor: counts.map((_, i) => {
            const t = i / Math.max(counts.length - 1, 1);
            return `hsla(${200 + t * 40}, 60%, ${55 - t * 10}%, 0.85)`;
          }),
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: '#e8eef5' },
            ticks: { stepSize: 1 }
          }
        }
      }
    });
  })();

  // ===== 商机评分分布柱状图 =====
  const scoreData = {{ score_dist_data|tojson }};
  (function() {
    const labels = ['0-20', '21-40', '41-60', '61-80', '81-100'];
    const ctx = document.getElementById('scoreDistChart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '公告数量',
          data: scoreData,
          backgroundColor: [
            'rgba(231,76,60,0.7)',
            'rgba(230,126,34,0.7)',
            'rgba(241,196,15,0.7)',
            'rgba(46,204,113,0.7)',
            'rgba(39,174,96,0.85)',
          ],
          borderColor: [
            '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60'
          ],
          borderWidth: 2,
          borderRadius: 8,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: '公告评分区间',
            font: { size: 15, weight: 'bold' },
            color: '#1a2a3a',
            padding: { bottom: 16 }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#e8eef5' },
            ticks: { stepSize: 1 }
          }
        }
      }
    });
  })();

})();
</script>
</body>
</html>"""


class ReportGenerator:
    """报告生成器"""

    def __init__(self, report_dir: str, db_path: str):
        self.report_dir = report_dir
        self.db_path = db_path
        os.makedirs(report_dir, exist_ok=True)

    def generate(self, summary: dict, chain_gaps: list = None, issue_number: int = 1) -> str:
        """生成HTML报告"""
        if chain_gaps is None:
            chain_gaps = []

        # 准备模板数据
        chain_display = {}
        chain_chart_data = []
        for chain_key, chain_info in {
            "upstream": {"name": "上游·勘探与装备", "description": "地质勘探、海洋调查、装备制造"},
            "midstream": {"name": "中游·工程与施工", "description": "海洋工程、地质施工、港口航道"},
            "downstream": {"name": "下游·监测与服务", "description": "环境监测、技术服务、数据信息"},
            "investment": {"name": "招商引资", "description": "产业园区、投资合作、特许经营"},
        }.items():
            stats = summary.get("chain_stats", {}).get(chain_key, {})
            items = summary.get("chain_details", {}).get(chain_key, [])
            count = stats.get("count", 0)
            budget = stats.get("total_budget", 0) or 0
            avg_score = stats.get("avg_score", 0) or 0
            chain_display[chain_key] = {
                "name": chain_info["name"],
                "description": chain_info["description"],
                "count": count,
                "budget": budget,
                "avg_score": avg_score,
                "notice_items": items,
            }
            chain_chart_data.append({
                "key": chain_key,
                "count": count,
                "budget": budget,
            })

        # 地区统计数据 -> chart format
        region_stats = summary.get("region_stats", {})
        max_region_count = max((v["count"] for v in region_stats.values()), default=1) if region_stats else 1
        region_chart_data = [
            {"name": region, "count": data["count"]}
            for region, data in sorted(region_stats.items(), key=lambda x: -x[1]["count"])
        ]

        # 评分分布数据
        top_opps = summary.get("top_opportunities", []) or []
        score_dist = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
        all_chain_items = []
        for ck in chain_display:
            all_chain_items.extend(chain_display[ck].get("notice_items", []))
        for item in all_chain_items:
            s = item.get("opportunity_score", 0) or 0
            if s <= 20: score_dist[0] += 1
            elif s <= 40: score_dist[1] += 1
            elif s <= 60: score_dist[2] += 1
            elif s <= 80: score_dist[3] += 1
            else: score_dist[4] += 1

        # 合并企业列表
        top_entities = (summary.get("top_tenderers", []) or [])[:10] + \
                       (summary.get("top_winners", []) or [])[:5]

        # 预处理商机数据: 解析 matched_keywords JSON 为列表
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
        env = Environment()
        env.filters["from_json"] = lambda s: json.loads(s) if s else []
        template = env.from_string(REPORT_TEMPLATE)

        html = template.render(
            issue_number=issue_number,
            report_date=datetime.now().strftime("%Y-%m-%d"),
            period_start=summary.get("period", {}).get("start", ""),
            period_end=summary.get("period", {}).get("end", ""),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            db_path=self.db_path,
            overview=summary.get("overview", {}),
            chain_display=chain_display,
            chain_chart_data=chain_chart_data,
            region_chart_data=region_chart_data,
            score_dist_data=score_dist,
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
