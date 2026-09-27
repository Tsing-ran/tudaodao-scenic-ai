"""把 ComfyUI UI 工作流 JSON 转成 /prompt API 格式（用 /object_info 拿每节点输入顺序）。
用法：python comfy_ui2api.py <ui_workflow.json> <out_api.json>"""
import json, sys, httpx
COMFY = "http://127.0.0.1:8188"
C = httpx.Client(trust_env=False, timeout=30)

def main():
    ui = json.load(open(sys.argv[1]))
    nodes = ui["nodes"]; links = ui["links"]
    # link: [id, from_node, from_slot, to_node, to_slot, type]
    link_by_id = {l[0]: l for l in links}
    obj = {}  # class → input order (required+optional names, in order)
    def info(cls):
        if cls not in obj:
            r = C.get(f"{COMFY}/object_info/{cls}").json()
            it = r[cls]["input"]
            names = list(it.get("required", {})) + list(it.get("optional", {}))
            obj[cls] = (names, it)
        return obj[cls]
    api = {}
    for n in nodes:
        cls = n["type"]; nid = str(n["id"])
        if cls in ("Note","Reroute","PrimitiveNode"): continue
        names, it = info(cls)
        inputs = {}
        # 连接型输入
        connected = {}
        for inp in n.get("inputs", []):
            if inp.get("link") is not None:
                l = link_by_id[inp["link"]]
                connected[inp["name"]] = [str(l[1]), l[2]]
        # widgets 按"非连接"输入顺序填
        wv = n.get("widgets_values", [])
        wi = 0
        for name in names:
            if name in connected:
                inputs[name] = connected[name]
            else:
                # 该输入是 widget？（required/optional 里且不是纯连接型如 IMAGE/MODEL）
                spec = it.get("required", {}).get(name) or it.get("optional", {}).get(name)
                if spec is None: continue
                t = spec[0]
                if isinstance(t, list) or t in ("INT","FLOAT","STRING","BOOLEAN"):
                    if wi < len(wv):
                        v = wv[wi]; wi += 1
                        # 跳过 seed 的 'randomize' 控件值
                        if isinstance(v, str) and v in ("randomize","fixed","increment","decrement") and wi < len(wv):
                            v = wv[wi-2] if wi>=2 else v
                        inputs[name] = v
        api[nid] = {"class_type": cls, "inputs": inputs}
    json.dump(api, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print(f"✓ {len(api)} 节点 → {sys.argv[2]}")

main()
