# Wiener filter

MATLAB直接运行 `code/run_wiener.m`，或 `run('C:/Users/Lenovo/Desktop/Discussion2/Wiener_Filiter/code/run_wiener.m')`。需MATLAB及Image Processing Toolbox；本机实际使用R2022a / Toolbox11.5。路径相对脚本解析，可独立运行。

同一批6对GoPro官方测试样本在data/samples，使用blur_gamma，与MSCNN、NAFNet的输入和sharp逐文件哈希一致。清单与0基ROI在data/samples_manifest.json，数据来源为[作者GoPro页面](https://seungjunnah.github.io/Datasets/gopro.html)（CC BY4.0）。sharp只用于展示、核对和PSNR评价，不用于复原或选参。

保留此前已人工选定的6组参数，不重新搜索，不使用sharp选参。按清单顺序LEN/THETA/NSR为：3/0/0.03，5/0/0.03，5/15/0.01，3/0/0.03，5/0/0.03，3/45/0.03。详见data/parameters.csv；THETA遵循MATLAB相对水平逆时针约定。

使用im2double、fspecial('motion')、RGB逐通道edgetaper和deconvwnr。整图1280×720处理，保存前仅限幅[0,1]，不做额外锐化、对比度增强等处理。仍是空间不变匀速直线PSF近似，条纹、振铃和残余模糊需从结果中如实判断。

已实际运行6图。原尺寸PNG在data/restored，运行环境、输入/输出哈希及参数在data/run_record.json；result只保留12张本方案三项对比PNG。生成对比：安装code/requirements.txt后运行 `python code/make_comparisons.py`；添加 `--check-only` 只核对而不改写PNG。局部来自整图结果，坐标及显示尺度与其他方案一致。总对比统一在项目根目录Result/comparison。

PSNR统一由MSCNN/code/evaluate_psnr.py读取已保存输出计算，数据和图表在根目录Result/evaluation；全图RGB、峰值255、无裁边，逐图PSNR再取六图算术平均。此次不重新复原、不调参、不新增其他指标或PPT。此前旧实验材料仍在项目外归档。
