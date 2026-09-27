"""生成「看着真实的游客聊天记录」灌入 conversations 表，供管理端数据大屏/对话列表展示。

数据进 conversations 表（analytics 全套端点都读它）：dashboard/hot-topics/sentiment-trend/
topic-intents/conversations/knowledge-gaps/alerts。情绪用英文码 happy/excited/neutral/curious/
empathetic/apologetic（与 analytics 的 _POSITIVE/_NEGATIVE 对齐）。

特点：①多轮会话（一个 session 2-5 轮，像真游客连着问）②覆盖文化问答/路线/设施服务/投诉/夸赞/
闲聊多种意图 ③情绪分布真实（多数正面+中性，少量负面投诉撑起预警/情感趋势）④时间戳铺在最近 N 天、
白天加权、近几天更密 ⑤session_id 以 demo- 前缀，可一键清除、不污染真实数据。

用法：python scripts/gen_demo_conversations.py --db <conversations.db路径> --sessions 60 --days 30
      --purge 先清除旧的 demo- 数据（幂等重跑）
"""
import argparse
import random
import sqlite3
from datetime import datetime, timedelta

# 情绪英文码（与 backend/api/analytics.py 一致）：正面 happy/excited，中性 neutral/curious，负面 empathetic/apologetic
P_HAPPY, P_EXC, NEU, CUR, EMP, APO = "happy", "excited", "neutral", "curious", "empathetic", "apologetic"

