%% 1. 设置相对路径与人工选定参数（不需要先运行搜索脚本）
clear; clc;
root = fileparts(mfilename('fullpath'));
% 近似模型：空间不变、匀速直线运动。参数来自候选全图及固定局部的人工比较。
% 每行对应 1.png、2.png、3.png、4.png；LEN：像素；THETA：相对水平逆时针角度。
% NSR为人工调节的噪信比近似值，不是测量得到的真实噪声方差。
parameters = [5 0 0.01; ...
              7 135 0.01; ...
              5 10 0.01; ...
              3 55 0.01];
% 两组固定局部：[左列 上行 宽 高]；所有方法使用完全相同的整数像素索引。
roi1 = [390 345 240 160; 530 210 240 160; 600 115 240 160; 330 210 240 160];
roi2 = [800 520 240 160; 170 420 240 160; 130 555 240 160; 780 480 240 160];
observations = ["长椅与砖缝的轮廓略有增强，树叶细节仍有模糊。"; ...
                "石块与部分路面轮廓更清楚，但树叶仍有拖影和颗粒伪影。"; ...
                "窗框边缘略有增强，墙面仍有细颗粒与弱振铃，改善有限。"; ...
                "店面轮廓仅有轻微改善，细字仍不可辨，高反差边缘仍有重影。"];
out = fullfile(root, 'results');
folders = {'wiener', 'comparison', 'crops'};
for k = 1:numel(folders)
    target = fullfile(out, folders{k});
    if ~exist(target, 'dir'), mkdir(target); end
end
toolbox = ver('images');
fprintf('MATLAB：%s\nImage Processing Toolbox：%s\n', version, toolbox.Version);

%% 2. 保持原始尺寸，使用同一个PSF分别处理RGB三个通道
for id = [3 1 2 4]                 % 先检查第3张建筑图
    I = im2double(imread(fullfile(root, 'origin_image', sprintf('%d.png', id))));
    N = im2double(imread(fullfile(root, 'nafnet_reference', sprintf('%d_nafnet.png', id))));
    assert(size(I, 3) == 3 && isequal(size(I), size(N)), '输入与NAFNet尺寸或通道不一致。');
    LEN = parameters(id, 1);
    THETA = parameters(id, 2);
    NSR = parameters(id, 3);
    PSF = fspecial('motion', LEN, THETA);
    J = zeros(size(I));
    for c = 1:3
        tapered = edgetaper(I(:, :, c), PSF);  % 减轻DFT周期边界引入的振铃
        J(:, :, c) = deconvwnr(tapered, PSF, NSR);
    end
    assert(isequal(size(J), size(I)) && all(isfinite(J(:))), '复原结果尺寸或数值异常。');
    % 仅裁到PNG可表示的[0,1]；没有锐化、对比度拉伸或其他美化。
    J = min(max(J, 0), 1);
    filename = fullfile(out, 'wiener', sprintf('%d_wiener.png', id));
    imwrite(J, filename);
    info = imfinfo(filename);
    assert(info.Height == size(I, 1) && info.Width == size(I, 2), '保存尺寸异常。');

    %% 3. 原始模糊图—维纳复原图—已有NAFNet结果：统一尺度展示
    pictures = {I, J, N};
    method_names = {'原始模糊图', '维纳复原（人工选参）', '已有 NAFNet（同学结果）'};
    f = figure('Visible', 'off', 'Color', 'w', 'Position', [30 30 1920 510]);
    for k = 1:3
        ax = axes('Parent', f, 'Position', [0.025+(k-1)*0.325, 0.08, 0.30, 0.72]);
        imshow(pictures{k}, 'Parent', ax);
        title(ax, method_names{k}, 'FontName', 'Microsoft YaHei', 'FontSize', 14);
        if k == 1
            rectangle(ax, 'Position', roi1(id, :), 'EdgeColor', [1 0.3 0], 'LineWidth', 1.2);
            rectangle(ax, 'Position', roi2(id, :), 'EdgeColor', [0 0.8 1], 'LineWidth', 1.2);
            text(ax, roi1(id,1), roi1(id,2)-10, '局部1', 'Color', [1 0.3 0], 'FontName', 'Microsoft YaHei');
            text(ax, roi2(id,1), roi2(id,2)-10, '局部2', 'Color', [0 0.8 1], 'FontName', 'Microsoft YaHei');
        end
    end
    annotation(f, 'textbox', [0.02 0.91 0.96 0.07], 'EdgeColor', 'none', ...
        'String', sprintf('图%d | 人工辅助：LEN=%g px，THETA=%g°（逆时针），NSR=%g | 三图同尺度', id, LEN, THETA, NSR), ...
        'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 16);
    drawnow;
    exportgraphics(f, fullfile(out, 'comparison', sprintf('%d_comparison.png', id)), 'Resolution', 120);
    close(f);

    %% 4. 两处固定位置的局部放大：相同裁剪位置、大小与显示尺度
    f = figure('Visible', 'off', 'Color', 'w', 'Position', [30 30 1680 940]);
    for r = 1:2
        if r == 1, box = roi1(id, :); else, box = roi2(id, :); end
        rows = box(2) + (0:box(4)-1);
        cols = box(1) + (0:box(3)-1);
        for k = 1:3
            ax = axes('Parent', f, 'Position', [0.035+(k-1)*0.325, 0.52-(r-1)*0.44, 0.29, 0.30]);
            imshow(pictures{k}(rows, cols, :), 'Parent', ax);
            title(ax, {method_names{k}, sprintf('局部%d：[x=%d y=%d w=%d h=%d]', r, box)}, ...
                'FontName', 'Microsoft YaHei', 'FontSize', 12);
        end
    end
    annotation(f, 'textbox', [0.02 0.91 0.96 0.07], 'EdgeColor', 'none', ...
        'String', sprintf('图%d固定局部对比 | LEN=%g，THETA=%g°，NSR=%g | 每块均为240×160像素', id, LEN, THETA, NSR), ...
        'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 15);
    drawnow;
    exportgraphics(f, fullfile(out, 'crops', sprintf('%d_crops.png', id)), 'Resolution', 120);
    close(f);
    fprintf('图%d完成：LEN=%g，THETA=%g，NSR=%g；保存尺寸 %d×%d。\n', ...
        id, LEN, THETA, NSR, info.Width, info.Height);
end

%% 5. 保存参数表，记录人工选择及局部坐标，不计算图像评价指标
Image = compose('%d.png', (1:4)');
LEN = parameters(:, 1); THETA = parameters(:, 2); NSR = parameters(:, 3);
Selection = repmat("人工辅助：观察全图与固定局部候选，兼顾拖影、噪声、重影和振铃", 4, 1);
T = table(Image, LEN, THETA, NSR, Selection, observations, ...
    roi1(:,1), roi1(:,2), roi1(:,3), roi1(:,4), roi2(:,1), roi2(:,2), roi2(:,3), roi2(:,4), ...
    'VariableNames', {'Image','LEN','THETA','NSR','Selection','Observation', ...
    'ROI1_x','ROI1_y','ROI1_w','ROI1_h','ROI2_x','ROI2_y','ROI2_w','ROI2_h'});
writetable(T, fullfile(root, 'parameters.csv'), 'Encoding', 'UTF-8');
fprintf('全部完成；输出为原尺寸PNG及同尺度对比图，参数表为 parameters.csv。\n');
