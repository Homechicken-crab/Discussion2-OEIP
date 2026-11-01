"""推理和维纳选参完成后，再读取sharp制作同尺度四项对比。"""
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
WIENER = ROOT.parent / '维纳滤波'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / 'samples_manifest.json').read_text(encoding='utf-8'))
    inference = json.loads((ROOT / 'results/inference_run.json').read_text(encoding='utf-8'))
    runs = {s['id']: s for s in inference['samples']}
    with (WIENER / 'results_gopro/parameters.csv').open(encoding='utf-8-sig', newline='') as f:
        params = {r['Sample']: r for r in csv.DictReader(f)}
    out = ROOT / 'results/comparisons'
    out.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20) if Path('C:/Windows/Fonts/arial.ttf').exists() else ImageFont.load_default(size=20)
    checks = []
    for sample in manifest['samples']:
        sid = sample['id']
        assert runs[sid]['input_sha256'] == sample['blur_gamma_sha256'] == sha(ROOT / sample['blur_gamma'])
        assert sha(ROOT / sample['sharp']) == sample['sharp_sha256']
        assert sample['blur_gamma_archive_path'].replace('/blur_gamma/', '/sharp/') == sample['sharp_archive_path']
        p = params[sid]
        images = [Image.open(path).convert('RGB') for path in
                  [ROOT / sample['blur_gamma'], WIENER / 'results_gopro' / (sid+'.png'),
                   ROOT / 'results/cnn' / (sid+'.png'), ROOT / sample['sharp']]]
        assert all(im.size == (1280, 720) for im in images)
        labels = ['GoPro blur_gamma', f"MATLAB Wiener L={p['LEN']} T={p['THETA']} N={p['NSR']}",
                  'Nah MS-CNN / GOPRO_L1 FP32', 'GoPro sharp reference']
        # 原图单独保留1280x720；此拼图统一0.5倍显示，不改变长宽比。
        canvas = Image.new('RGB', (1300, 844), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 5), sid+' | overview: all panels 0.5x', font=font, fill='black')
        for k, (im, label) in enumerate(zip(images, labels)):
            x, y = 10+(k % 2)*650, 42+(k//2)*400
            draw.text((x, y), label, font=font, fill='black')
            canvas.paste(im.resize((640, 360), Image.Resampling.LANCZOS), (x, y+30))
        canvas.save(out / (sid+'_overview.png'))
        canvas = Image.new('RGB', (2100, 930), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 5), sid+' | fixed crops, all panels 2x nearest-neighbor display', font=font, fill='black')
        for r, (x, y, w, h) in enumerate(sample['crops_xywh_zero_based']):
            top = 42+r*440
            draw.text((10, top), f'ROI{r+1} zero-based x,y,w,h=[{x},{y},{w},{h}]', font=font, fill='black')
            for k, (im, label) in enumerate(zip(images, labels)):
                left = 10+k*525
                draw.text((left, top+28), label, font=font, fill='black')
                crop = im.crop((x, y, x+w, y+h)).resize((w*2, h*2), Image.Resampling.NEAREST)
                canvas.paste(crop, (left, top+56))
        canvas.save(out / (sid+'_crops.png'))
        checks.append({'id': sid, 'paired_test_paths_verified': True, 'input_sha256': sha(ROOT/sample['blur_gamma']),
                       'all_four_sizes': [1280, 720], 'same_input_path_for_matlab_and_cnn': sample['blur_gamma'],
                       'identical_crop_coordinates': sample['crops_xywh_zero_based'], 'wiener': p,
                       'wiener_sha256': sha(WIENER/'results_gopro'/(sid+'.png')),
                       'cnn_sha256': sha(ROOT/'results/cnn'/(sid+'.png'))})
        print('verified and compared', sid, flush=True)
    (ROOT/'results/pairing_and_output_checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
