# -*- coding: utf-8 -*-
"""
演示数据生成器 - 生成模拟招标数据用于系统测试和展示
"""

import random
import json
from datetime import datetime, timedelta
from config import KEYWORDS_UPSTREAM, KEYWORDS_MIDSTREAM, KEYWORDS_DOWNSTREAM, \
    KEYWORDS_INVESTMENT, REGIONS
import hashlib


# 模拟项目模板
PROJECT_TEMPLATES = {
    "upstream": [
        "广州市{region}海域地质勘探项目",
        "广东省{region}近海海洋地质调查服务采购",
        "{region}港口航道水深测量及海底地形测绘工程",
        "南海北部{region}海域地球物理勘探项目",
        "{region}海洋牧场选址地质勘察服务",
        "广东省{region}海岸带地质环境综合调查",
        "{region}深海矿产资源勘查技术服务采购",
        "海洋调查船设备升级改造项目",
        "{region}海域使用论证海底地质调查",
        "广东省地质灾害隐患点勘查{region}片区项目",
    ],
    "midstream": [
        "{region}海上风电场基础施工及海底电缆敷设工程",
        "广州港{region}港区航道疏浚工程",
        "{region}跨海大桥桩基及海底隧道工程EPC总承包",
        "广东省{region}海洋牧场建设施工项目",
        "{region}海堤加固及防波堤建设工程",
        "{region}港口码头水工建筑物施工",
        "海上风电{region}海域送出工程总承包",
        "{region}海底管道铺设及防护工程",
        "广东省{region}海岸带保护修复工程",
        "{region}海洋经济示范区基础设施EPC",
    ],
    "downstream": [
        "{region}海域海洋环境监测系统建设",
        "广东省{region}海洋生态修复技术服务",
        "{region}地质灾害监测预警系统采购",
        "{region}海洋大数据平台建设项目",
        "广东省{region}智慧海洋信息系统集成",
        "{region}海岸线动态监测遥感服务",
        "{region}海洋预报减灾体系建设",
        "广东省{region}地质资料数字化及数据库建设",
        "{region}海洋工程设施运维服务",
        "{region}海域生态环境跟踪评估",
    ],
    "investment": [
        "{region}海洋经济产业园招商引资PPP项目",
        "广东省{region}海洋科技园区BOT建设运营",
        "{region}海洋装备制造产业基地特许经营",
        "{region}深海产业EPC+O项目招商",
        "广东省{region}海洋经济示范区产业基金合作",
    ],
}

# 模拟企业名称
TENDERERS = [
    "广州市自然资源局", "广东省地质调查局", "广州海洋地质调查局",
    "深圳市规划和自然资源局", "珠海市海洋综合执法支队",
    "湛江市港口管理局", "广东省海洋综合开发研究院",
    "汕头市交通运输局", "广东省发改委", "阳江市海洋发展局",
    "茂名市自然资源局", "江门市水利局", "惠州市海事局",
]

AGENCIES = [
    "广东采联采购科技有限公司", "广东省机电设备招标中心",
    "广州市国科招标代理有限公司", "中经国际招标集团广东分公司",
    "广东省广大工程招标有限公司", "深圳市国际招标有限公司",
]

WINNERS = [
    "广东省地质物探工程勘察院", "中交第四航务工程局有限公司",
    "广州海洋地质勘查开发有限公司", "自然资源部南海局",
    "中船重工（广州）海洋装备有限公司", "广东省工程勘察院",
    "中海油能源发展股份有限公司", "广州打捞局",
    "中交广州航道局有限公司", "广东省大亚湾海洋科技有限公司",
]


def generate_demo_data(days: int = 14, count: int = 60) -> list:
    """生成模拟招标数据"""
    notices = []
    now = datetime.now()
    all_templates = []
    
    for chain, templates in PROJECT_TEMPLATES.items():
        for t in templates:
            all_templates.append((chain, t))

    for i in range(count):
        chain, template = random.choice(all_templates)
        region = random.choice(list(REGIONS.values()))
        title = template.format(region=region)
        
        # 随机日期(最近days天内)
        pub_date = now - timedelta(days=random.randint(0, days - 1))
        
        # 随机金额
        budget = random.choice([
            random.uniform(50, 200),      # 小项目
            random.uniform(200, 1000),     # 中等项目
            random.uniform(1000, 5000),    # 大项目
            random.uniform(5000, 30000),   # 重大项目
        ])
        
        # 随机关键词
        keyword_pool = {
            "upstream": KEYWORDS_UPSTREAM,
            "midstream": KEYWORDS_MIDSTREAM,
            "downstream": KEYWORDS_DOWNSTREAM,
            "investment": KEYWORDS_INVESTMENT,
        }
        matched_kws = random.sample(keyword_pool[chain], min(random.randint(2, 6), len(keyword_pool[chain])))
        
        # 部分项目有中标信息
        has_winner = random.random() < 0.4
        winner = random.choice(WINNERS) if has_winner else ""
        win_amount = budget * random.uniform(0.8, 1.0) if has_winner else 0
        
        notice_id = hashlib.md5(f"{title}_{pub_date.strftime('%Y%m%d')}_{i}".encode()).hexdigest()[:16]
        
        notices.append({
            "notice_id": notice_id,
            "title": title,
            "source": random.choice(["gd_zbtb", "gz_ggzy", "national", "bidcenter"]),
            "source_url": f"https://www.gzggzy.cn/jyywjsgcfwjzzbgg/{random.randint(1000000, 9999999)}.jhtml",
            "notice_type": random.choice(["招标公告", "中标公告", "变更公告", "招标预告"]),
            "project_name": title,
            "project_code": f"GD-{now.year}-{random.randint(1000, 9999)}",
            "region": region,
            "budget": round(budget, 2),
            "publish_date": pub_date.strftime("%Y-%m-%d"),
            "deadline_date": (pub_date + timedelta(days=random.randint(7, 30))).strftime("%Y-%m-%d"),
            "tenderer": random.choice(TENDERERS),
            "agency": random.choice(AGENCIES),
            "winner": winner,
            "win_amount": round(win_amount, 2),
            "content": f"本项目涉及{title}，项目位于{region}，主要内容包括{', '.join(matched_kws[:3])}等相关工作。",
            "collected_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return notices


if __name__ == "__main__":
    data = generate_demo_data(days=14, count=60)
    print(f"生成 {len(data)} 条演示数据")
    for d in data[:3]:
        print(json.dumps(d, ensure_ascii=False, indent=2))
