"""从作者发布的 ZIP 按 HTTP Range 读取固定测试样本，不下载训练集。"""
import hashlib
import json
import time
from pathlib import Path

from PIL import Image
from remotezip import RemoteZip

ROOT = Path(__file__).resolve().parent
SOURCE = 'https://huggingface.co/datasets/snah/GOPRO_Large/resolve/main/GOPRO_Large.zip'
# 在推理前按序列名称排序选前六个序列，每个序列选排序后的中间帧。
FIXED = [('GOPR0384_11_00', '000051.png'), ('GOPR0384_11_05', '004051.png'),
         ('GOPR0385_11_01', '003061.png'), ('GOPR0396_11_00', '000051.png'),
         ('GOPR0410_11_00', '000168.png'), ('GOPR0854_11_00', '000051.png')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = {'source_page': 'https://seungjunnah.github.io/Datasets/gopro.html',
                'archive_url': SOURCE, 'license': 'CC BY 4.0', 'split': 'test',
                'selection_rule': 'first six lexicographically sorted test sequences; middle sorted frame (zero-based len//2)',
                'selection_frozen_before_inference': True, 'blur_version': 'blur_gamma',
                'download_method': 'HTTP Range ZIP central directory and only 12 selected PNG entries; no full archive or train images',
                'samples': []}
    for seq, name in FIXED:
        item = {'id': seq + '_' + Path(name).stem, 'sequence': seq, 'filename': name}
        for kind in ('blur_gamma', 'sharp'):
            item[kind] = f'samples/{seq}/{kind}/{name}'
            item[kind + '_archive_path'] = f'test/{seq}/{kind}/{name}'
        # 用于所有方法的固定局部，0基像素坐标，推理前固定，不按结果挑选。
        item['crops_xywh_zero_based'] = [[400, 180, 256, 192], [800, 400, 256, 192]]
        manifest['samples'].append(item)
    target = ROOT / 'samples_manifest.json'
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    with RemoteZip(SOURCE + '?download=true&fresh=' + str(int(time.time())), initial_buffer_size=256*1024) as z:
        entries = z.namelist()
        seqs = sorted({n.split('/')[1] for n in entries if n.startswith('test/') and '/blur_gamma/' in n and n.endswith('.png')})
        assert [seq for seq, _ in FIXED] == seqs[:6]
        for item in manifest['samples']:
            names = sorted(n for n in entries if n.startswith(f"test/{item['sequence']}/blur_gamma/") and n.endswith('.png'))
            assert names[len(names)//2].endswith('/'+item['filename'])
            for kind in ('blur_gamma', 'sharp'):
                path = ROOT / item[kind]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(z.read(item[kind + '_archive_path']))
                with Image.open(path) as image:
                    assert image.size == (1280, 720) and image.mode == 'RGB'
                item[kind + '_sha256'] = sha(path)
                print(item[kind], flush=True)
    manifest['selected_png_bytes'] = sum((ROOT / s[k]).stat().st_size for s in manifest['samples'] for k in ('blur_gamma', 'sharp'))
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
