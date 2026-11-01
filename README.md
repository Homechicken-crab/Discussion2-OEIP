# 讨论2：单幅运动模糊图像复原

**当前阶段：保留原4图MATLAB维纳实验，新增作者GOPRO_L1多尺度CNN预训练推理；已在固定6对GoPro测试样本上实际运行CNN与MATLAB维纳，保存原尺寸输出及四项对比。未计算评价指标，未制作PPT。**

题目：对手机拍摄物体时因快速运动造成的图像模糊进行复原。至少研究并实现一种算法；展示涵盖研究目标、算法方案、验证结果、结论总结。

本项目采用“GPT 指导、Codex 执行与记录、GPT 审查”的协作方式。**采用现有模糊图片和官方GoPro配对测试样本，不安排实拍。**

## 当前实现与结果

新增 [多尺度CNN](多尺度CNN/README.md)：Nah等人CVPR2017方法对应的作者PyTorch实现及GOPRO_L1单精度预训练权重推理，没有自行训练。GoPro是数据集；NAFNet是组员已完成的独立方案，本次未处理其模型或项目。6对固定样本、来源/配置/哈希、实际环境与运行命令见该目录说明；[四项对比](多尺度CNN/results/comparisons)展示GoPro模糊图、MATLAB维纳、CNN和sharp参考。

旧MotionDeblur_Wiener目录已完整改名为维纳滤波，没有保留重复旧目录；原4图未标为GoPro。

正式 MATLAB 项目为 [维纳滤波](维纳滤波)。使用 im2double → fspecial('motion',LEN,THETA) → RGB 逐通道 edgetaper 和 deconvwnr → 限幅保存。保持 1280×720 原分辨率，不做额外锐化或对比度增强。THETA 按 MATLAB 的相对水平逆时针约定记录。参数由观察候选图人工辅助选择，未采用质量分数自动排名。

- [首轮结果](维纳滤波/results)与[首轮参数](维纳滤波/parameters.csv)保留不变，基线提交为 [4229fb4](https://github.com/Homechicken-crab/Discussion2-OEIP/commit/4229fb479523ed39e1ff9b5ad0612f91ee2c6503)。
- [第二轮输出与观察](维纳滤波/results_round2_image3/observations.md)：两条计算路径检查通过；粗搜194组、细搜75组，保留单位核控制与两组代表候选。三处固定局部均从同一整图结果裁取。当前方案改善仍有限，不能据此确定存在空间变化模糊。
- 原图在 origin_image，已有 NAFNet 结果在 nafnet_reference；NAFNet 仅供视觉对照，不是清晰真值。初期提出的逆滤波、CLS、合成评价不属于本轮已执行内容。

## 阅读顺序

1. [实际方案](docs/01_实际方案.md)：研究问题、选择理由、分阶段流程与决策条件。
2. [课件学习对应](docs/02_课件学习对应.md)：第四、五章的知识如何进入算法。
3. [验证与记录规范](docs/03_验证与记录规范.md)：早期后续验证设计；其中合成实验与指标尚未执行。
4. [GPT 审查与协作](docs/04_GPT审查与协作.md)：可直接提供给指导 GPT 的任务说明。
5. [展示结构草案](docs/05_展示结构草案.md)：历史提纲，本轮不制作 PPT。
6. [实施说明](docs/06_实施说明.md)：代码入口、参数约定和后续运行方法。

## 文件组织

```text
维纳滤波/          MATLAB：原4图脚本和分轮结果；新增wiener_gopro.m与results_gopro
多尺度CNN/         作者模型代码、配置、固定6对样本、CNN输出及四项对比（权重忽略）
docs/                课程对应、方法说明、协作提示词及历史计划
src/                 早期Python准备代码；新CNN入口在多尺度CNN/infer.py
configs/             早期Python参数示例，不供MATLAB或CNN读取
data/private/        早期Python私有输入占位，不供MATLAB读取
data/public/         早期Python公开副本占位；GoPro输入在多尺度CNN/samples
results/             早期占位目录；实际结果在两个方案各自目录
sources/courseware/  用户提供的两章课件，供 GPT 对照审查
sources/assignment.png  用户提供的题目截图
sources/local/       完整提取文本与转换中间文件，仅本地保存
sources/manifest.json  来源文件大小与 SHA-256
validation/          代码准备状态与诊断记录，不是正式实验结果
```

按用户要求，题目、两章课件和本次准备材料一同同步到公开仓库，便于 GPT 对照审查。课件版权归原作者，来源资料不适用项目代码的任何许可。含本地路径的转换中间文件不上传。以后图片的原始 EXIF 与路径保留在本地，公开展示副本去除元数据。

## MATLAB 运行方式

打开 维纳滤波/wiener_restore.m，采用 round2 模式可独立生成本轮代表结果，不依赖先运行搜索脚本。search_motion_parameters.m 的 stage 可选择 consistency、coarse、fine；一致性模式应先运行搜索脚本，再运行正式脚本的一致性模式。MATLAB R2022a + Image Processing Toolbox 11.5 已实际使用。新增GoPro实验直接运行维纳滤波/wiener_gopro.m（默认restore），使用同级多尺度CNN内固定样本，输出和参数独立保存到results_gopro。

大量候选及一致性检查的临时数组留在项目 temp_candidates/，不提交 GitHub。首轮与第二轮正式结果分别保存；均未计算 PSNR、SSIM、NIQE、CPBD 等评价指标，也没有合成验证成绩。

## 来源

课程定位见 [课件学习对应](docs/02_课件学习对应.md)。当前 MATLAB 接口见 [fspecial](https://www.mathworks.com/help/images/ref/fspecial.html)、[edgetaper](https://www.mathworks.com/help/images/ref/edgetaper.html)、[deconvwnr](https://www.mathworks.com/help/images/ref/deconvwnr.html)。早期 Python 实现采用不同角度和边界约定，不与 MATLAB 结果混用。
