"""通用 F/M + 换装 形象「人景一体」批量生成（万相 t2i-turbo，云端 0 GPU）。
复用 /digital-human/generate 的半身构图模板（比例自然、完整），固定 seed/形象减跨景区漂移。
用法: gen_fm_wanx.py <scenics逗号分隔|all> <aspects:16x9,9x16|16x9> <outdir> [deploy:0|1]
  deploy=1 直接落 ditto_avatars(<base>__<scenic>__<aspect>.png)；否则落 outdir 供预览。
"""
import sys, os, time
from io import BytesIO

SCENICS_ALL = ["lingshan", "nihuawan", "xihu", "mogaoku", "zhangjiajie", "bingmayong", "huangshan", "gugong"]
SCENE = {
    "lingshan": "灵山胜境青翠群山与缭绕薄雾，古朴禅意的中式亭台楼阁，远处太湖烟波，宁静秀美的真实自然山水园林",
    "nihuawan": "拈花湾禅意小镇的唐风街巷",
    "xihu": "西湖烟雨与断桥远景", "huangshan": "黄山云海与奇松", "gugong": "故宫红墙金瓦的宫廷",
    "zhangjiajie": "张家界石英砂岩峰林", "bingmayong": "兵马俑军阵展厅", "mogaoku": "敦煌莫高窟与鸣沙山",
}
# 高颜值面部描述（参考抽奖提示词，按性别/年龄适配）
_F_YOUNG = ("年轻貌美的二十岁妙龄少女，闭月羞花倾国倾城的绝美容颜，精致漂亮的瓜子脸，小巧尖下巴，"
            "流畅匀称的脸部线条，饱满苹果肌减龄甜美，水汪汪明亮灵动的双眼皮大眼睛，又长又翘的睫毛，"
            "小巧精致挺翘的鼻子，饱满水润的樱唇，皮肤白皙嫩滑吹弹可破，清纯甜美惊艳动人，超高颜值绝世美女")
_F_MATURE = ("年轻知性的绝美女子，闭月羞花的精致容颜，秀美的瓜子脸，明亮有神的大眼睛，皮肤白皙细腻，"
             "优雅高贵端庄，气质从容知性，超高颜值美女")
_M_FACE = "英俊帅气，五官立体深邃，剑眉星目，轮廓分明，皮肤干净清爽，超高颜值"
# 用户补充：发量较多、正面对镜头、时尚发型（圈中达标的 F5/coat 保持原样不加）
_HAIR = "，浓密丰盈的一头秀发，时尚精致好看的发型，完全正面对着镜头"
_F_YOUNG_H = _F_YOUNG + _HAIR
_F_MATURE_H = _F_MATURE + _HAIR
# (deploy_base, gender, face_desc, outfit_desc, seed)
AVATARS = [
    ("F1_modern", "女", _F_YOUNG_H, "身着海军蓝职业西装外套，知性专业", 1001),
    ("F2_hanfu", "女", _F_YOUNG_H, "身着传统汉服襦裙，温婉古典", 1002),
    ("F3_youth", "女", _F_YOUNG_H, "身着景区志愿者马甲，青春活力", 1003),
    ("F4_qipao", "女", _F_YOUNG_H, "身着优雅改良旗袍，端庄秀美", 1004),
    ("F5_ethnic", "女", _F_YOUNG, "身着鲜艳少数民族服饰与银饰，民族风情", 1005),  # 圈中达标·保留
    ("F6_mature", "女", _F_MATURE_H, "身着高级职业套装，知性资深", 1006),
    ("M1_modern", "男", _M_FACE, "身着浅色衬衫与西装，儒雅亲和", 1007),
    ("M2_scholar", "男", _M_FACE, "身着传统青衫长袍，文士书卷气", 1008),
    ("M3_youth", "男", _M_FACE, "身着景区导览制服，青年阳光", 1009),
    ("M4_business", "男", _M_FACE, "身着正式深色西装，商务干练", 1010),
    ("sweet_outfit_qipao", "女", _F_YOUNG_H, "身着精致旗袍", 1011),
    ("sweet_outfit_hanfu", "女", _F_YOUNG_H, "身着唐风汉服", 1012),
    ("sweet_outfit_blazer", "女", _F_YOUNG_H, "身着职业西装", 1013),
    ("sweet_outfit_ethnic", "女", _F_YOUNG_H, "身着少数民族服饰", 1014),
    ("sweet_outfit_vest", "女", _F_YOUNG_H, "身着景区导览马甲", 1015),
    ("sweet_outfit_coat", "女", _F_YOUNG, "身着冬季大衣", 1016),  # 圈中达标·保留
]
NEG = ("丑, 丑陋, 五官扭曲, 脸部畸形, 塌鼻, 龅牙, 大头, 头大, 头部过大, 比例失调, 多人, 合影, "
       "卡通, 动漫, 3D, 扭曲, 变形, 多手, 多脸, 残肢, 模糊, 低质量, 文字, 水印, 恐怖, 过曝, 低龄儿童, 小孩, "
       "佛像, 大佛, 雕像, 石像, 塑像, 假背景, 背景虚假, "
       "侧脸, 侧身, 侧面, 半侧面, 3/4侧脸, 转头, 回头, 歪头, 低头, 背对镜头, 扭身, 看向别处")
