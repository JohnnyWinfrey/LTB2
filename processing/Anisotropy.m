clc;
clear all;
close all;

Norm = 1;   Circ = 1;   Latex = 1;

sampleName = "";
sampleReg = '';
Side = "";

waveMin = 550;
waveMax = 951;

numSteps = 41;
stepSize = 0.5;

saveFolderAN = mkdir('Anisotropy');
saveFolderpathAN = fullfile('Anisotropy');

if Latex == 1
    saveFolderLatex = mkdir('Latex');
    saveFolderpathLatex = fullfile('Latex');
end

if Norm == 1
    refFile_VIS = readmatrix('VISRef_4_1_2026.txt');
    try
        refValues = unique(refFile_VIS(:,1));
        refMask = refValues >= waveMin & refValues <= waveMax;
        refIntensity = refFile_VIS(:,2);
    catch e
        error(append('Cant find a VIS norm spectrum'))
    end
    NormVIS = refIntensity / max(refIntensity);
    Norm_VIS = NormVIS(refMask);

    if Circ == 1
        refFile_Circ = readmatrix('CIRCRef_3_20_2026_Subt2__0__3.txt');
        try
            refValuesCirc = unique(refFile_Circ(:,1));
            refMaskCirc = refValuesCirc >= waveMin & refValuesCirc <= waveMax;
            refIntensityCirc = refFile_Circ(:,2);
        catch e
            error(append('Cant find a Circ norm spectrum'))
        end
        NormCirc = refIntensityCirc / max(refIntensityCirc);
        Norm_Circ = NormCirc(refMaskCirc);
    end
end

% Pols order matches PlanarDiffraction.m: k=1->0deg, k=2->45deg, k=3->90deg, k=4->-45deg
Pols = [0 45 90 -45];
PolsCirc = ["RH" "LH"];

pminus = count(Side, upper(Side));
if pminus == 1
    pminus = '+';
elseif pminus == 0
    pminus = '-';
end

sampleTitleAN = append(sampleName, ' Region ', sampleReg, ' ', pminus, upper(Side), ' Side');

saveFolderpathPD = fullfile('Planar Diffraction');
h5dataPath = append(saveFolderpathPD, '/', Side, '/', sampleName, '_Region', sampleReg, '_', Side, '_LPScan.h5');

waveValuesAll = unique(h5read(h5dataPath, '/wavelength'));
intensityValues = h5read(h5dataPath, '/intensity');
wavelengthValues = h5read(h5dataPath, '/wavelength');

waveMask = waveValuesAll >= waveMin & waveValuesAll <= waveMax;
waveValues = wavelengthValues(waveMask);
intensityValues = intensityValues(find(waveMask == 1, 1, 'first'):find(waveMask == 1, 1, 'last'), :);

numIncident = length(Pols);
s = size(intensityValues);
numPos = s(2) / (2 * numIncident);
posScale = linspace(0, stepSize * (numPos - 1), numPos);

for i = 0:(numPos - 1)
    n = 8 * i + 1;
    for k = 1:numIncident
        intensityData(k,:,i+1) = intensityValues(:, n+k-1) + intensityValues(:, n+k);
        if Norm == 1
            intensityNorm(k,:,i+1) = (intensityValues(:, n+k-1) + intensityValues(:, n+k)) ./ Norm_VIS;
        end
    end
end

if Circ == 1
    saveFolderpathCirc = fullfile('CircPol');
    h5dataPathCirc = append(saveFolderpathCirc, '/', Side, '/', sampleName, '_Region', sampleReg, '_', Side, '_CPScan.h5');
    intensityValuesCirc = h5read(h5dataPathCirc, '/intensity');
    intensityValuesCirc = intensityValuesCirc(find(waveMask == 1, 1, 'first'):find(waveMask == 1, 1, 'last'), :);
    sCirc = size(intensityValuesCirc);
    numPosCirc = sCirc(2) / 8;
    posScaleCirc = linspace(0, stepSize * (numPosCirc - 1), numPosCirc);

    intensityCirc = zeros(length(PolsCirc), sCirc(1), numPosCirc);
    intensityCircNorm = zeros(length(PolsCirc), sCirc(1), numPosCirc);
    for i = 0:(numPosCirc - 1)
        for l = 1:length(PolsCirc)
            intensityCirc(l,:,i+1) = intensityValuesCirc(:, 8*i+2) + intensityValuesCirc(:, 8*i+4);
            if Norm == 1
                intensityCircNorm(l,:,i+1) = intensityCirc(l,:,i+1) ./ Norm_Circ.';
            end
        end
    end
end

%% Anisotropy Calculation
% S1: (90deg - 0deg) / (90deg + 0deg)   k=3 vs k=1
% S2: (45deg - (-45deg)) / (45deg + (-45deg))   k=2 vs k=4

if Norm == 0
    int_filt = intensityData;
else
    int_filt = intensityNorm;
end

Diff_S1 = squeeze(int_filt(3,:,:) - int_filt(1,:,:));
Diff_S2 = squeeze(int_filt(2,:,:) - int_filt(4,:,:));
Avg_S1  = squeeze((int_filt(3,:,:) + int_filt(1,:,:)) / 2);
Avg_S2  = squeeze((int_filt(2,:,:) + int_filt(4,:,:)) / 2);
Ani_S1  = 0.5 * Diff_S1 ./ Avg_S1;
Ani_S2  = 0.5 * Diff_S2 ./ Avg_S2;

if Circ == 1
    if Norm == 0
        circ_filt = intensityCirc;
    else
        circ_filt = intensityCircNorm;
    end
    Diff_S3 = squeeze(circ_filt(2,:,:) - circ_filt(1,:,:));
    Avg_S3  = squeeze((circ_filt(2,:,:) + circ_filt(1,:,:)) / 2);
    Ani_S3  = 0.5 * Diff_S3 ./ Avg_S3;
