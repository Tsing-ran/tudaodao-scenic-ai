import os
for v in ["ALL_PROXY","all_proxy","HTTP_PROXY","http_proxy","HTTPS_PROXY","https_proxy","FTP_PROXY","ftp_proxy"]:
    os.environ.pop(v, None)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import hf_hub_download

ROOT = os.path.expanduser("~/Desktop/LiveTalking/models")

# (repo_id, filename_in_repo, local_subdir, rename_to)
JOBS = [
    ("TMElyralab/MuseTalk", "musetalkV15/unet.pth",      "musetalkV15", "unet.pth"),
    ("TMElyralab/MuseTalk", "musetalkV15/musetalk.json", "musetalkV15", "musetalk.json"),
    ("stabilityai/sd-vae-ft-mse", "config.json",                       "sd-vae-ft-mse", "config.json"),
    ("stabilityai/sd-vae-ft-mse", "diffusion_pytorch_model.bin",       "sd-vae-ft-mse", "diffusion_pytorch_model.bin"),
    ("openai/whisper-tiny", "config.json",               "whisper", "config.json"),
    ("openai/whisper-tiny", "model.safetensors",         "whisper", "model.safetensors"),
    ("openai/whisper-tiny", "preprocessor_config.json",  "whisper", "preprocessor_config.json"),
    ("openai/whisper-tiny", "generation_config.json",    "whisper", "generation_config.json"),
    ("openai/whisper-tiny", "tokenizer.json",            "whisper", "tokenizer.json"),
    ("openai/whisper-tiny", "tokenizer_config.json",     "whisper", "tokenizer_config.json"),
    ("openai/whisper-tiny", "vocab.json",                "whisper", "vocab.json"),
    ("openai/whisper-tiny", "merges.txt",                "whisper", "merges.txt"),
    ("openai/whisper-tiny", "normalizer.json",           "whisper", "normalizer.json"),
    ("openai/whisper-tiny", "added_tokens.json",         "whisper", "added_tokens.json"),
    ("openai/whisper-tiny", "special_tokens_map.json",   "whisper", "special_tokens_map.json"),
    ("yzd-v/DWPose", "dw-ll_ucoco_384.pth",              "dwpose", "dw-ll_ucoco_384.pth"),
    ("ManyOtherFunctions/face-parse-bisent", "79999_iter.pth",        "face-parse-bisent", "79999_iter.pth"),
    ("ManyOtherFunctions/face-parse-bisent", "resnet18-5c106cde.pth", "face-parse-bisent", "resnet18-5c106cde.pth"),
]

for repo, fname, subdir, rename in JOBS:
    dest_dir = os.path.join(ROOT, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    final = os.path.join(dest_dir, rename)
    if os.path.exists(final) and os.path.getsize(final) > 0:
        print(f"SKIP {subdir}/{rename}")
        continue
    print(f"GET  {repo} :: {fname}")
    p = hf_hub_download(repo_id=repo, filename=fname)
    # hf_hub_download returns cache path (symlink); copy to flat dest
    import shutil
    shutil.copy(os.path.realpath(p), final)
    print(f" ->  {final}  ({os.path.getsize(final)} bytes)")

print("ALL DONE")
