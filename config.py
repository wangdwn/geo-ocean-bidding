# -*- coding: utf-8 -*-
"""
广东省地质海洋企业招投标情报系统 - 配置文件
"""

import os

# ===== 路径配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# 数据库路径
DB_PATH = os.path.join(DATA_DIR, "bidding_intel.db")

# ===== 地质海洋产业链关键词体系 =====
# 上游：地质勘探、海洋装备、材料
KEYWORDS_UPSTREAM = [
    "地质勘探", "地质勘查", "地质调查", "海洋调查", "海洋地质",
    "地球物理勘探", "地球化学勘探", "遥感地质", "钻探", "岩土工程",
    "海洋测绘", "海底测绘", "水深测量", "地形测量",
    "海洋装备", "海洋工程装备", "水下机器人", "ROV", "AUV",
    "海洋传感器", "海洋监测设备", "海洋仪器",
    "钻机", "钻探设备", "取芯", "岩芯",
    "物探船", "调查船", "测量船", "工程船",
    "防腐材料", "海洋涂料", "海底电缆", "海底光缆",
]

# 中游：海洋工程、地质工程、施工
KEYWORDS_MIDSTREAM = [
    "海洋工程", "海上风电", "海上平台", "海洋牧场",
    "海底隧道", "跨海大桥", "港口建设", "码头工程",
    "航道疏浚", "海底管道", "海底电缆敷设",
    "海洋油气", "海上钻井", "采油平台",
    "地质灾害防治", "地质灾害评估", "地质灾害治理",
    "边坡治理", "基坑支护", "地基处理", "桩基工程",
    "岩土施工", "注浆加固", "基坑降水",
    "防波堤", "护岸工程", "海堤建设",
    "海洋牧场", "深海养殖", "海洋渔业设施",
    "海水淡化", "海洋能发电", "潮汐能",
]

# 下游：运营维护、技术服务、监测
KEYWORDS_DOWNSTREAM = [
    "海洋监测", "海洋环境监测", "海洋生态修复",
    "海域使用论证", "海洋环境影响评价", "海域评估",
    "地质灾害监测", "地质灾害预警", "地面沉降监测",
    "工程测量", "变形监测", "沉降观测",
    "海洋预报", "海洋气象", "海洋信息服务",
    "地质资料", "地质数据库", "地质信息系统",
    "海洋数据", "海洋大数据", "智慧海洋",
    "运维服务", "设施维护", "设备检修",
    "海洋咨询", "地质咨询", "技术咨询",
]

# 招商引资关键词
KEYWORDS_INVESTMENT = [
    "招商引资", "产业园区", "海洋经济示范区",
    "海洋产业园", "地质装备产业园", "海洋科技园",
    "产业基金", "投资合作", "PPP", "BOT",
    "EPC", "总承包", "特许经营",
]

# 全部关键词
ALL_KEYWORDS = KEYWORDS_UPSTREAM + KEYWORDS_MIDSTREAM + KEYWORDS_DOWNSTREAM + KEYWORDS_INVESTMENT

# ===== 产业链分类映射 =====
INDUSTRY_CHAIN_MAP = {
    "upstream": {
        "name": "上游·勘探与装备",
        "keywords": KEYWORDS_UPSTREAM,
        "description": "地质勘探、海洋调查、装备制造、材料供应",
    },
    "midstream": {
        "name": "中游·工程与施工",
        "keywords": KEYWORDS_MIDSTREAM,
        "description": "海洋工程、地质施工、港口航道、海上能源",
    },
    "downstream": {
        "name": "下游·监测与服务",
        "keywords": KEYWORDS_DOWNSTREAM,
        "description": "环境监测、技术服务、数据信息、运维咨询",
    },
    "investment": {
        "name": "招商引资",
        "keywords": KEYWORDS_INVESTMENT,
        "description": "产业园区、投资合作、特许经营",
    },
}

# ===== 数据源配置 =====
SOURCES = {
    "gd_zbtb": {
        "name": "广东省招标投标监管网",
        "base_url": "https://www.gdzwfw.gov.cn/ztbjg-portal",
        "search_url": "https://www.gdzwfw.gov.cn/ztbjg-portal/api/xxgggs/list",
        "type": "api",
        "enabled": True,
    },
    "gd_ggzy": {
        "name": "广东省公共资源交易平台",
        "base_url": "https://ygp.gdzwfw.gov.cn",
        "search_url": "https://ygp.gdzwfw.gov.cn/ggzy-portal/api/v1/notice/searchNotice",
        "type": "api",
        "enabled": True,
    },
    "gz_ggzy": {
        "name": "广州公共资源交易中心",
        "base_url": "https://www.gzggzy.cn",
        "search_url": "https://www.gzggzy.cn/jyywjsgcfwjzzbgg/index.jhtml",
        "type": "html",
        "enabled": True,
    },
    "national": {
        "name": "中国招标投标公共服务平台",
        "base_url": "http://www.cebpubservice.com",
        "search_url": "http://www.cebpubservice.com/ctpsp_iiss/acceptdefault/acceptinfo/acceptinfoserachbypage.jsp",
        "type": "api",
        "enabled": True,
    },
}

# ===== 爬虫配置 =====
CRAWLER_CONFIG = {
    "request_delay": 2,        # 请求间隔(秒)
    "timeout": 30,              # 请求超时(秒)
    "max_pages": 20,            # 每个关键词最大翻页数
    "max_retries": 3,           # 最大重试次数
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "search_days": 7,           # 搜索最近N天的公告
}

# ===== 分析配置 =====
ANALYSIS_CONFIG = {
    # 商机评分权重
    "score_weights": {
        "budget": 0.30,          # 预算金额权重
        "keyword_relevance": 0.25,  # 关键词相关度
        "chain_coverage": 0.20,   # 产业链覆盖度
        "recency": 0.15,         # 时效性
        "investment_potential": 0.10,  # 招商引资潜力
    },
    # 金额阈值(万元)
    "budget_thresholds": {
        "high": 5000,     # 5000万以上为高
        "medium": 1000,   # 1000-5000万为中
        "low": 100,       # 100-1000万为低
    },
    # 报告中每个分类最多展示条目
    "max_items_per_category": 15,
}

# ===== 地区配置 =====
REGIONS = {
    "guangzhou": "广州市",
    "shenzhen": "深圳市",
    "zhuhai": "珠海市",
    "shantou": "汕头市",
    "foshan": "佛山市",
    "shaoguan": "韶关市",
    "zhanjiang": "湛江市",
    "zhaoqing": "肇庆市",
    "jiangmen": "江门市",
    "maoming": "茂名市",
    "huizhou": "惠州市",
    "meizhou": "梅州市",
    "shanwei": "汕尾市",
    "heyuan": "河源市",
    "yangjiang": "阳江市",
    "qingyuan": "清远市",
    "dongguan": "东莞市",
    "zhongshan": "中山市",
    "chaozhou": "潮州市",
    "jieyang": "揭阳市",
    "yunfu": "云浮市",
}
