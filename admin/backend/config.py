from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DASHSCOPE_API_KEY: str = "YOUR_DASHSCOPE_API_KEY"

    ALIYUN_ACCESS_KEY_ID: str = "YOUR_ACCESS_KEY_ID"
    ALIYUN_ACCESS_KEY_SECRET: str = "YOUR_ACCESS_KEY_SECRET"

    AVATAR_ENDPOINT: str = "avatar.cn-zhangjiakou.aliyuncs.com"
    AVATAR_APP_ID: str = "YOUR_APP_ID"
    AVATAR_TENANT_ID: str = "YOUR_TENANT_ID"

    # D-ID Streaming（无GPU时的数字人方案）
    DID_API_KEY: str = "YOUR_DID_API_KEY"
    DID_AVATAR_URL: str = ""   # 万相生成后自动写入

    class Config:
        env_file = ".env"


settings = Settings()

# 五类景区主题配置
SCENE_THEMES = {
    "buddhist": {
        "name": "佛教文化类",
        "example": "灵山胜境、峨眉山、九华山",
        "avatar_prompt": (
            "中国女性景区讲解员，身穿米白色绣金边汉服，发髻端正，金色发饰，"
            "面容温柔，微笑自然，正面直视镜头，"
            "柔和均匀室内自然光，简洁米色渐变虚化背景，"
            "专业人像摄影，照片级真实感，半身像，4K超清"
        ),
        "avatar_negative": "卡通，插画，油画，二次元，夸张表情，侧脸，复杂背景，寺庙建筑，强烈阴影，低质量，模糊，变形",
        "colors": {
            "primary": "#C9A84C",
            "secondary": "#8B1A1A",
            "background": "#1A0A00",
            "surface": "#2D1500",
            "text": "#F5E6C8",
            "accent": "#FFD700"
        },
        "decoration": "lotus",
        "greeting": "阿弥陀佛，欢迎来到灵山胜境。我是您的AI导览师，请问您想了解哪处圣境？"
    },
    "nature": {
        "name": "自然山水类",
        "example": "张家界、黄山、九寨沟",
        "avatar_prompt": (
            "中国女性景区导游，身穿翠绿色改良汉服，丸子头发型，"
            "面容清纯甜美，微笑自然，正面直视镜头，"
            "柔和均匀自然光，简洁浅绿色渐变虚化背景，"
            "专业人像摄影，照片级真实感，半身像，4K超清"
        ),
        "avatar_negative": "卡通，插画，二次元，夸张表情，侧脸，复杂背景，山水风景，强烈阴影，低质量，模糊，变形",
        "colors": {
            "primary": "#2D9E6B",
            "secondary": "#1B6B8A",
            "background": "#071A10",
            "surface": "#0D2B1A",
            "text": "#D4F5E2",
            "accent": "#52E5A0"
        },
        "decoration": "leaf",
        "greeting": "您好，欢迎来到这片钟灵毓秀的自然天地！我是您的AI导览师，随时为您讲解山水奥秘。"
    },
    "ancient_town": {
        "name": "古镇民俗类",
        "example": "乌镇、凤凰古城、丽江古城",
        "avatar_prompt": (
            "中国女性景区讲解员，身穿粉蓝色改良旗袍，发插珠钗，"
            "面容甜美端庄，亲切微笑，正面直视镜头，"
            "柔和均匀自然光，简洁暖米色渐变虚化背景，"
            "专业人像摄影，照片级真实感，半身像，4K超清"
        ),
        "avatar_negative": "卡通，插画，二次元，夸张表情，侧脸，古镇建筑背景，复杂背景，强烈阴影，低质量，模糊，变形",
        "colors": {
            "primary": "#C0392B",
            "secondary": "#7D4E2D",
            "background": "#0D0A08",
            "surface": "#1E1410",
            "text": "#FAF0E6",
            "accent": "#E8A87C"
        },
        "decoration": "ink",
        "greeting": "欢迎来到古镇！我是您的AI导览师，且听我为您讲述这方水土的千年故事。"
    },
    "historical": {
        "name": "历史遗址类",
        "example": "故宫、兵马俑、圆明园",
        "avatar_prompt": (
            "中国女性景区讲解员，身穿深蓝色暗纹汉服，发髻端正，"
            "气质沉稳优雅，微笑，正面直视镜头，"
            "柔和均匀自然光，简洁深蓝色渐变虚化背景，"
            "专业人像摄影，照片级真实感，半身像，4K超清"
        ),
        "avatar_negative": "卡通，插画，二次元，夸张表情，侧脸，历史建筑背景，复杂背景，强烈阴影，低质量，模糊，变形",
        "colors": {
            "primary": "#B8860B",
            "secondary": "#1B3A5C",
            "background": "#0A0A0A",
            "surface": "#161210",
            "text": "#F4E4C1",
            "accent": "#CD9A3A"
        },
        "decoration": "bronze",
        "greeting": "欢迎光临！我是您的AI导览师，将带您穿越历史长河，感受华夏文明的厚重积淀。"
    },
    "modern": {
        "name": "现代主题类",
        "example": "科技馆、主题乐园、现代博物馆",
        "avatar_prompt": (
            "中国女性景区讲解员，身穿简洁深色职业套装，"
            "精致妆容，形象干练，面带专业微笑，正面直视镜头，"
            "柔和均匀室内自然光，简洁浅灰色渐变虚化背景，"
            "专业人像摄影，照片级真实感，半身像，4K超清"
        ),
        "avatar_negative": "卡通，插画，二次元，夸张表情，侧脸，科技场景背景，复杂背景，强烈阴影，低质量，模糊，变形",
        "colors": {
            "primary": "#0052CC",
            "secondary": "#00B4D8",
            "background": "#05070F",
            "surface": "#0D1117",
            "text": "#E8F4FD",
            "accent": "#00D4FF"
        },
        "decoration": "circuit",
        "greeting": "欢迎！我是您的AI导览师，随时为您提供专业、精准的讲解服务。"
    }
}
