clc;
clear all;
close all;

Norm = 1;   NormFilter = 1;    Latex = 1;

sampleName = "";
sampleReg = '';
Side = "";

waveMin = 550;
waveMax = 951;

numSteps = 41;
stepSize = 0.5;
startPos = 0;

saveFolderPD = mkdir('Planar Diffraction');
saveFolderpathPD = fullfile('Planar Diffraction');

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
end

Pols = [0 45 90 -45];

pminus = count(Side, upper(Side));
if pminus == 1
    pminus = '+';
elseif pminus == 0
    pminus = '-';
end

dataFilePD = append(sampleName, '_Reg', sampleReg, '_', Side, 'Side');
sampleTitlePD = append(sampleName, ' Region ', sampleReg, ' ', pminus, upper(Side), ' Side');

h5dataPath = append('Planar Diffraction/', Side, '/', sampleName, '_Region', sampleReg, '_', Side, '_LPScan.h5');
IPValues = unique(h5read(h5dataPath, '/IP_Theta'));
CWValues = unique(h5read(h5dataPath, '/CW_Theta' ));
CPValues = unique(h5read(h5dataPath, '/CP_Theta' ));
waveValues = unique(h5read(h5dataPath, '/wavelength'));
intensityValues = h5read(h5dataPath, '/intensity');
wavelengthValues = h5read(h5dataPath, '/wavelength');

waveMask = waveValues >= waveMin & waveValues <= waveMax;
waveValues = wavelengthValues(waveMask);
intensityValues = intensityValues(find(waveMask == 1, 1, 'first'):find(waveMask == 1, 1, 'last'),:);

numIncident = length(IPValues);
s = size(intensityValues);
intensityMatrix = zeros(numIncident,s(1),s(2)/(2*numIncident));
posScale = linspace(0,stepSize*s(2)/(2*numIncident),s(2)/(2*numIncident));

for i = 0:((s(2)/(2*numIncident))-1)
    n = 8*i+1;
    for k = 1:numIncident
        intensityData(k,:,i+1) = intensityValues(:,n+k-1) + intensityValues(:,n+k);
        intensity(k,:,i+1) = smooth(intensityData(k,:,i+1), 21);

        if Norm == 1
            intensityNorm(k,:,i+1) = (intensityValues(:,n+k-1) + intensityValues(:,n+k))./Norm_VIS;
        end
    end
end

h = [0 0 0; 1 1 1 ; 0 0 0]/3;

cmap_ST = jet;
for AnglesIP = 1:192                     
    adj_cmap_ST(AnglesIP,:) = cmap_ST(63+AnglesIP,:);  
end 

PDcol = [0 max(reshape(intensity(k,:,:), s(1), s(2)/(numIncident*2)), [], 'all')];
PDNormcol = [0 max(reshape(intensityNorm(k,:,:), s(1), s(2)/(numIncident*2)), [], 'all')];
PDNormFiltcol = [0 max(imfilter(reshape(intensityNorm(k,:,:), s(1), s(2)/(numIncident*2)),h), [], 'all')];

status = fclose('all');
f1 = figure(1);
f1.Position = [100 100 1000 500];
f1.Resize = 'off';

for k = 1:numIncident

    subplot(2,2,k);
    dataPlot = reshape(intensity(k,:,:), s(1), s(2)/(numIncident*2));
    surf(waveValues, posScale, dataPlot')
    shading interp
    colormap(adj_cmap_ST)
    colorbar
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(PDcol)
    title(append(sampleName, ' Region ', sampleReg, ' ', pminus, ' ', Side, ' Side ', int2str(Pols(k)), '\circ Polarization', newline, ' UnNormalized', newline)) 
    ylabel('Position (mm)')
    xlabel('Wavelength (nm)')
    ylim([0 20]);
    xlim([waveMin waveMax]);
    view(0,90)
end

set(f1, 'Name', sampleTitlePD + " In-Plane Diffraction UnNormalized", 'NumberTitle', 'off');
savefig(f1, fullfile(pwd, saveFolderpathPD, sampleTitlePD + " In-Plane Diffraction UnNormalized.fig"));
if Latex == 1
    exportgraphics(f1, fullfile(pwd, saveFolderpathLatex, sampleTitlePD + " In-Plane Diffraction UnNormalized.png"), 'Resolution', 300);
end

if Norm == 1
    f2 = figure(2);
    f2.Position = [100 100 1000 500];
    f2.Resize = 'off';
    
    for k = 1:numIncident
    
        subplot(2,2,k);
        dataPlot = reshape(intensityNorm(k,:,:), s(1), s(2)/(numIncident*2));
        surf(waveValues, posScale, dataPlot')
        shading interp
        colormap(adj_cmap_ST)
        colorbar
        c = colorbar;
        c.Ruler.Exponent = 0;
        clim(PDNormcol)
        title(append(sampleName, ' Region ', sampleReg, ' ', pminus, ' ', Side, ' Side ', int2str(Pols(k)), '\circ Polarization', newline, ' Normalized', newline)) 
        ylabel('Position (mm)')
        xlabel('Wavelength (nm)')
        ylim([0 20]);
        xlim([waveMin waveMax]);
        view(0,90)
    end

    set(f2, 'Name', sampleTitlePD + " In-Plane Diffraction Normalized", 'NumberTitle', 'off');
    savefig(f2, fullfile(pwd, saveFolderpathPD, sampleTitlePD + " In-Plane Diffraction Normalized.fig"));
    if Latex == 1
        exportgraphics(f2, fullfile(pwd, saveFolderpathLatex, sampleTitlePD + " In-Plane Diffraction Normalized.png"), 'Resolution', 300);
    end
end

if NormFilter == 1
    f3 = figure(3);
    f3.Position = [100 100 1000 500];
    f3.Resize = 'off';

    for k = 1:numIncident
    
        subplot(2,2,k);
        dataPlot = imfilter(reshape(intensityNorm(k,:,:), s(1), s(2)/(numIncident*2)),h);
        surf(waveValues, posScale, dataPlot')
        shading interp
        colormap(adj_cmap_ST)
        colorbar
        c = colorbar;
        c.Ruler.Exponent = 0;
        clim(PDcol)
        title(append(sampleName, ' Region ', sampleReg, ' ', pminus, ' ', Side, ' Side ', int2str(Pols(k)), '\circ Polarization', newline, ' Normalized and Filtered', newline)) 
        ylabel('Position (mm)')
        xlabel('Wavelength (nm)')
        ylim([0 20]);
        xlim([waveMin waveMax]);
        view(0,90)
    end

    set(f3, 'Name', sampleTitlePD + " In-Plane Diffraction Normalized and Filtered", 'NumberTitle', 'off');
    savefig(f3, fullfile(pwd, saveFolderpathPD, sampleTitlePD + " In-Plane Diffraction Normalized and Filtered.fig"));
    if Latex == 1
        exportgraphics(f3, fullfile(pwd, saveFolderpathLatex, sampleTitlePD + " In-Plane Diffraction Normalized and Filtered.png"), 'Resolution', 300);
    end
end

close('all');
