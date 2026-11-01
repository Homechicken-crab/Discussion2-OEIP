# 多尺度 CNN：作者预训练模型推理复现

使用 Nah、Kim、Lee 的 CVPR 2017 方法对应的[作者 PyTorch 实现](https://github.com/SeungjunNah/DeepDeblur-PyTorch)，提交 `e92dc7c3337127887da617ffe819b49cb022fd81`。本次只使用作者 GOPRO_L1 单精度预训练权重推理，没有自行训练，也没有复现论文全部训练流程。与 NAFNet 为不同方法；本次未操作 NAFNet 模型或项目。

## 来源与实现

- [论文](https://openaccess.thecvf.com/content_cvpr_2017/html/Nah_Deep_Multi-Scale_Convolutional_CVPR_2017_paper.html)、[作者 GoPro 数据页](https://seungjunnah.github.io/Datasets/gopro.html)。GoPro 是配对数据集，按 CC BY 4.0 使用，作者为 Seungjun Nah 等。
- [GOPRO_L1 权重包](https://drive.google.com/file/d/1AfZhyUXEA8_UdZco9EdtpWjTBAb8BbWv/view)：实际下载约130 MB包，模型本体46,943,690字节。SHA-256：`8d02a04244f0f54ba645834b6726eafa4348e88df870a31a8ccb037e63ea0e49`；包哈希见 model_config.json。权重不进入 Git。
- 实际包内配置保存在 official_training_args.txt：MSResNet、3尺度、19残差块/尺度、64通道、5×5卷积、Gaussian金字塔、rgb_range=255、blur_gamma、single、amp=False。模型配置与其一致。
- official_model 中3个网络文件与上述作者提交逐字节相同，保留 MIT LICENSE。data_common.py 只将 `multichannel=True` 改成 `channel_axis=-1`，适配 scikit-image 0.25.2；文件哈希见 source_record.json。
- infer.py 使用作者网络及预处理函数，独立推理入口避开旧训练器和指标依赖。`torch.load(weights_only=True)` 后要求存在 G，`strict=True` 加载并逐张量核对；缺失、形状不符或哈希错误直接终止。实际244个张量完整加载，11,721,321个参数。
- RGB float32输入保持0–255，网络内部减127.5；不做0–1归一化或额外伽马变换。保留作者Gaussian金字塔和由粗到细前向；输出按作者方式+0.5、限幅转uint8。推理使用 eval、inference_mode，关闭AMP/TF32，无额外锐化或对比度增强。
- 作者 PyTorch 版默认设置与原论文不同，包括RGB范围0–255、L1而非默认对抗损失、训练批量16及分布式训练选项。本次指定非AMP的GOPRO_L1，不把这些设置写成原论文完整训练复现。包内历史指标字符串与图表不代表本次计算的指标。

## 固定样本与运行

samples_manifest.json 在推理前固定：官方测试集序列按名称排序取前6个，每个取排序后的中间帧；包含不同街景、花卉、建筑和车辆场景，没有按效果换样本。严格使用同序列、同文件名的 blur_gamma 与 sharp。

| 序列 | 文件名 | MATLAB LEN / THETA / NSR |
|---|---|---|
| GOPR0384_11_00 | 000051.png | 3 / 0 / 0.03 |
| GOPR0384_11_05 | 004051.png | 5 / 0 / 0.03 |
| GOPR0385_11_01 | 003061.png | 5 / 15 / 0.01 |
| GOPR0396_11_00 | 000051.png | 3 / 0 / 0.03 |
| GOPR0410_11_00 | 000168.png | 5 / 0 / 0.03 |
| GOPR0854_11_00 | 000051.png | 3 / 45 / 0.03 |

数据来自作者页面链接的 Hugging Face ZIP，通过 HTTP Range 读取目录及选定12张PNG，没有下载完整压缩包、训练集或完整测试集。样本字节数及各文件SHA-256见清单。原来4张图仍保留原身份，未标为GoPro。

本机独立环境：`D:\codex\2026-11-01\xian\work\multiscale_env`，Python 3.12.6、PyTorch 2.11.0+cu128、CUDA运行库12.8、驱动596.49、RTX4060 Laptop GPU 8GB。依赖检查通过；其余版本见 results/environment.json。

在本目录运行（本机实际使用上方环境的 Scripts/python.exe）：

```powershell
python infer.py --limit 1
python infer.py
python make_comparisons.py
```

新机器可用 `py -3.12 -m venv .venv`，再用 `.venv\Scripts\python.exe -m pip install -r requirements.txt`。用同一环境运行 download_weights.py 获取指定权重；选定小样本已随仓库提供，需要重新获取时运行 prepare_samples.py。网络不可用或权重不匹配时会报错。本轮仅验证GPU运行，未测试CPU耗时。

权重首次已成功从官方链接下载并完成推理；之后额外检查重新下载时遇到过Google Drive的TLS EOF连接错误。当前本机权重已验证，不受影响，下载脚本会优先复用已验证文件；新机器若遇此网络错误需重试，或从上方官方链接手动下载同一包并核对哈希。

MATLAB R2022a + Image Processing Toolbox 11.5：打开同级 `Wiener_Filter/wiener_gopro.m` 直接运行（默认restore），输出在 `Wiener_Filter/results_gopro/`。两个方案读取 samples 下完全相同的 blur_gamma 文件；sharp 只在配对检查和对比图脚本读取。维纳选参时尚未展示sharp：固定方向分别0、0、15、0、0、45度，每图仅试LEN=3/5/9与NSR=0.01/0.03的6组，共36组；人工检查两个固定局部后选择上述折中参数，无自动评分。候选留在维纳项目temp_candidates/gopro，忽略不提交。

## 已执行与结果

先单张成功，再批量6张。单张网络前向3.58秒；批量每张前向3.13–3.67秒，含预处理和PNG保存3.39–4.03秒；首次模型导入/加载时间不计入上述单图计时。峰值为PyTorch已分配显存约0.83 GB，非整机全部显存。实际记录见 results/inference_single.json、inference_run.json。

- CNN原尺寸PNG：results/cnn/；维纳原尺寸PNG及独立参数表：同级Wiener_Filter/results_gopro/。全部1280×720 RGB；本批尺寸可被4整除，无需补边。其他尺寸先按作者右侧/下侧复制边缘补至4的倍数，推理后裁回，不缩小输入。
- 四项整体和局部对比：results/comparisons/，共12张。整体统一0.5倍；局部统一2倍最近邻显示。每张图的两处ROI均在推理前固定为0基 `[400,180,256,192]`、`[800,400,256,192]`，四方法位置/尺度相同；复原整图之后裁局部。
- 已实际查看全部6张整体对比及6张局部对比，配对/尺寸/输入哈希检查记录在 results/pairing_and_output_checks.json。没有PSNR、SSIM、NIQE等本轮评价指标，没有PPT。

观察：第一处街景中CNN的行人和黄色立柱边缘更集中，墙面细节仍有限；第二处街景的人物轮廓、衣服和头发较维纳自然，细小文字仍不清楚；第三处街景整体人脸和门窗轮廓改善，但固定局部的窗台和路面细纹仍明显弱于sharp。花卉中CNN减少花瓣边缘拖影，部分叶片细节仍有平滑感；楼体车辆场景中CNN的窗格和车身改善明显，车轮与细树枝仍未完全恢复；停车场场景中CNN车尾轮廓、车灯及树干更明确，树皮、地砖和背景细节仍与参考有差异。维纳的小核只作保守补偿，仍有条纹/颗粒/重影，不能据此声称所有维纳参数都无效。CNN也没有完全恢复参考细节；6张固定样本和视觉观察不足以支持整个测试集的定量结论。

原维纳4图、首轮/第二轮结果、参数与NAFNet已有对照完整迁移，既未覆盖为GoPro输出，也未重新运行NAFNet。改名后原wiener_restore.m实际运行通过，9张第二轮PNG的解码像素与原结果一致；保留原PNG文件字节以避免仅编码元数据变化。