# 每景区：(问题, 回答, 情绪)。问题贴各景区真实诉求，回答口语化无 markdown（数字人口播风格）。
SCENIC_QA = {
    "lingshan": [
        ("灵山大佛有多高啊", "灵山大佛高达八十八米，是世界上最高的青铜释迦牟尼立像之一，远远就能望见，特别震撼。", P_EXC),
        ("九龙灌浴几点开始表演", "九龙灌浴每天上午十点和下午两点各一场，建议提前十分钟到大佛广场南侧就位，场面很壮观。", NEU),
        ("梵宫在哪里怎么过去", "梵宫在大佛的西南侧，从九龙灌浴出来沿主路步行约八分钟就到，沿途有指示牌，跟着走就行。", NEU),
        ("最近的卫生间在哪", "离您最近的卫生间在五印坛城入口右手边，步行两三分钟，那边还有母婴室和直饮水。", NEU),
        ("带着老人有没有轻松点的路线", "有的，建议走无障碍主路，从入口坐景区电瓶车直达大佛广场，沿途有休息长椅，老人走起来不累。", EMP),
        ("这里能烧香祈福吗", "可以的，灵山有专门的祈福区，请用景区提供的环保香，殿内请不要拍照，保持安静以示尊重。", NEU),
        ("素斋在哪里吃推荐吗", "梵宫附近的素斋馆很受欢迎，菌菇煲和素水饺都不错，中午人多建议十一点半前去避开排队。", P_HAPPY),
        ("你讲得真好谢谢你", "不客气呀，能陪您逛灵山我也很开心，接下来想去拈花湾看夜景的话我再帮您规划路线。", P_HAPPY),
        ("门票多少钱学生有优惠吗", "灵山胜境成人票二百一十元，全日制学生凭学生证半价，一米四以下儿童免票，建议网上提前订。", NEU),
        ("排队人太多了好烦", "理解您的心情，这个点确实是高峰，建议先去人少的五印坛城，等十一点后再回来看九龙灌浴会顺畅很多。", EMP),
    ],
    "nihuawan": [
        ("拈花湾夜游几点开始", "拈花湾的夜游灯光大概日落后开启，夏天七点左右，香月花街和拈花塔点灯后特别美，建议傍晚就进去。", P_EXC),
        ("晚上有什么演出吗", "有的，禅意主题的《禅行》夜间演出很值得看，沿着环湖的几个点位次第上演，跟着人流走就能依次看到。", NEU),
        ("住宿贵不贵有推荐的吗", "客栈从几百到上千都有，波罗蜜多酒店和禅意客栈口碑不错，旺季周末要提前订，平日会实惠一些。", NEU),
        ("拈花塔能上去吗", "拈花塔可以登临，塔上俯瞰整个小镇和湖景很开阔，傍晚上去正好赶上华灯初上，拍照特别出片。", P_HAPPY),
        ("这边适合带孩子玩吗", "挺适合的，白天可以玩手作和喂鱼，晚上看灯光和演出，节奏慢，孩子不会累，亲子家庭很喜欢这里。", P_HAPPY),
        ("最近的停车场在哪", "主停车场在小镇北入口，停好车走过来约五分钟，旺季车位紧张建议早点来或者直接停旁边的生态停车场。", NEU),
    ],
    "xihu": [
        ("断桥在哪边怎么走", "断桥在白堤的东头，从断桥往西走就是整条白堤，远处能看到雷峰塔，是看西湖最经典的一段。", NEU),
        ("游船票多少钱在哪买", "西湖手划船和电瓶船都有，电瓶船每位五十五元含三潭印月登岛，码头在中山公园和花港都有，现场买就行。", NEU),
        ("雷峰塔值得上去吗", "值得，塔内有白蛇传的故事陈列，登顶能俯瞰整个西湖和湖心三岛，傍晚看夕阳染湖面特别美。", P_HAPPY),
        ("音乐喷泉几点有", "西湖音乐喷泉在湖滨三公园那边，一般晚上七点和八点各一场，想占好位置建议提前半小时去栏杆边。", P_EXC),
        ("坐地铁怎么到西湖", "坐地铁一号线到龙翔桥站,从A口出来步行约十分钟就到湖滨,这一段离断桥和音乐喷泉都很近。", NEU),
        ("有没有推荐的本地菜", "楼外楼的西湖醋鱼和龙井虾仁是招牌，知味观的小笼和猫耳朵也好吃又实惠，中午人多建议错峰。", P_HAPPY),
        ("下雨天还能逛吗", "下雨的西湖别有韵味，烟雨朦胧像水墨画，建议带伞走苏堤，或者去旁边的浙博、茶室避雨喝杯龙井。", EMP),
    ],
    "huangshan": [
        ("黄山日出几点能看到", "这个季节日出大概在清晨五点半前后，光明顶和始信峰是最佳观日点，建议提前一小时上去占位置，山顶冷记得带件外套。", P_EXC),
        ("索道票多少钱排队久吗", "云谷索道和玉屏索道单程都是九十元，旺季排队可能要一小时，建议早上第一班上山或者错开中午高峰。", NEU),
        ("迎客松在哪个位置", "迎客松在玉屏楼那边，从玉屏索道上站出来走几分钟就到，是黄山的标志，记得排队合影注意脚下安全。", NEU),
        ("体力不好能爬下来吗", "建议您上下都坐索道，山上走玉屏到光明顶这段相对平缓，量力而行，多歇脚，背包越轻越好。", EMP),
        ("山上住宿怎么样贵吗", "山顶有白云宾馆等几家，旺季床位紧张价格偏高，一定要提前很久预订，想省钱可以选山脚汤口住一晚。", NEU),
        ("今天天气适合上山吗", "上山前最好查下实时天气，云海要靠运气，雨雾天能见度低注意防滑，台风或大风天索道可能停运要留意公告。", EMP),
        ("缆车太挤了等好久", "高峰期确实挤，辛苦您了，下山如果不赶时间可以等过了下午三点的高峰，人会少很多，体验好一些。", APO),
    ],
    "gugong": [
        ("故宫需要预约吗怎么约", "故宫全部实名预约，提前在故宫博物院公众号或官网放票时段抢，旺季很抢手，建议定好闹钟提前约。", NEU),
        ("中轴线一天逛得完吗", "中轴线从午门到神武门这条主线半天就能走完，太和殿、乾清宫这些大殿都在线上，想看珍宝馆钟表馆再留半天。", NEU),
        ("珍宝馆在哪要另收费吗", "珍宝馆和钟表馆在东路宁寿宫区域，需要单独买票，里面的金器和古钟表很精彩，喜欢文物的别错过。", P_HAPPY),
        ("有讲解器租吗多少钱", "有自动讲解器，进门后在租赁点办理，走到哪讲到哪挺方便，也可以用手机扫展牌上的二维码听免费讲解。", NEU),
        ("出口在哪边出去方便吗", "参观顺序是从午门进、神武门出，出来对面就是景山，想拍故宫全景可以上景山万春亭俯瞰，很值得。", NEU),
        ("人太多了根本走不动", "理解您，旺季中轴线确实拥挤，建议往东西六宫的侧路走，人少很多还能静下心看看后宫的院落。", EMP),
        ("故宫的猫在哪能看到", "故宫的猫常在背阴的庭院和墙根晒太阳，碰到全靠缘分，看到了也请不要投喂哦，让它们保持健康。", P_HAPPY),
    ],
    "zhangjiajie": [
        ("百龙天梯要排队吗票多少", "百龙天梯单程七十二元，旺季排队较长，建议早上早点去，坐电梯上袁家界只要一两分钟，省下不少爬山体力。", NEU),
        ("阿凡达的山在哪个景点", "电影取景的乾坤柱在袁家界景区，也叫哈利路亚山，从天子山或百龙天梯都能上去，雾天云雾缭绕特别仙。", P_EXC),
        ("玻璃栈道恐高能走吗", "大峡谷玻璃桥很刺激，恐高的话可以贴着内侧扶手慢慢走，或者改去金鞭溪走谷底的水边步道，一样很美还轻松。", EMP),
        ("天子山索道在哪坐", "天子山索道在丁香榕那边上站，下到十里画廊很方便，景区内换乘环保车记得保管好门票，三天内多次进出有效。", NEU),
        ("两天怎么安排比较顺", "建议第一天森林公园金鞭溪加袁家界，住山上；第二天天子山加十里画廊下山，这样不走回头路最顺。", P_HAPPY),
    ],
    "bingmayong": [
        ("一号坑二号坑哪个好看", "一号坑规模最大、军阵最震撼，必看；二号坑能看到跪射俑等不同兵种，三号坑是指挥部，时间够建议都看。", P_EXC),
        ("铜车马在哪个馆", "铜车马在专门的文物陈列厅，做工极其精细被誉为青铜之冠，离三号坑不远，跟着馆内指示牌走就能找到。", P_HAPPY),
        ("可以拍照吗能用闪光灯吗", "坑内可以拍照但请关闭闪光灯，保护文物，人多时拍完照请往前走不要长时间堵在栏杆边，方便后面的游客。", NEU),
        ("请个讲解值不值", "很值，兵马俑背后的历史和工艺细节光看说明牌很难体会，跟着讲解或租电子讲解器，逛起来会生动很多。", NEU),
        ("从西安市区怎么过来", "市区可以坐游五（306）路公交直达，或者坐高铁到临潼站再打车，自驾的话停车场就在景区外，挺方便。", NEU),
    ],
    "mogaoku": [
        ("莫高窟要提前多久预约", "莫高窟强烈建议提前一个月在官网约A类票，含数字展示中心加八个洞窟，旺季应急票看的窟少，提前约最划算。", NEU),
        ("洞窟里能拍照吗", "洞窟内全程禁止拍照，是为了保护壁画的颜料不被光照损伤，请理解配合，数字展示中心的影片可以拍。", NEU),
        ("数字展示中心是看什么的", "数字中心先放两部球幕电影，介绍敦煌历史和洞窟艺术，看完再坐摆渡车去实体洞窟，这样参观会更看得懂。", P_HAPPY),
        ("九层楼是哪个窟", "九层楼是标志性的红色木构窟檐，里面是巨大的弥勒佛像，几乎所有讲解线路都会经过，是莫高窟的门面。", P_EXC),
        ("讲解员会带着看几个窟", "讲解员一般带看八个洞窟，每批洞窟会轮换以保护壁画，跟紧讲解听故事，洞内光线暗注意脚下台阶。", NEU),
    ],
}

