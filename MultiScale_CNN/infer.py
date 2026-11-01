"""作者 MSResNet / GOPRO_L1 单精度推理；不训练、不读取清晰参考图。"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import torch

from official_model.MSResNet import build_model
from official_model import data_common

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=6, choices=range(1, 7))
    parser.add_argument('--device', default='cuda', choices=['cuda', 'cpu'])
    args = parser.parse_args()
    config = json.loads((ROOT / 'model_config.json').read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / 'samples_manifest.json').read_text(encoding='utf-8'))
    checkpoint = ROOT / config['checkpoint']
    assert sha(checkpoint) == config['checkpoint_sha256'], '权重 SHA-256 不匹配'
    device = torch.device(args.device)
    if device.type == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('未检测到 CUDA；若需 CPU 验证，请明确指定 --device cpu --limit 1')
    # FP32，不启用 AMP 或 TF32；与网络自带 mean=127.5 保持一致。
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    model = build_model(SimpleNamespace(**config))
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    if not isinstance(state, dict) or 'G' not in state or not state['G']:
        raise RuntimeError('官方检查点缺少生成器 G，禁止随机权重推理')
    loaded = model.load_state_dict(state['G'], strict=True)
    assert not loaded.missing_keys and not loaded.unexpected_keys
    # load_state_dict 之外再核对所有已加载张量。
    assert all(torch.equal(value, state['G'][key]) for key, value in model.state_dict().items())
    model.to(device=device, dtype=torch.float32).eval()
    out = ROOT / 'results' / 'cnn'
    out.mkdir(parents=True, exist_ok=True)
    record = {'python': platform.python_version(), 'torch': torch.__version__,
              'numpy': np.__version__, 'cuda_runtime': torch.version.cuda,
              'device': str(device), 'checkpoint_sha256': sha(checkpoint),
              'generator_strict_load': True, 'loaded_tensor_count': len(state['G']),
              'parameter_count': sum(p.numel() for p in model.parameters()),
              'rgb_range': 255, 'precision': 'float32', 'amp': False, 'tf32': False,
              'reference_images_read_by_inference': False, 'samples': []}
    if device.type == 'cuda':
        free, total = torch.cuda.mem_get_info()
        record.update(gpu=torch.cuda.get_device_name(), available_gpu_bytes=free, total_gpu_bytes=total)
    print('严格加载生成器通过：', len(state['G']), '个张量', flush=True)
    with torch.inference_mode():
        for sample in manifest['samples'][:args.limit]:
            path = ROOT / sample['blur_gamma']
            assert sha(path) == sample['blur_gamma_sha256']
            image = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)
            h, w, _ = image.shape
            start = time.perf_counter()
            padded, pad = data_common.pad(image, divisor=2**(config['n_scales']-1))
            pyramid = data_common.generate_pyramid(padded, n_scales=config['n_scales'])[0]
            shapes = [list(x.shape) for x in pyramid]
            tensors = [x.unsqueeze(0).to(device) for x in data_common.np2tensor(pyramid)[0]]
            if device.type == 'cuda':
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            forward_start = time.perf_counter()
            result = model(tensors)[0][:, :, :h, :w]
            if device.type == 'cuda':
                torch.cuda.synchronize()
            forward_seconds = time.perf_counter() - forward_start
            assert tuple(result.shape) == (1, 3, h, w) and torch.isfinite(result).all()
            # 与作者 utils.py 相同：+0.5、限幅、转换 uint8，无额外后处理。
            array = (result[0]+0.5).clamp(0, 255).permute(1, 2, 0).to('cpu', torch.uint8).numpy()
            dest = out / (sample['id']+'.png')
            Image.fromarray(array).save(dest)
            entry = {'id': sample['id'], 'input_sha256': sha(path), 'output_sha256': sha(dest),
                     'width': w, 'height': h, 'pyramid_shapes': shapes,
                     'padding_bottom_right': [pad[0][1], pad[1][1]],
                     'forward_seconds': forward_seconds, 'processing_seconds_including_png': time.perf_counter()-start}
            if device.type == 'cuda':
                entry['peak_allocated_gpu_bytes'] = torch.cuda.max_memory_allocated()
            record['samples'].append(entry)
            print(sample['id'], json.dumps(entry), flush=True)
    log = ROOT / 'results' / ('inference_single.json' if args.limit == 1 else 'inference_run.json')
    log.write_text(json.dumps(record, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
