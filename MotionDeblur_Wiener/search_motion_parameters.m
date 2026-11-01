%% 1. 第3张建筑图：一致性检查、扩大粗搜与人工细搜
clear; clc;
root = fileparts(mfilename('fullpath'));
stage = 'fine';                    % 'consistency'、'coarse' 或 'fine'
coarse_LEN = [1 3 5 7 9 13 17 25 33];
coarse_THETA = 0:15:165;
coarse_NSR = [0.01 0.03];
% 细搜范围在查看粗搜拼图后人工修改；不按清晰度分数排名。
fine_LEN = [3 5 7];
fine_THETA = [0 5 10 15 20];
fine_NSR = [0.003 0.01 0.03 0.05 0.1];
% [左列 上行 宽 高]，全部为整图复原后裁剪；不进行局部独立反卷积。
roi = [600 115 240 160; 900 280 240 160; 400 380 240 160];
roi_names = {'窗框和墙面', '另一处建筑边缘', '树枝细节'};
out = fullfile(root, 'temp_candidates', 'round2', stage);
if ~exist(out, 'dir'), mkdir(out); end
I = im2double(imread(fullfile(root, 'origin_image', '3.png')));
assert(size(I,3) == 3);
if strcmp(stage, 'consistency')
    LEN_values = [1 5]; THETA_values = 10; NSR_values = 0.01;
elseif strcmp(stage, 'coarse')
    LEN_values = coarse_LEN; THETA_values = coarse_THETA; NSR_values = coarse_NSR;
else
    assert(strcmp(stage, 'fine'), 'stage取值错误。');
    LEN_values = fine_LEN; THETA_values = fine_THETA; NSR_values = fine_NSR;
end
all_parameters = zeros(0,3);
fprintf('MATLAB %s；图3；阶段 %s；全分辨率RGB；先整图处理再裁剪。\n', version, stage);

%% 2. 构建PSF，RGB逐通道edgetaper和deconvwnr，与正式脚本一致
for LEN = LEN_values
    angles = THETA_values;
    if LEN == 1
        angles = 0;                % 单位核与方向无关，只算一次，作为控制项
    end
    for NSR = NSR_values
        crops = cell(3, numel(angles)+1);
        labels = cell(1, numel(angles)+1);
        labels{1} = {'原始模糊图', '未处理'};
        for r = 1:3
            rows = roi(r,2)+(0:roi(r,4)-1); cols = roi(r,1)+(0:roi(r,3)-1);
            crops{r,1} = I(rows,cols,:);
        end
        for k = 1:numel(angles)
            THETA = mod(angles(k),180); % 相对水平逆时针，方向轴以180度为周期
            PSF = fspecial('motion',LEN,THETA);
            % 两个R2022a接口均不接受标量核；用等价3×3中心脉冲表示LEN=1。
            if numel(PSF)==1, PSF = [0 0 0;0 PSF 0;0 0 0]; end
            J = zeros(size(I));
            for c = 1:3
                tapered = edgetaper(I(:,:,c),PSF);
                J(:,:,c) = deconvwnr(tapered,PSF,NSR);
            end
            assert(isequal(size(J),size(I)) && all(isfinite(J(:))));
            if LEN==1, assert(all(abs(J(:)-I(:)/(1+NSR))<1e-12)); end
            if strcmp(stage,'consistency')
                search_before_clip = J;
                save(fullfile(out,sprintf('search_L%g_float.mat',LEN)),'search_before_clip');
            end
            J = min(max(J,0),1);   % 仅裁至PNG表示范围，无额外锐化或对比度处理
            if strcmp(stage,'consistency')
                imwrite(J,fullfile(out,sprintf('search_L%g.png',LEN)));
            end
            for r = 1:3
                rows = roi(r,2)+(0:roi(r,4)-1); cols = roi(r,1)+(0:roi(r,3)-1);
                crops{r,k+1} = J(rows,cols,:);
            end
            labels{k+1} = {sprintf('LEN=%g  THETA=%g°',LEN,THETA),sprintf('NSR=%g',NSR)};
            all_parameters(end+1,:) = [LEN THETA NSR];
            fprintf('LEN=%g THETA=%g NSR=%g\n',LEN,THETA,NSR);
        end
        if strcmp(stage,'consistency'), continue; end

        %% 3. 只导出三个固定局部的候选拼图；全部候选留在临时目录
        for r = 1:3
            ncol = 4; nrow = ceil(size(crops,2)/ncol);
            f = figure('Visible','off','Color','w','Position',[30 30 1800 320*nrow+120]);
            for k = 1:size(crops,2)
                row = ceil(k/ncol); col = mod(k-1,ncol)+1;
                ax = axes('Parent',f,'Position', ...
                    [0.025+(col-1)*0.245,0.04+(nrow-row)*0.75/nrow,0.22,0.64/nrow]);
                imshow(crops{r,k},'Parent',ax);
                title(ax,labels{k},'FontName','Microsoft YaHei','FontSize',10,'Interpreter','none');
            end
            note = '';
            if LEN == 1, note = ' | LEN=1为接近无运动核的控制，不代表去除拖影'; end
            annotation(f,'textbox',[0.02 0.87 0.96 0.11],'EdgeColor','none', ...
                'String',{sprintf('图3 | %s | %s | LEN=%g NSR=%g%s',stage,roi_names{r},LEN,NSR,note), ...
                sprintf('整图复原后裁剪 ROI=[%d %d %d %d]；THETA相对水平逆时针',roi(r,:))}, ...
                'HorizontalAlignment','center','FontName','Microsoft YaHei','FontSize',13);
            drawnow;
            exportgraphics(f,fullfile(out,sprintf('ROI%d_L%g_N%g.png',r,LEN,NSR)),'Resolution',110);
            close(f);
        end
    end
end
T = array2table(all_parameters,'VariableNames',{'LEN','THETA','NSR'});
writetable(T,fullfile(out,'search_parameters.csv'));
fprintf('完成：本阶段实际计算%d组；只作人工比较，不计算图像评价指标。\n',height(T));
