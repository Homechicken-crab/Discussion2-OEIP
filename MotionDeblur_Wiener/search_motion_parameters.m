%% 1. 读取路径，集中设置人工搜索参数
clear; clc;
root = fileparts(mfilename('fullpath'));
image_ids = [3 1 2 4];              % 第3张建筑图优先；可只选一张缩短搜索时间
stage = 'fine';                     % 'coarse' 粗搜；'fine' 每张图的邻域细搜
coarse_LEN = [3 5 9 13 17 25];
coarse_THETA = 0:15:165;            % MATLAB：相对水平逆时针，方向轴以180度为周期
% 下面各元胞对应图1～4；看过粗搜全图和局部后人工缩小范围。
fine_LEN = {[3 5 7], [5 7 9], [3 5 7], [3 4 5]};
fine_THETA = {[175 0 5], [130 135 140], [0 10 20], [45 55 65]};
fine_NSR = [0.001 0.003 0.01];
% 固定局部坐标 [左列 上行 宽 高]；采用整数索引，恰好取宽×高像素。
roi = [390 345 240 160; ...         % 图1：长椅、树木及路面
       530 210 240 160; ...         % 图2：树干、石块与背景
       600 115 240 160; ...         % 图3：窗框与建筑立面
       330 210 240 160];            % 图4：店面、走廊边缘
out = fullfile(root, 'temp_candidates', stage);
if ~exist(out, 'dir'), mkdir(out); end
fprintf('MATLAB %s；阶段 %s；参数由人工观察候选图选择。\n', version, stage);

%% 2. 按图、长度和噪信比生成候选；全分辨率RGB分别复原
for id = image_ids
    if strcmp(stage, 'coarse')
        LEN_values = coarse_LEN; THETA_values = coarse_THETA; NSR_values = 0.003;
    else
        LEN_values = fine_LEN{id}; THETA_values = fine_THETA{id}; NSR_values = fine_NSR;
    end
    I = im2double(imread(fullfile(root, 'origin_image', sprintf('%d.png', id))));
    rows = roi(id, 2) + (0:roi(id, 4)-1);
    cols = roi(id, 1) + (0:roi(id, 3)-1);
    image_out = fullfile(out, sprintf('image_%d', id));
    if ~exist(image_out, 'dir'), mkdir(image_out); end
    for LEN = LEN_values
        for NSR = NSR_values
            full_images = cell(1, numel(THETA_values)+1);
            crop_images = cell(size(full_images));
            labels = cell(size(full_images));
            full_images{1} = I;
            crop_images{1} = I(rows, cols, :);
            labels{1} = '原始模糊图';
            for k = 1:numel(THETA_values)
                THETA = mod(THETA_values(k), 180);
                PSF = fspecial('motion', LEN, THETA);
                J = zeros(size(I));
                for c = 1:3
                    tapered = edgetaper(I(:, :, c), PSF);
                    J(:, :, c) = deconvwnr(tapered, PSF, NSR);
                end
                % 仅作PNG显示范围裁剪；不锐化、不拉伸对比度、不改变分辨率。
                J = min(max(J, 0), 1);
                full_images{k+1} = J;
                crop_images{k+1} = J(rows, cols, :);
                labels{k+1} = sprintf('THETA=%g°', THETA);
                fprintf('图%d：LEN=%g THETA=%g NSR=%g\n', id, LEN, THETA, NSR);
            end

            %% 3. 导出同尺度全图拼图与固定位置局部拼图
            for view = 1:2
                if view == 1
                    pictures = full_images; suffix = 'full';
                else
                    pictures = crop_images; suffix = 'crop';
                end
                ncol = 4; nrow = ceil(numel(pictures)/ncol);
                f = figure('Visible', 'off', 'Color', 'w', ...
                    'Position', [30 30 1600 280*nrow+70]);
                for k = 1:numel(pictures)
                    row = ceil(k/ncol); col = mod(k-1, ncol)+1;
                    ax = axes('Parent', f, 'Position', ...
                        [0.025+(col-1)*0.245, 0.04+(nrow-row)*0.75/nrow, 0.22, 0.67/nrow]);
                    imshow(pictures{k}, 'Parent', ax);
                    title(ax, labels{k}, 'FontName', 'Microsoft YaHei', 'FontSize', 11, 'Interpreter', 'none');
                end
                annotation(f, 'textbox', [0.02 0.87 0.96 0.11], 'EdgeColor', 'none', ...
                    'String', {sprintf('图%d | %s | LEN=%g px，NSR=%g | 人工辅助搜索', id, stage, LEN, NSR), ...
                    sprintf('固定ROI=[%d %d %d %d]；角度相对水平逆时针', roi(id, :))}, ...
                    'HorizontalAlignment', 'center', 'FontName', 'Microsoft YaHei', 'FontSize', 14);
                name = sprintf('L%g_N%g_%s.png', LEN, NSR, suffix);
                drawnow;
                exportgraphics(f, fullfile(image_out, name), 'Resolution', 110);
                close(f);
            end
        end
    end
end
fprintf('候选已保存到 temp_candidates；没有用质量分数自动选参。\n');