# 通用服务/夸赞/投诉/闲聊（适配所有景区，{s} 占位景区名）；撑起设施速查、情感趋势负面样本、预警
UNIVERSAL = [
    ("这附近有母婴室吗", "有的，{s}的游客服务中心设有母婴室，配了热水和休息座椅，需要的话我可以指给您最近的一个。", NEU),
    ("能寄存行李吗在哪", "可以的，入口游客中心提供行李寄存，大件小件都收，凭码取件，轻装游玩更舒服。", NEU),
    ("手机快没电了哪能充电", "游客服务中心有共享充电宝和充电插座，餐饮区一般也能借到，先到服务台问一下最方便。", NEU),
    ("有轮椅可以借吗", "有的，{s}游客中心提供免费轮椅和婴儿车租借，押证件即可，方便老人和小朋友。", EMP),
    ("这里能用医保吗有医务室吗", "景区设有医务室提供基础医疗和应急药品，位置在游客中心附近，身体不舒服随时去，安全第一。", EMP),
    ("你们的数字人好厉害啊", "谢谢夸奖呀，我会一直在这儿陪您逛，有任何想知道的尽管问我，拍张照片我还能帮您认认这是哪个景点。", P_HAPPY),
    ("今天玩得好开心谢谢", "听到您玩得开心我也特别高兴，临走前要不要我帮您生成一张今天的电子游记明信片，留个纪念。", P_HAPPY),
    ("找不到路了好着急", "别急，您把手机镜头对准旁边的指示牌或地标拍一张，我帮您定位现在的位置再一步步给您指路。", EMP),
    ("东西怎么这么贵", "景区内餐饮纪念品价格是偏高一些，理解您，您可以去游客中心拿张优惠地图，部分商户有折扣会实惠点。", APO),
    ("讲解声音太小听不清", "抱歉让您体验打折了，您可以租一个电子讲解器贴着耳朵听，或者靠近讲解牌扫码听语音，会清楚很多。", APO),
    ("天气热有没有阴凉的地方", "这个点日头足，建议先去室内展馆或树荫长廊歇一歇，避开正午太阳，等下午四点后再逛室外凉快些。", EMP),
    ("有没有适合拍照的机位", "有的，{s}最出片的机位我可以推荐给您，顺光的时段拍最好看，需要的话我把位置和最佳时间一起发您。", P_HAPPY),
]

