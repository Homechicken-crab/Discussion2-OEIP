"""默认生成本方案三项对比；MSCNN入口加--all-methods生成根目录Result下的五项总对比。"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
PROJECT = BASE.parent
METHODS = ('Wiener_Filiter', 'MSCNN', 'NAFNet')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    path = Path('C:/Windows/Fonts/arial.ttf')
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default(size=size)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-methods', action='store_true')
    parser.add_argument('--check-only', action='store_true', help='只核对现有对比图，不改写PNG')
    args = parser.parse_args()
    assert not args.all_methods or BASE.name == 'MSCNN', '总对比由MSCNN入口统一导出到根目录Result'
    chosen = METHODS if args.all_methods else (BASE.name,)
    manifest = json.loads((BASE/'data/samples_manifest.json').read_text(encoding='utf-8'))
    records = {name: json.loads((PROJECT/name/'data/run_record.json').read_text(encoding='utf-8')) for name in chosen}
    sample_records = {name: {s['id']: s for s in record['samples']} for name, record in records.items()}
    params = {}
    if 'Wiener_Filiter' in chosen:
        with (PROJECT/'Wiener_Filiter/data/parameters.csv').open(encoding='utf-8-sig', newline='') as f:
            params = {r['Sample']:r for r in csv.DictReader(f)}
    output = BASE/'result'
    if args.all_methods:
        output = PROJECT/'Result/comparison'
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    for sample in manifest['samples']:
        sid = sample['id']
        assert sample['blur_gamma_archive_path'].replace('/blur_gamma/', '/sharp/') == sample['sharp_archive_path']
        blur, sharp = BASE/'data'/sample['blur_gamma'], BASE/'data'/sample['sharp']
        assert sha(blur)==sample['blur_gamma_sha256'] and sha(sharp)==sample['sharp_sha256']
        paths = [blur]
        labels = ['GoPro blur_gamma input']
        for method in chosen:
            other = PROJECT/method/'data'
            assert sha(other/sample['blur_gamma'])==sample['blur_gamma_sha256']
            assert sha(other/sample['sharp'])==sample['sharp_sha256']
            run = sample_records[method][sid]
            assert run['input_sha256']==sample['blur_gamma_sha256']
            restored = PROJECT/method/'data/restored'/(sid+'.png')
            assert sha(restored)==run['output_sha256']
            paths.append(restored)
            if method == 'Wiener_Filiter':
                p = params[sid]
                labels.append(f"Wiener / MATLAB | LEN={p['LEN']} THETA={p['THETA']} NSR={p['NSR']}")
            else:
                labels.append('MSCNN / Nah GOPRO_L1 FP32' if method=='MSCNN' else 'NAFNet / supplied matching checkpoint FP32')
        paths.append(sharp); labels.append('GoPro sharp reference (display only)')
        images = [Image.open(p).convert('RGB') for p in paths]
        assert all(im.size==(1280,720) for im in images)
        # 整体图纵向排列，每张图原生1倍显示，避免将五张整图压成一排小图。
        canvas = Image.new('RGB',(1304,90+len(images)*778),'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((12,8),sid,font=font(28),fill='black')
        draw.text((12,46),'Full images: identical 1x display; scroll vertically',font=font(24),fill='black')
        for k,(image,label) in enumerate(zip(images,labels)):
            top = 90+k*778
            draw.text((12,top),f'{k+1}. {label}',font=font(28),fill='black')
            canvas.paste(image,(12,top+42))
        overview = output/(sid+'_overview.png')
        if args.check_only:
            with Image.open(overview) as saved:
                assert saved.size==canvas.size and saved.tobytes()==canvas.tobytes(), str(overview)
        else:
            canvas.save(overview)
        # 每行一种方法，两列固定ROI。所有方法都先整图复原再从同位置裁取。
        rois = sample['crops_xywh_zero_based']
        assert rois==[[400,180,256,192],[800,400,256,192]]
        canvas = Image.new('RGB',(1060,100+len(images)*464),'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((12,8),sid,font=font(26),fill='black')
        draw.text((12,46),'Fixed zero-based ROIs; all crops 2x nearest-neighbor display',font=font(22),fill='black')
        for k,(image,label) in enumerate(zip(images,labels)):
            top = 100+k*464
            draw.text((12,top),f'{k+1}. {label}',font=font(24),fill='black')
            for r,(x,y,w,h) in enumerate(rois):
                left = 12+r*524
                draw.text((left,top+34),f'ROI{r+1} [{x},{y},{w},{h}]',font=font(20),fill='black')
                patch = image.crop((x,y,x+w,y+h)).resize((w*2,h*2),Image.Resampling.NEAREST)
                canvas.paste(patch,(left,top+68))
        crops = output/(sid+'_crops.png')
        if args.check_only:
            with Image.open(crops) as saved:
                assert saved.size==canvas.size and saved.tobytes()==canvas.tobytes(), str(crops)
        else:
            canvas.save(crops)
        checks.append({'id':sid,'input_sha256':sha(blur),'reference_sha256':sha(sharp),
                       'paired_paths_verified':True,'output_sizes':[1280,720],
                       'rois_xywh_zero_based':rois,'overview_scale':1,'crop_display_scale':2,
                       'methods':list(chosen),'overview_sha256':sha(overview),'crops_sha256':sha(crops)})
        print('Checked comparisons:' if args.check_only else 'Saved comparisons:',sid,flush=True)
    record_path = BASE/'data/run_record.json'
    own_record = json.loads(record_path.read_text(encoding='utf-8'))
    own_record['all_methods_comparison' if args.all_methods else 'comparison'] = checks
    record_path.write_text(json.dumps(own_record,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
