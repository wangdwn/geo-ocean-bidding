# -*- coding: utf-8 -*-
"""Ocean Series shared chrome: design-system CSS links + sticky A/B/C/D nav.

This repo is a 经营盘 (Pan B) submodule (招标雷达). Link the live CSS from
https://wangdwn.github.io/design-system/ — do not copy tokens.
"""

DS_HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://wangdwn.github.io/design-system/tokens.css">
<link rel="stylesheet" href="https://wangdwn.github.io/design-system/nav.css">"""

OS_NAV = """<nav class="os-nav" aria-label="海洋系列">
  <div class="os-nav__inner">
    <a class="os-nav__brand" href="https://wangdwn.github.io/">
      <span class="os-nav__mark" aria-hidden="true"></span>
      <span class="os-nav__brand-text">海洋系列</span>
    </a>
    <div class="os-nav__pills">
      <a class="os-nav__pill os-nav__pill--a" href="https://wangdwn.github.io/guangzhou-marine-enterprises/">A 家底</a>
      <a class="os-nav__pill os-nav__pill--b is-current" href="https://wangdwn.github.io/marine-monitor/" aria-current="page">B 经营</a>
      <a class="os-nav__pill os-nav__pill--c" href="https://wangdwn.github.io/guangzhou-ocean-dashboard/">C 质量</a>
      <a class="os-nav__pill os-nav__pill--d" href="https://wangdwn.github.io/marine-weekly/">D 底座</a>
    </div>
    <a class="os-nav__ds" href="https://wangdwn.github.io/design-system/">设计系统</a>
  </div>
</nav>"""