SPECS = {"16x9": ("1280*720", 640, 360), "9x16": ("720*1280", 720, 1280)}
DITTO = "/root/autodl-tmp/LiveTalking/data/ditto_avatars"

scenics = SCENICS_ALL if sys.argv[1] == "all" else sys.argv[1].split(",")
aspects = sys.argv[2].split(",")
outdir = sys.argv[3]
deploy = len(sys.argv) > 4 and sys.argv[4] == "1"
os.makedirs(outdir, exist_ok=True)

for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(k, None)
import httpx, dashscope
from dashscope import ImageSynthesis
from PIL import Image
dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

n = ok = fail = 0
cli = httpx.Client(timeout=120, trust_env=False)
for base, gz, face, outfit, seed in AVATARS:
    for sc in scenics:
        scene = SCENE.get(sc, "中国著名景区")
        full = (f"一位{gz}景区导览讲解员，{face}，{outfit}，"
                f"严格完全正面面对镜头，脸部和身体都端端正正笔直正对镜头和观众，双肩与镜头平行展开，"
                f"绝对不侧脸、不侧身、不转头、不歪头、不低头，双眼平视直视镜头，正脸完整朝向观众，"
                f"面带亲切甜美的浅浅微笑，"
                f"自然真实的头身比例，头部大小正常绝不显头大，中景半身像，镜头适当拉远完整露出上半身到腰部，"
                f"站在{scene}前，柔和自然光，超写实人像摄影，电影质感，8k 高清，画面里只有一个人")
        for asp in aspects:
            size, w, h = SPECS[asp]
            n += 1
            try:
                resp = ImageSynthesis.call(model="wanx2.1-t2i-plus", prompt=full, negative_prompt=NEG,
                                           n=1, size=size, seed=seed, style="<photography>")
                if resp.status_code != 200:
                    print(f"[{n}] {base} {sc} {asp} FAIL {resp.code} {resp.message}"); fail += 1; continue
                im = Image.open(BytesIO(cli.get(resp.output.results[0].url).content)).convert("RGB")
                if im.size != (w, h):
                    im = im.resize((w, h), Image.LANCZOS)
                dst = os.path.join(DITTO if deploy else outdir, f"{base}__{sc}__{asp}.png")
                im.save(dst); ok += 1
                print(f"[{n}] {base} {sc} {asp} ok -> {dst}")
            except Exception as e:
                print(f"[{n}] {base} {sc} {asp} ERR {e}"); fail += 1
print(f"WANX_DONE ok={ok} fail={fail}")
