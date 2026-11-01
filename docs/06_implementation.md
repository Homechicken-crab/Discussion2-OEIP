# 当前 MATLAB 实施说明

正式入口为 Wiener_Filter 中的两个独立脚本。已在本机 MATLAB R2022a + Image Processing Toolbox 11.5 实际使用。早期 src/deblur.py 仅为历史准备代码，不是当前实验入口。

## wiener_restore.m

默认 round2 模式读取第 3 张原图、首轮 PNG、已有 NAFNet 对照，并根据脚本顶部人工选择的代表参数独立生成 results_round2_image3/。不需要先运行搜索脚本。首轮 results/、parameters.csv 和原图、NAFNet 文件保持不变，首轮源代码仍可在提交 4229fb4 中查看。

输出包含原尺寸 RGB 代表结果、四方法全图对比、三个固定区域的局部对比，以及本轮参数与 ROI 表。不生成额外锐化或对比度增强结果。

## search_motion_parameters.m

修改顶部 stage 选择阶段：

- consistency：使用 LEN=1 控制和首轮 LEN=5、THETA=10°、NSR=0.01，保存临时浮点结果和 PNG。然后将正式脚本 mode 设为 consistency 并运行，核对两条路径的未限幅浮点数组和 PNG；其中 LEN=5 再与首轮 PNG 逐像素比较。
- coarse：扩大 LEN、THETA、NSR 搜索，只导出三个固定局部的候选拼图。LEN=1 与方向无关，只计算 0°。
- fine：按已查看候选人工缩小范围。实际运行的范围由脚本和本轮 observations.md 记录，建议范围不自动视为已执行。

候选、参数遍历表、数值检查数组与运行日志均放 temp_candidates/，不提交 GitHub。没有自动质量分数排名。

## 统一处理约定

输入通过 im2double 转为 double；保持原始 1280×720，不缩放，不作 sRGB 线性化。THETA 为相对水平逆时针角度，以 180° 为周期。三个 RGB 通道采用同一 PSF，各自 edgetaper 后 deconvwnr；结果仅限幅至 [0,1] 后保存 PNG。

R2022a 的两个复原接口不接受标量 PSF。LEN=1 的 fspecial 结果以等价 3×3 中心脉冲表示，因此仍能调用同样的边界与复原流程。它的输出在浮点容差内等于 I/(1+NSR)，只有增益变化，不能解释为去除了运动拖影。

本轮所有局部从整图结果裁取，没有局部独立反卷积：

| 区域 | x | y | 宽 | 高 |
|---|---:|---:|---:|---:|
| 窗框和墙面 | 600 | 115 | 240 | 160 |
| 另一处建筑边缘 | 900 | 280 | 240 | 160 |
| 树枝细节 | 400 | 380 | 240 | 160 |

坐标为 MATLAB 整数像素索引，实际范围为 x:x+宽-1、y:y+高-1。所有方法使用相同裁剪位置与显示尺度。NAFNet 仅为已有视觉对照，不是配对清晰真值。
