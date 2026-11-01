%% 1. 第3张图：保留4229fb4首轮结果，本轮独立输出
clear; clc;
root = fileparts(mfilename('fullpath'));
mode = 'round2';                   % 'consistency' 核对；'round2' 导出本轮代表结果
% 参数由候选全图和多个固定局部人工选择，不是自动最优值。
parameters = [1 0 0.03; 5 10 0.03; 9 15 0.03];
names = {'control_L1','candidate_A','candidate_B'};
roles = {'接近无运动核的控制项，不解释为去除拖影','人工选取的折中候选','较强补偿的对照候选'};
roi = [600 115 240 160; 900 280 240 160; 400 380 240 160];
roi_names = {'窗框和墙面','另一处建筑边缘','树枝细节'};
I = im2double(imread(fullfile(root,'origin_image','3.png')));
B = im2double(imread(fullfile(root,'results','wiener','3_wiener.png')));
N = im2double(imread(fullfile(root,'nafnet_reference','3_nafnet.png')));
assert(size(I,3)==3 && isequal(size(I),size(B),size(N)));
fprintf('MATLAB %s；图3原尺寸%d×%d；模式%s。\n',version,size(I,2),size(I,1),mode);
if strcmp(mode,'consistency')
    parameters = [1 0 0.01;5 10 0.01]; names = {'consistency_L1','consistency_L5'};
    out = fullfile(root,'temp_candidates','round2','consistency');
else
    assert(strcmp(mode,'round2'),'mode取值错误。');
    out = fullfile(root,'results_round2_image3');
end
if ~exist(out,'dir'), mkdir(out); end

%% 2. 与搜索脚本相同的像素范围、角度、边界、RGB处理及裁剪
for p = 1:size(parameters,1)
    LEN = parameters(p,1); THETA = mod(parameters(p,2),180); NSR = parameters(p,3);
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
    if strcmp(mode,'consistency'), formal_before_clip = J; end
    J = min(max(J,0),1);           % 仅限幅，无锐化、直方图拉伸等处理
    filename = fullfile(out,sprintf('3_%s.png',names{p}));
    imwrite(J,filename);
    info = imfinfo(filename);
    assert(info.Width==size(I,2) && info.Height==size(I,1));
    if strcmp(mode,'consistency')
        S = load(fullfile(out,sprintf('search_L%g_float.mat',LEN)));
        assert(isequal(formal_before_clip,S.search_before_clip),'搜索与正式脚本浮点结果不一致。');
        assert(isequal(imread(filename),imread(fullfile(out,sprintf('search_L%g.png',LEN)))),'两条路径PNG不一致。');
        if LEN==5
            assert(isequal(imread(filename),imread(fullfile(root,'results','wiener','3_wiener.png'))), ...
                '与4229fb4首轮图3结果不一致。');
            fprintf('PASS：与4229fb4首轮图3的PNG一致。\n');
        end
        fprintf('PASS：LEN=%g，搜索/正式脚本未裁剪浮点结果及PNG逐像素一致。\n',LEN);
        continue;
    end

    %% 3. 原始图—首轮维纳—本轮候选—已有NAFNet；全部同尺度
    pictures = {I,B,J,N};
    methods = {'原始模糊图','首轮维纳：5 / 10° / 0.01', ...
        sprintf('本轮：%g / %g° / %g',LEN,THETA,NSR),'已有NAFNet（不是清晰真值）'};
    f = figure('Visible','off','Color','w','Position',[30 30 1920 500]);
    for k = 1:4
        ax = axes('Parent',f,'Position',[0.025+(k-1)*0.245,0.08,0.22,0.70]);
        imshow(pictures{k},'Parent',ax);
        title(ax,methods{k},'FontName','Microsoft YaHei','FontSize',12,'Interpreter','none');
        if k == 1
            colors = [1 .3 0; 0 .7 1; 0 .8 .2];
            for r = 1:3
                rectangle(ax,'Position',roi(r,:),'EdgeColor',colors(r,:),'LineWidth',1);
                text(ax,roi(r,1),roi(r,2)-10,sprintf('ROI%d',r),'Color',colors(r,:));
            end
        end
    end
    annotation(f,'textbox',[.02 .91 .96 .07],'EdgeColor','none', ...
        'String',sprintf('图3第二轮 | %s | LEN=%g THETA=%g° NSR=%g | %s', ...
        names{p},LEN,THETA,NSR,roles{p}),'HorizontalAlignment','center', ...
        'FontName','Microsoft YaHei','FontSize',14,'Interpreter','none');
    drawnow; exportgraphics(f,fullfile(out,sprintf('3_%s_comparison.png',names{p})),'Resolution',120); close(f);

    %% 4. 三个区域均从同一张整图结果裁取，不作局部独立复原
    f = figure('Visible','off','Color','w','Position',[30 30 1920 1350]);
    for r = 1:3
        rows = roi(r,2)+(0:roi(r,4)-1); cols = roi(r,1)+(0:roi(r,3)-1);
        for k = 1:4
            ax = axes('Parent',f,'Position',[.025+(k-1)*.245,.055+(3-r)*.28,.22,.22]);
            imshow(pictures{k}(rows,cols,:),'Parent',ax);
            title(ax,{methods{k},sprintf('ROI%d %s [%d %d %d %d]',r,roi_names{r},roi(r,:))}, ...
                'FontName','Microsoft YaHei','FontSize',10,'Interpreter','none');
        end
    end
    annotation(f,'textbox',[.02 .93 .96 .05],'EdgeColor','none', ...
        'String',sprintf('图3多区域同尺度对比 | %s | LEN=%g THETA=%g° NSR=%g | 每块240×160像素', ...
        names{p},LEN,THETA,NSR),'HorizontalAlignment','center', ...
        'FontName','Microsoft YaHei','FontSize',14,'Interpreter','none');
    drawnow; exportgraphics(f,fullfile(out,sprintf('3_%s_regions.png',names{p})),'Resolution',120); close(f);
    fprintf('已保存%s：LEN=%g THETA=%g NSR=%g；1280×720 RGB。\n',names{p},LEN,THETA,NSR);
end
if strcmp(mode,'consistency'), return; end

%% 5. 参数和ROI表；首轮目录和首轮parameters.csv保持不动
T = table(string(names(:)),parameters(:,1),parameters(:,2),parameters(:,3),string(roles(:)), ...
    'VariableNames',{'Candidate','LEN','THETA','NSR','ManualSelectionRole'});
writetable(T,fullfile(out,'parameters.csv'),'Encoding','UTF-8');
R = table(string(roi_names(:)),roi(:,1),roi(:,2),roi(:,3),roi(:,4), ...
    'VariableNames',{'Region','x','y','width','height'});
writetable(R,fullfile(out,'regions.csv'),'Encoding','UTF-8');
fprintf('完成：首轮结果未覆盖；本轮结果在results_round2_image3。\n');
