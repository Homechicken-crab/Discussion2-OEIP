"""保留同学的NAFNet结构和best.pth；严格加载后对固定6张blur_gamma推理。"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from nafnet_model import NAFNet

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
RESULT = BASE / 'result'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', default='cuda', choices=('cuda', 'cpu'))
    parser.add_argument('--limit', type=int, default=6, choices=range(1, 7))
    args = parser.parse_args()
    config = json.loads((DATA / 'model_config.json').read_text(encoding='utf-8'))
    manifest = json.loads((DATA / 'samples_manifest.json').read_text(encoding='utf-8'))
    checkpoint = DATA / config['checkpoint']
    if sha(checkpoint) != config['checkpoint_sha256']:
        raise RuntimeError('best.pth哈希不匹配，禁止加载未知权重')
    if sha(BASE/'code/nafnet_model.py') != config['model_code_sha256']:
        raise RuntimeError('模型源码与确认过的同学版本不一致')
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA不可用，请明确指定--device cpu')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    device = torch.device(args.device)
    model = NAFNet(**config['network'])
    checkpoint_data = torch.load(checkpoint, map_location='cpu', weights_only=True)
    if 'model_state_dict' not in checkpoint_data or not checkpoint_data['model_state_dict']:
        raise RuntimeError('缺少model_state_dict，不允许随机初始化推理')
    state = checkpoint_data['model_state_dict']
    match = model.load_state_dict(state, strict=True)
    assert not match.missing_keys and not match.unexpected_keys
    assert all(torch.equal(v, state[k]) for k, v in model.state_dict().items())
    print('PASS: strictly loaded and verified', len(state), 'tensors.', flush=True)
    record = {'method': 'NAFNet', 'python': platform.python_version(), 'torch': torch.__version__,
              'cuda_runtime': torch.version.cuda, 'device': str(device),
              'checkpoint_sha256': sha(checkpoint), 'model_code_sha256': sha(BASE/'code/nafnet_model.py'),
              'generator_strict_load': True, 'loaded_tensor_count': len(state),
              'parameter_count': sum(p.numel() for p in model.parameters()),
              'configuration': config, 'reference_images_read_by_inference': False,
              'trained_this_run': False, 'precision': 'float32', 'samples': []}
    if device.type == 'cuda':
        free, total = torch.cuda.mem_get_info()
        record.update(gpu=torch.cuda.get_device_name(), available_gpu_bytes=free, total_gpu_bytes=total)
    del checkpoint_data, state
    model.to(device).eval()
    output = RESULT / 'restored'
    output.mkdir(parents=True, exist_ok=True)
    with torch.inference_mode():
        for sample in manifest['samples'][:args.limit]:
            path = DATA / sample['blur_gamma']
            assert sha(path) == sample['blur_gamma_sha256']
            started = time.perf_counter()
            # 原方案TF.to_tensor等价操作：RGB float32 0–1，不额外伽马变换。
            array = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)/255.0
            h, w = array.shape[:2]
            tensor = torch.from_numpy(np.ascontiguousarray(array.transpose(2, 0, 1))).unsqueeze(0).to(device)
            if device.type == 'cuda':
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            forward_start = time.perf_counter()
            # 模型内部右/下补零至16倍数，forward最后裁回原图；不缩小或分块。
            result = model(tensor)
            if device.type == 'cuda':
                torch.cuda.synchronize()
            forward_seconds = time.perf_counter()-forward_start
            assert tuple(result.shape) == (1, 3, h, w) and torch.isfinite(result).all()
            # 保留原项目TF.to_pil_image的量化约定：乘255后截断为uint8。
            restored = (result[0].float().clamp(0, 1).permute(1, 2, 0).cpu().numpy()*255).astype(np.uint8)
            dest = output/(sample['id']+'.png')
            Image.fromarray(restored).save(dest)
            entry = {'id': sample['id'], 'input_sha256': sha(path), 'output_sha256': sha(dest),
                     'width': w, 'height': h, 'padding_bottom_right': [(-h)%16, (-w)%16],
                     'forward_seconds': forward_seconds, 'processing_seconds_including_png': time.perf_counter()-started}
            if device.type == 'cuda':
                entry['peak_allocated_gpu_bytes'] = torch.cuda.max_memory_allocated()
            record['samples'].append(entry)
            print(sample['id'], json.dumps(entry), flush=True)
    (RESULT/'run_record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
