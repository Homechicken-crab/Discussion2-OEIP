%% 1. GoPro固定6样本；不覆盖原4图参数和分轮结果
clear; clc;
root = fileparts(mfilename('fullpath'));
cnn = fullfile(fileparts(root),'多尺度CNN');
mode = 'restore';                    % 'preview' 少量候选；'restore' 正式输出
M = jsondecode(fileread(fullfile(cnn,'samples_manifest.json')));
% 只根据模糊输入及候选人工选择，不读取sharp，不自动计算分数。
parameters = [3 0 .03;5 0 .03;5 15 .01;3 0 .03;5 0 .03;3 45 .03];
roi = [400 180 256 192;800 400 256 192];  % 0基坐标，与清单一致
out = fullfile(root,'results_gopro');
if strcmp(mode,'preview'), out = fullfile(root,'temp_candidates','gopro'); end
if ~exist(out,'dir'), mkdir(out); end
ids = strings(numel(M.samples),1);

%% 2. 整图处理，RGB逐通道；原分辨率，无额外增强
for i = 1:numel(M.samples)
    s = M.samples(i); ids(i) = string(s.id);
    I = im2double(imread(fullfile(cnn,s.blur_gamma)));
    assert(isequal(size(I),[720 1280 3]));
    if strcmp(mode,'preview')
        choices = [3 parameters(i,2) .01;5 parameters(i,2) .01;9 parameters(i,2) .01; ...
                   3 parameters(i,2) .03;5 parameters(i,2) .03;9 parameters(i,2) .03];
        pictures = {I}; labels = {'Blur input'};
    else
        assert(strcmp(mode,'restore')); choices = parameters(i,:);
    end
    for p = 1:size(choices,1)
        LEN = choices(p,1); THETA = choices(p,2); NSR = choices(p,3);
        PSF = fspecial('motion',LEN,THETA); J = zeros(size(I));
        for c = 1:3
            J(:,:,c) = deconvwnr(edgetaper(I(:,:,c),PSF),PSF,NSR);
        end
        assert(isequal(size(J),size(I)) && all(isfinite(J(:))));
        J = min(max(J,0),1);
        if strcmp(mode,'preview')
            pictures{end+1} = J;
            labels{end+1} = sprintf('L=%g T=%g N=%g',LEN,THETA,NSR);
        else
            imwrite(J,fullfile(out,[s.id '.png']));
            info = imfinfo(fullfile(out,[s.id '.png']));
            assert(info.Width==1280 && info.Height==720);
        end
    end
    if strcmp(mode,'preview')
        f = figure('Visible','off','Color','w','Position',[20 20 1900 740]);
        for r = 1:2
            rows = roi(r,2)+(1:roi(r,4)); cols = roi(r,1)+(1:roi(r,3));
            for k = 1:7
                ax = axes('Parent',f,'Position',[.008+(k-1)*.142,.08+(2-r)*.43,.135,.34]);
                imshow(pictures{k}(rows,cols,:),'Parent',ax);
                title(ax,{labels{k},sprintf('ROI%d',r)},'Interpreter','none','FontSize',10);
            end
        end
        annotation(f,'textbox',[.01 .93 .98 .05],'String',s.id,'EdgeColor','none', ...
            'Interpreter','none','HorizontalAlignment','center');
        exportgraphics(f,fullfile(out,[s.id '_preview.png']),'Resolution',110); close(f);
    end
    fprintf('%s %s completed.\n',s.id,mode);
end

%% 3. 新样本参数单独记录；仅正式运行保存
if strcmp(mode,'restore')
    T = table(ids,parameters(:,1),parameters(:,2),parameters(:,3), ...
        repmat("人工辅助；仅观察模糊输入和候选，未使用sharp选参",numel(ids),1), ...
        'VariableNames',{'Sample','LEN','THETA','NSR','Selection'});
    writetable(T,fullfile(out,'parameters.csv'),'Encoding','UTF-8');
    fprintf('MATLAB %s, Image Processing Toolbox; no metrics.\n',version);
end
