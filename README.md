# 讨论2：单幅运动模糊图像复原

**当前阶段：准备工作与方案讨论。尚未接收待处理图片，未开展正式复原实验，也没有实验结果或最终 PPT。**

题目：对手机拍摄物体时因快速运动造成的图像模糊进行复原。至少研究并实现一种算法；展示涵盖研究目标、算法方案、验证结果、结论总结。

本项目采用“GPT 指导、Codex 执行与记录、GPT 审查”的协作方式。**输入是一张现成的运动模糊图片，不安排实拍。**

## 推荐方案

先判断整图或局部区域能否近似采用匀速直线运动模型，再用参数化运动 PSF 和常数 K 近似维纳滤波复原。用阈值截断逆滤波作基线；必要时扩展约束最小二乘。模糊核方向、长度需要从输入图片估计并做候选比较；当前代码不会自动找到真实模糊核。

真实单图作为应用验证；后续另设有已知清晰真值的合成对照来检查算法、噪声敏感性和核参数失配。两类证据分别报告，不用合成成绩替代真实图像效果。

## 阅读顺序

1. [实际方案](docs/01_实际方案.md)：研究问题、选择理由、分阶段流程与决策条件。
2. [课件学习对应](docs/02_课件学习对应.md)：第四、五章的知识如何进入算法。
3. [验证与记录规范](docs/03_验证与记录规范.md)：哪些指标能用、如何避免错误结论。
4. [GPT 审查与协作](docs/04_GPT审查与协作.md)：可直接提供给指导 GPT 的任务说明。
5. [展示结构草案](docs/05_展示结构草案.md)：按题目四部分组织，当前仅为提纲。
6. [实施说明](docs/06_实施说明.md)：代码入口、参数约定和后续运行方法。

## 文件组织

```text
docs/                方案、课程对应、评价规范、GPT 提示词、展示提纲
src/                 复原与候选比较工具（准备版）
configs/             尚待图片到位后调整的候选参数
data/private/        原始图片，仅本地保存，不进入 Git
data/public/         获得用户授权且去元数据的公开输入副本
results/             正式实验结果（当前为空，只有状态说明）
sources/courseware/  用户提供的两章课件，供 GPT 对照审查
sources/assignment.png  用户提供的题目截图
sources/local/       完整提取文本与转换中间文件，仅本地保存
sources/manifest.json  来源文件大小与 SHA-256
validation/          代码准备状态与诊断记录，不是正式实验结果
```

按用户要求，题目、两章课件和本次准备材料一同同步到公开仓库，便于 GPT 对照审查。课件版权归原作者，来源资料不适用项目代码的任何许可。含本地路径的转换中间文件不上传。以后图片的原始 EXIF 与路径保留在本地，公开展示副本去除元数据。

## 准备代码

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\deblur.py --help
.\.venv\Scripts\python.exe src\check_numerics.py
```

代码仅做准备性数值自检。正式实验等待输入图片和指导 GPT 对方案的审查。后续每批结果必须保存输入哈希、区域坐标、参数、运行环境、原始浮点复原值和展示图。

## 来源

课程资料定位见 [课件学习对应](docs/02_课件学习对应.md)。外部技术依据采用 [OpenCV 官方运动去模糊教程](https://docs.opencv.org/4.13.0/d1/dfd/tutorial_motion_deblur_filter.html)、[scikit-image 复原 API](https://scikit-image.org/docs/0.26.x/api/skimage.restoration.html) 与 [评价指标 API](https://scikit-image.org/docs/0.26.x/api/skimage.metrics.html)。这些来源支持方法说明；本项目尚未验证其在待提供图片上的效果。
