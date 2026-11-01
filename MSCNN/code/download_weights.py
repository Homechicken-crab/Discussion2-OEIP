"""仅下载作者 GOPRO_L1 单精度包，核对后提取生成器权重。"""
import hashlib
import json
import zipfile
from pathlib import Path

import gdown

ROOT = Path(__file__).resolve().parent.parent / 'data'
config = json.loads((ROOT / 'model_config.json').read_text(encoding='utf-8'))
existing = ROOT / config['checkpoint']
if existing.exists() and hashlib.sha256(existing.read_bytes()).hexdigest() == config['checkpoint_sha256']:
    print('Existing official GOPRO_L1 generator SHA-256 verified; no download needed.')
    raise SystemExit(0)
cache = ROOT / 'weights'
cache.mkdir(exist_ok=True)
archive = cache / 'GOPRO_L1.zip'
if not archive.exists():
    gdown.download(id='1AfZhyUXEA8_UdZco9EdtpWjTBAb8BbWv', output=str(archive), quiet=False)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == config['archive_sha256']
with zipfile.ZipFile(archive) as z:
    name = 'GOPRO_L1/models/model-1000.pt'
    path = cache / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(z.read(name))
assert hashlib.sha256(path.read_bytes()).hexdigest() == config['checkpoint_sha256']
print('GOPRO_L1 generator SHA-256 verified.')
