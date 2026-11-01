"""只读取固定六图的已保存PNG，计算全图RGB PSNR；结果统一写入根目录Result。"""
import csv
import hashlib
import json
import math
import platform
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
PROJECT = BASE.parent
METHODS = ('Wiener_Filiter', 'MSCNN', 'NAFNet')
SERIES = ('Blur_input',) + METHODS
LABELS = ('Blur input', 'Wiener', 'MSCNN', 'NAFNet')
COLORS = ('#8a8a8a', '#d98025', '#3975b5', '#38926a')
OUT = PROJECT / 'Result' / 'evaluation'
FIXED = [('GOPR0384_11_00','000051.png'), ('GOPR0384_11_05','004051.png'),
         ('GOPR0385_11_01','003061.png'), ('GOPR0396_11_00','000051.png'),
         ('GOPR0410_11_00','000168.png'), ('GOPR0854_11_00','000051.png')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rgb(path):
    with Image.open(path) as image:
        assert image.mode == 'RGB' and image.size == (1280,720), str(path)
        return np.asarray(image, dtype=np.float64)


def psnr(image, reference):
    # 对H、W、RGB全部像素求一个MSE；先转float64以避免uint8减法溢出。
    mse = np.mean(np.square(image-reference), dtype=np.float64)
    return math.inf if mse == 0 else 10*math.log10(255.0**2/float(mse))


def main():
    manifest = json.loads((BASE/'data/samples_manifest.json').read_text(encoding='utf-8'))
    assert [(s['sequence'],s['filename']) for s in manifest['samples']] == FIXED
    assert manifest['blur_version'] == 'blur_gamma'
    runs = {method: json.loads((PROJECT/method/'data/run_record.json').read_text(encoding='utf-8')) for method in METHODS}
    by_id = {method: {s['id']:s for s in run['samples']} for method,run in runs.items()}
    rows, sources = [], []
    for sample in manifest['samples']:
        sid = sample['id']
        assert sample['blur_gamma_archive_path'].replace('/blur_gamma/', '/sharp/') == sample['sharp_archive_path']
        blur = BASE/'data'/sample['blur_gamma']
        sharp = BASE/'data'/sample['sharp']
        assert sha(blur)==sample['blur_gamma_sha256'] and sha(sharp)==sample['sharp_sha256']
        reference = read_rgb(sharp)
        values = [psnr(read_rgb(blur), reference)]
        source = {'sample':sid, 'blur_sha256':sha(blur), 'sharp_sha256':sha(sharp), 'restored':{}}
        for method in METHODS:
            data = PROJECT/method/'data'
            assert sha(data/sample['blur_gamma'])==sample['blur_gamma_sha256']
            assert sha(data/sample['sharp'])==sample['sharp_sha256']
            restored = data/'restored'/(sid+'.png')
            assert by_id[method][sid]['input_sha256']==sample['blur_gamma_sha256']
            assert sha(restored)==by_id[method][sid]['output_sha256']
            values.append(psnr(read_rgb(restored), reference))
            source['restored'][method] = {'path':restored.relative_to(PROJECT).as_posix(), 'sha256':sha(restored)}
        rows.append([sid]+values); sources.append(source)
    OUT.mkdir(parents=True, exist_ok=True)
    per_image = OUT/'psnr_per_image.csv'
    with per_image.open('w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Sample']+list(SERIES))
        writer.writerows([[r[0]]+[f'{v:.10f}' for v in r[1:]] for r in rows])

    # 从正式逐图CSV读取绘图/均值输入，保证表格与图表使用相同数值。
    with per_image.open(encoding='utf-8', newline='') as file:
        table = list(csv.DictReader(file))
    scores = np.array([[float(r[m]) for m in SERIES] for r in table], dtype=np.float64)
    means = scores.mean(axis=0)       # 六张图PSNR的算术平均，不先平均MSE。
    mean_csv = OUT/'psnr_mean.csv'
    with mean_csv.open('w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Method','Mean_PSNR_dB','Image_count'])
        writer.writerows([[m,f'{v:.10f}',len(rows)] for m,v in zip(SERIES,means)])
    with mean_csv.open(encoding='utf-8', newline='') as file:
        mean_table = list(csv.DictReader(file))
    plotted_means = np.array([float(r['Mean_PSNR_dB']) for r in mean_table])
    if not np.isfinite(scores).all():
        raise ValueError('CSV已保存：出现零误差的无限PSNR，请单独说明后绘图。')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
    fig, ax = plt.subplots(figsize=(15,6.5), layout='constrained')
    x = np.arange(len(rows)); width = .19
    for j,(label,color) in enumerate(zip(LABELS,COLORS)):
        bars = ax.bar(x+(j-1.5)*width, scores[:,j], width, label=label, color=color)
        ax.bar_label(bars, fmt='%.2f', padding=3, fontsize=8)
    ax.set_xticks(x, [f'{seq}\n{Path(name).stem}' for seq,name in FIXED], fontsize=9)
    ax.set_ylim(0,float(scores.max())+5)
    ax.set_ylabel('PSNR (dB)')
    ax.set_title('GoPro fixed six samples: full-image RGB PSNR\nPeak=255; no border crop, alignment or resizing')
    ax.legend(ncols=4,loc='upper center')
    ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
    fig.savefig(OUT/'psnr_per_image.png',dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8,5), layout='constrained')
    bars = ax.bar(LABELS,plotted_means,color=COLORS,width=.6)
    ax.bar_label(bars,fmt='%.3f',padding=5)
    ax.set_ylim(0,float(plotted_means.max())+5)
    ax.set_ylabel('Mean PSNR (dB)')
    ax.set_title('Arithmetic mean of six per-image RGB PSNR values\nSame saved PNGs and same sharp references')
    ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
    fig.savefig(OUT/'psnr_mean.png',dpi=180); plt.close(fig)

    record = {'metric':'PSNR', 'unit':'dB', 'pixel_range':[0,255], 'channels':'RGB',
              'dtype_for_calculation':'float64', 'region':'entire original 1280x720 image, all RGB channels',
              'formula':'10*log10(255^2/mean((restored-sharp)^2))',
              'average':'arithmetic mean of six per-image PSNR values; not PSNR from pooled MSE',
              'border_crop':0,'alignment':False,'resize':False,'other_metrics':False,
              'blur_baseline_included':True,'restoration_rerun':False,'source_files':sources,
              'environment':{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__},
              'outputs':{path.relative_to(PROJECT).as_posix():sha(path) for path in sorted(OUT.iterdir()) if path.is_file()}}
    (BASE/'data/psnr_run_record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    for method in METHODS:
        path = PROJECT/method/'data/run_record.json'
        run = json.loads(path.read_text(encoding='utf-8'))
        if 'metrics_computed' in run:
            run['metrics_computed_during_inference'] = run.pop('metrics_computed')
        run['evaluation'] = {'metric':'PSNR','record_project_relative':'MSCNN/data/psnr_run_record.json',
                             'output_directory_project_relative':'Result/evaluation'}
        path.write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved PSNR CSVs and plots to',OUT)
    print(dict(zip(SERIES,plotted_means.tolist())))


if __name__=='__main__':
    main()
