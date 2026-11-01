# 图像输入

已收到 4 张现成的模糊图片，均为 1280×720 RGB，位于 ../Wiener_Filter/origin_image/。已有 NAFNet 对照位于 ../Wiener_Filter/nafnet_reference/，不作为清晰真值。不需要安排实拍。

这里的 `private/`、`public/` 为早期 Python 准备流程的目录约定，不供当前 MATLAB 脚本读取。正式输入与结果以 Wiener_Filter 中的文件为准。

不要把题目截图、课件示例或合成图冒充本次手机真实模糊输入。

新增GoPro固定6对测试样本在 ../MultiScale_CNN/samples/；清单见同项目 samples_manifest.json。两方案读取同一模糊输入，sharp仅供展示核对。