end

% Spatial filter (position smoothing)
h = [0 0 0; 1 1 1; 0 0 0] / 3;
Ani_S1 = imfilter(Ani_S1, h);
Ani_S2 = imfilter(Ani_S2, h);
if Circ == 1
    Ani_S3 = imfilter(Ani_S3, h);
end

numSubplots = 2 + (Circ == 1);

cmap_AN = jet;
for n = 1:192
    adj_cmap_AN(n,:) = cmap_AN(63+n,:);
end

status = fclose('all');

%% Surface Plots
f1 = figure(1);
f1.Position = [100 100 400 700];
f1.Resize = 'off';

subplot(numSubplots,1,1);
hold on;
v = [-0.5 0 0.5];
contour(waveValues, posScale, Ani_S1', v, 'LineColor', 'k', 'ZLocation', 'zmax');
surfc(waveValues, posScale, Ani_S1');
shading interp
colormap(adj_cmap_AN)
title(append(sampleTitleAN, ' Anisotropy', newline, 'S1'));
ylabel('Position (mm)');
view(0, 90);
c = colorbar;
c.Ruler.Exponent = 0;
clim([-0.5 0.5]);
xlim([waveMin waveMax]);

subplot(numSubplots,1,2);
hold on;
contour(waveValues, posScale, Ani_S2', v, 'LineColor', 'k', 'ZLocation', 'zmax');
surfc(waveValues, posScale, Ani_S2');
shading interp
colormap(adj_cmap_AN)
title('S2');
ylabel('Position (mm)');
view(0, 90);
c = colorbar;
c.Ruler.Exponent = 0;
clim([-0.5 0.5]);
xlim([waveMin waveMax]);

if Circ == 1
    subplot(numSubplots,1,3);
    hold on;
    contour(waveValues, posScaleCirc, Ani_S3', v, 'LineColor', 'k', 'ZLocation', 'zmax');
    surfc(waveValues, posScaleCirc, Ani_S3');
    shading interp
    colormap(adj_cmap_AN)
    title('S3');
    xlabel('Wavelength (nm)');
    ylabel('Position (mm)');
    view(0, 90);
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim([-0.5 0.5]);
    xlim([waveMin waveMax]);
end

set(f1, 'Name', sampleTitleAN + " Anisotropy", 'NumberTitle', 'off');
savefig(f1, fullfile(pwd, saveFolderpathAN, sampleTitleAN + " Anisotropy.fig"));
if Latex == 1
    exportgraphics(f1, fullfile(pwd, saveFolderpathLatex, sampleTitleAN + " Anisotropy.png"), 'Resolution', 300);
end

%% Line Plots (3 positions: 25%, center, 75%)
posIdx = [round(numPos * 0.25), round(numPos / 2), round(numPos * 0.75)];
posLabels = {[num2str(posScale(posIdx(1)), '%.1f') ' mm'], ...
             [num2str(posScale(posIdx(2)), '%.1f') ' mm'], ...
             [num2str(posScale(posIdx(3)), '%.1f') ' mm']};

f2 = figure(2);
f2.Position = [100 100 400 700];
f2.Resize = 'off';

subplot(numSubplots,1,1);
plot(waveValues, Ani_S1(:,posIdx(1)), 'r', waveValues, Ani_S1(:,posIdx(2)), 'k', waveValues, Ani_S1(:,posIdx(3)), 'b');
title('S1 Anisotropy');
ylabel('Anisotropy');
ylim([-1.5 1.5]);
xlim([waveMin waveMax]);
yticks([-1 0 1]);

subplot(numSubplots,1,2);
plot(waveValues, Ani_S2(:,posIdx(1)), 'r', waveValues, Ani_S2(:,posIdx(2)), 'k', waveValues, Ani_S2(:,posIdx(3)), 'b');
title('S2 Anisotropy');
ylabel('Anisotropy');
ylim([-1.5 1.5]);
xlim([waveMin waveMax]);
yticks([-1 0 1]);

if Circ == 1
    posIdxCirc = [round(numPosCirc * 0.25), round(numPosCirc / 2), round(numPosCirc * 0.75)];
    subplot(numSubplots,1,3);
    plot(waveValues, Ani_S3(:,posIdxCirc(1)), 'r', waveValues, Ani_S3(:,posIdxCirc(2)), 'k', waveValues, Ani_S3(:,posIdxCirc(3)), 'b');
    title('S3 Anisotropy');
    xlabel('Wavelength (nm)');
    ylabel('Anisotropy');
    ylim([-1.5 1.5]);
    xlim([waveMin waveMax]);
    yticks([-1 0 1]);
end

L = legend(posLabels);
set(get(L, 'Title'), 'String', 'Position');
set(findall(gcf, '-property', 'FontSize'), 'FontSize', 8)
set(L, 'FontSize', 6);
set(L, 'Position', [0.8, 0.85, 0.05, 0.05]);
set(findall(gcf, '-property', 'LineWidth'), 'LineWidth', 1.5)
set(findall(gcf, '-property', 'FontWeight'), 'FontWeight', 'normal')
set(findall(gcf, '-property', 'PlotBoxAspectRatio'), 'PlotBoxAspectRatio', [1, 1, 1])
set(findall(gcf, '-property', 'YGrid'), 'YGrid', 'on')

set(f2, 'Name', sampleTitleAN + " View", 'NumberTitle', 'off');
savefig(f2, fullfile(pwd, saveFolderpathAN, sampleTitleAN + " View.fig"));
if Latex == 1
    exportgraphics(f2, fullfile(pwd, saveFolderpathLatex, sampleTitleAN + " View.png"), 'Resolution', 300);
end

close('all');
