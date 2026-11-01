# GPT 审查与协作：当前 MATLAB 排查

## 当前状态

已收到 4 张 1280×720 RGB 原图和同学的 4 张 NAFNet 结果。首轮 MATLAB 实现与正式结果已提交为 4229fb4，保存在 Wiener_Filter/results/；首轮参数表不覆盖。当前集中处理第 3 张，继续使用 fspecial('motion')、edgetaper、deconvwnr。

本轮目标是区分：首轮参数探索不足，还是统一匀速直线 PSF 近似的适用性有限。只作数值路径一致性检查和视觉比较，不计算 PSNR、SSIM、NIQE、CPBD，不制作 PPT；已有 NAFNet 不是清晰真值。

## 可复制给指导 GPT 的审查指令

> 请阅读 Wiener_Filter/search_motion_parameters.m、wiener_restore.m，以及 results_round2_image3/observations.md、parameters.csv 和多区域对比图。以 4229fb4 为首轮基线，核查：两条代码路径是否在 im2double、角度、边界、RGB 与限幅方式上相同；LEN=1 是否被明确当作控制；实际搜索范围与记录是否一致；代表参数是否减少拖影，而非仅使画面变平滑；窗框、另一处建筑边缘和树枝的副作用是否如实记录。所有区域应从同一整图结果裁取。不要把 NAFNet 当作真值，不要用无真值清晰度分数排名，也不要把区域观感不同直接断言为空间变化模糊。

如果当前 GPT 环境不能直接读取仓库文件，请提供相应 Markdown、MATLAB 代码和图像文件，或上传正式材料压缩包。

## 每轮交接内容

- 代码提交与本轮结果目录；原始图与首轮基线保持情况。
- 实际执行的 LEN、THETA、NSR 范围，包含控制项；说明哪些是建议但尚未运行。
- 实际查看的候选图和保留参数，不将未查看的内容写成观察事实。
- 固定 ROI 坐标、统一显示尺度、整图处理后裁剪的约定。
- 改善、颗粒、重影、光晕、条纹等副作用，以及可支持的有限结论。
- 下一步可验证的问题；不保证继续调参必然解决。

初期 Python 准备实现、合成评价计划和 PPT 提纲保留作历史材料，不是本轮已经执行的内容。

## 新增多尺度CNN审查入口

本页上文保留第二轮维纳阶段记录。当前还已完成作者GOPRO_L1预训练推理及固定6对GoPro与MATLAB维纳对照，见 ../MultiScale_CNN/README.md。审查 model_config.json、source_record.json、samples_manifest.json、infer.py、results/inference_run.json 及同尺度对比；重点核对完整权重加载、RGB 0–255、blur_gamma配对、sharp未作为网络输入、无自行训练或指标成绩。
