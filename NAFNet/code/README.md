# NAFNet

入口：`python code/run_nafnet.py`（默认CUDA，固定6图）；对比：`python code/make_comparisons.py`。从任意工作目录传入脚本路径均可，路径相对脚本解析。

环境：Python 3.12.6、PyTorch 2.11.0+cu128、RTX4060 Laptop 8GB；独立环境位于 `D:\codex\2026-11-01\xian\work\multiscale_env`。新环境可用 `python -m pip install -r code/requirements.txt`。

保留同学项目 `motion_deblur_project/motion_deblur_project - 副本/models/model.py` 及 `checkpoints/best.pth`，模型源码未改，权重放在 `data/weights/best.pth`，不提交Git。权重SHA-256：`d3c80dc1b533375389c5e0e875c540e7e412fd1f4801a27b3e4906d416ad51da`。原始小组项目仍在桌面；没有改动它，也未下载另一套权重。

原加载器无条件导入缺失的 `models/nafnet.py`，导致当前模型也无法加载。新入口只导入完整且匹配的 `nafnet_model.py`，严格加载并逐张量核对664个张量。配置为width32、编码块[2,2,4,8]、中间12块、解码块[2,2,2,2]；不强行使用作者当前GoPro预设[1,1,1,28]/1/[1,1,1,1]。与[作者基础NAFNet](https://github.com/megvii-research/NAFNet/tree/2b4af71ebe098a92a75910c233a3965a3e93ede4)在同配置同权重的小图前向核对一致，详细来源/源码哈希见 `data/source_record.json`。

输入为 `data/samples_manifest.json` 固定的6对GoPro测试样本，沿用 `blur_gamma`，与另外两方案逐文件哈希相同。RGB float32 0–1，不额外做伽马变换；保持原图尺寸，模型内部右/下补零至16倍数后裁回。保留原方案uint8截断量化，无AMP、锐化或对比度增强。sharp仅供对比脚本读取。

限制：原权重未记录可核实的公开下载地址及训练时blur/blur_gamma对应关系；原dataset.py只查找名为blur的目录。已核实数值范围/通道/结构/加载匹配，但不声称训练模糊版本已确认。本次明确统一输入blur_gamma；这限制了跨方案效果归因。新机器需从原小组项目复制同一权重并核对哈希。

已先完成单张，再实际推理全部6图。原尺寸PNG在 `result/restored`，本方案整体与固定局部对比在 `result/comparison`，实际耗时、权重核对及配对检查在 `result/run_record.json`。本轮未训练、未计算评价指标、未制作PPT。唯一的三方案总对比位于同级 `MSCNN/result/comparison/all_methods`。