SCENIC_NAME = {
    "lingshan": "灵山", "nihuawan": "拈花湾", "xihu": "西湖", "huangshan": "黄山",
    "gugong": "故宫", "zhangjiajie": "张家界", "bingmayong": "兵马俑", "mogaoku": "莫高窟",
}
GROUPS = ["adult", "family_kids", "senior", "couple"]


# 情绪极性：正面/中性/负面 —— 控制每会话的情绪配比，避免「关切/抱歉」过多拉低满意度
POL = {P_HAPPY: "pos", P_EXC: "pos", NEU: "neu", CUR: "neu", EMP: "neg", APO: "neg"}


def build_rows(sessions: int, days: int, seed: int = 7):
    rng = random.Random(seed)
    scenics = list(SCENIC_QA.keys())
    rows = []
    now = datetime.now()
    for i in range(sessions):
        # 前 N 个会话每景区各保底一个，其余按热度加权（灵山/西湖/故宫更热）
        scenic = scenics[i] if i < len(scenics) else rng.choices(scenics, weights=[5, 2, 4, 3, 4, 2, 2, 2])[0]
        sname = SCENIC_NAME[scenic]
        # 该会话候选问答：景区专属 + 通用（占位替换景区名），按极性分桶
        items = list(SCENIC_QA[scenic]) + [(q, a.replace("{s}", sname), e) for q, a, e in UNIVERSAL]
        by_pol = {"pos": [], "neu": [], "neg": []}
        for q, a, e in items:
            by_pol[POL[e]].append((q, a, e))
        # 逐轮按极性配比抽（中性 45% / 正面 40% / 负面 15%，真实且整体满意度偏正）
        used, turns = set(), []
        for _ in range(rng.randint(2, 5)):
            pol = rng.choices(["neu", "pos", "neg"], weights=[45, 40, 15])[0]
            cand = [x for x in by_pol[pol] if x[0] not in used] \
                or [x for x in (by_pol["neu"] + by_pol["pos"]) if x[0] not in used]
            if not cand:
                break
            pick = rng.choice(cand)
            used.add(pick[0])
            turns.append(pick)
        sid = f"demo-{scenic}-{i:03d}"
        # 时间：近 days 天内、近几天更密、白天加权
        day_off = int(abs(rng.gauss(0, days / 2.2))) % days
        base = now - timedelta(days=day_off)
        hour = rng.choices(range(8, 21), weights=[2, 4, 6, 7, 6, 5, 4, 5, 6, 6, 5, 3, 2])[0]
        t = base.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59))
        for q, a, emo in turns:
            rows.append((sid, scenic, q, a, emo, 1, t.strftime("%Y-%m-%d %H:%M:%S")))
            t += timedelta(seconds=rng.randint(25, 180))  # 轮间隔
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="conversations.db 路径")
    ap.add_argument("--sessions", type=int, default=60)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--purge", action="store_true", help="先删除旧的 demo- 会话再插入（幂等）")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
        scenic_id TEXT NOT NULL DEFAULT 'lingshan', user_message TEXT NOT NULL,
        ai_reply TEXT NOT NULL, emotion TEXT NOT NULL DEFAULT 'neutral',
        context_used INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)""")
    if args.purge:
        n = conn.execute("DELETE FROM conversations WHERE session_id LIKE 'demo-%'").rowcount
        print(f"已清除旧 demo 数据 {n} 行")
    rows = build_rows(args.sessions, args.days, args.seed)
    conn.executemany(
        "INSERT INTO conversations (session_id, scenic_id, user_message, ai_reply, emotion, context_used, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    # 统计
    tot = conn.execute("SELECT COUNT(*) FROM conversations WHERE session_id LIKE 'demo-%'").fetchone()[0]
    bys = conn.execute("SELECT scenic_id, COUNT(*) FROM conversations WHERE session_id LIKE 'demo-%' GROUP BY scenic_id ORDER BY 2 DESC").fetchall()
    bye = conn.execute("SELECT emotion, COUNT(*) FROM conversations WHERE session_id LIKE 'demo-%' GROUP BY emotion ORDER BY 2 DESC").fetchall()
    conn.close()
    print(f"插入 {len(rows)} 行（{args.sessions} 会话），当前 demo 总计 {tot} 行")
    print("按景区：", dict(bys))
    print("按情绪：", dict(bye))


if __name__ == "__main__":
    main()
