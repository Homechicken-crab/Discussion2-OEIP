%% 1. 固定GoPro六样本；沿用已选参数，不读取sharp、不再搜索
clear; clc;
base = fileparts(fileparts(mfilename('fullpath')));
data = fullfile(base,'data'); out = fullfile(data,'restored');
M = jsondecode(fileread(fullfile(data,'samples_manifest.json')));
T = readtable(fullfile(data,'parameters.csv'),'TextType','string','Encoding','UTF-8');
assert(height(T)==numel(M.samples));
if ~exist(out,'dir'), mkdir(out); end
record.method = 'Wiener'; record.matlab = version;
record.toolbox = ver('images'); record.references_used_for_parameter_selection = false;
record.pipeline = 'im2double; fspecial motion; RGB edgetaper/deconvwnr; clamp [0,1]; original resolution';

%% 2. 整图RGB逐通道复原；只在保存PNG前限幅，无额外增强
for i = 1:numel(M.samples)
    s = M.samples(i); assert(T.Sample(i)==string(s.id));
    input_path = fullfile(data,s.blur_gamma);
    I = im2double(imread(input_path));
    assert(isequal(size(I),[720 1280 3]));
    LEN = T.LEN(i); THETA = T.THETA(i); NSR = T.NSR(i);
    started = tic; PSF = fspecial('motion',LEN,THETA); J = zeros(size(I));
    for c = 1:3
        J(:,:,c) = deconvwnr(edgetaper(I(:,:,c),PSF),PSF,NSR);
    end
    assert(isequal(size(J),size(I)) && all(isfinite(J(:))));
    output_path = fullfile(out,[s.id '.png']);
    imwrite(min(max(J,0),1),output_path);
    info = imfinfo(output_path); assert(info.Width==1280 && info.Height==720);
    entry.id = s.id; entry.width = size(I,2); entry.height = size(I,1);
    entry.LEN = LEN; entry.THETA = THETA; entry.NSR = NSR;
    entry.input_sha256 = file_sha256(input_path);
    assert(strcmp(entry.input_sha256,s.blur_gamma_sha256));
    entry.output_sha256 = file_sha256(output_path);
    entry.processing_seconds_including_png = toc(started);
    record.samples(i) = entry;
    fprintf('%s: LEN=%g THETA=%g NSR=%g; 1280x720 RGB saved.\n',s.id,LEN,THETA,NSR);
end

%% 3. 单份运行记录；完整参数另在data/parameters.csv
fid = fopen(fullfile(data,'run_record.json'),'w','n','UTF-8');
assert(fid~=-1); fprintf(fid,'%s',jsonencode(record,'PrettyPrint',true)); fclose(fid);

function digest = file_sha256(path)
    fid = fopen(path,'rb'); assert(fid~=-1);
    bytes = fread(fid,Inf,'*uint8'); fclose(fid);
    md = java.security.MessageDigest.getInstance('SHA-256'); md.update(bytes);
    digest = lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
