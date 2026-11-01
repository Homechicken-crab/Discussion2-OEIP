# MSCNN

入口：`python code/run_mscnn.py`；本方案对比：`python code/make_comparisons.py`；三个方案全部运行完成后，总对比：`python code/make_comparisons.py --all-methods`。路径相对脚本解析。

环境：Python3.12.6、PyTorch2.11.0+cu128、scikit-image0.25.2、RTX4060 Laptop 8GB。实际独立环境 `D:\codex\2026-11-01\xian\work\multiscale_env`。新环境用 `python -m pip install -r code/requirements.txt`。

使用Nah等人CVPR2017方法的[作者PyTorch实现](https://github.com/SeungjunNah/DeepDeblur-PyTorch)，提交 `e92dc7c3337127887da617ffe819b49cb022fd81`，及作者[GOPRO_L1单精度权重包](https://drive.google.com/file/d/1AfZhyUXEA8_UdZco9EdtpWjTBAb8BbWv/view)。获取入口 `python code/download_weights.py`；现有权重在 `data/weights/GOPRO_L1/models/model-1000.pt`，忽略不提交。权重SHA-256：`8d02a04244f0f54ba645834b6726eafa4348e88df870a31a8ccb037e63ea0e49`。来源/文件哈希/包哈希和关键配置见data中的JSON及原始训练参数文本。

三份网络文件保持作者源码不变；预处理仅将scikit-image的 `multichannel=True` 更新为 `channel_axis=-1`。三尺度、每尺度19残差块、64通道、5×5卷积，Gaussian金字塔，由粗到细复原。RGB float32范围0–255，网络内部减127.5；关闭AMP/TF32，严格加载并核对244个张量。需要时右/下复制边缘补至4倍数，最后裁回。无额外增强。作者PyTorch默认RGB范围、L1损失、批量16等与原论文训练设置不同；本次是预训练推理，没有自行训练或复现全部训练流程。

数据来自[作者GoPro页面](https://seungjunnah.github.io/Datasets/gopro.html)链接的官方测试集（CC BY4.0）。继续使用既定6对blur_gamma/sharp，无重新挑选。小样本在data/samples，清单、文件哈希和固定0基ROI在data/samples_manifest.json；各方案独立副本逐文件一致。sharp不进入网络。全部原尺寸1280×720，本批不需补边。

新目录下已实际运行6图；输出在result/restored，三项对比在result/comparison。总对比只保存在result/comparison/all_methods，按模糊→维纳→MSCNN→NAFNet→sharp顺序纵向排列整图，原生1倍显示；局部统一2倍最近邻显示，两处固定ROI先整图复原后裁取。result/run_record.json记录实际运行和配对/尺寸核对。无评价指标或PPT。

权重下载遇Google Drive连接错误时，可手动从同一官方链接取包后核对哈希；本机已有验证通过的权重，不依赖重新下载。当前NAFNet采用同学提供的匹配权重，其训练blur版本来源限制见NAFNet/code/README.md，因此不将少量视觉对比表述为严格统一训练条件下的定量优劣结论。
