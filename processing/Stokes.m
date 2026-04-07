clc;
clear all;
close all;

Norm = 1;   Latex = 1;

sampleName = "";
sampleReg = '';
Side = "";

waveMin = 550;
waveMax = 951;

numIncident = 10;
incidentSpacing = 10;
startIncident = 0;

saveFolderST = mkdir('Stokes');
saveFolderpathST = fullfile('Stokes');

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

pminus = count(Side, upper(Side));
if pminus == 1
    pminus = '+';
elseif pminus == 0
    pminus = '-';
end

dataFileST = append(sampleName, '_Reg', sampleReg, '_', Side, 'Side');
sampleTitleST = append(sampleName, ' Region ', sampleReg, ' ', pminus, upper(Side), ' Side');

h5dataPath = append(saveFolderpathST, '/', Side, '/', sampleName, '_Region', sampleReg, '_', Side, '_stokesScan.h5');
info = h5info(h5dataPath);
dataSet = {info.Datasets.Name};

for r = 1:length(dataSet)
    data{:,r} = h5read(h5dataPath, append('/', dataSet{r}));
end

IPValues = data{:,3};
CWValues = data{:,2};
CPValues = data{:,1};
wavelengthValues = data{:,6};
intensityValues = data{:,5};

waveMask = wavelengthValues >= waveMin & wavelengthValues <= waveMax;
waveValues = wavelengthValues(waveMask);

Mask00 = CWValues == 0 & CPValues == 0;
Mask045 = CWValues == 0 & CPValues == 45;
Mask4545 = CWValues == 45 & CPValues == 45;
Mask450 = CWValues == 45 & CPValues == 0;

I00 = data{:,5}(:,Mask00);
%I00 = smooth(I00,21);
I045 = data{:,5}(:,Mask045);
%I045 = smooth(I045,21);
I4545 = data{:,5}(:,Mask4545);
%I4545 = smooth(I4545,21);
I450 = data{:,5}(:,Mask450);
%I450 = smooth(I450,21);

S0 = (I450 + I045).';
S0 = S0(:,find(waveMask == 1, 1, "first"):find(waveMask == 1, 1, "last"));
S1 = (2*(I00-0.5*(I450+I045))).';
S1 = S1(:,find(waveMask == 1, 1, "first"):find(waveMask == 1, 1, "last"));
S2 = (2*(I4545-0.5*(I450+I045))).';
S2 = S2(:,find(waveMask == 1, 1, "first"):find(waveMask == 1, 1, "last"));
S3 = (2*(I045-0.5*(I450+I045))).';
S3 = S3(:,find(waveMask == 1, 1, "first"):find(waveMask == 1, 1, "last"));
  
S0Norm = S0./S0;
S1Norm = S1./S0;
S2Norm = S2./S0;
S3Norm = S3./S0;

if Norm == 1
    S0SourceNorm = S0./(Norm_VIS');
    S1SourceNorm = S1./(Norm_VIS');
    S2SourceNorm = S2./(Norm_VIS');
    S3SourceNorm = S3./(Norm_VIS');
end

SDOP = sqrt((reshape(S1,numIncident,[]).^2 + reshape(S2,numIncident,[]).^2 + reshape(S3,numIncident,[]).^2)) ./ reshape(S0,numIncident,[]);
SDOLP = sqrt((reshape(S1,numIncident,[]).^2 + reshape(S2,numIncident,[]).^2)) ./ reshape(S0,numIncident,[]);
SDOCP = sqrt(reshape(S3,numIncident,[]).^2) ./ reshape(S0,numIncident,[]);

cmap_ST = jet;
for AnglesIP = 1:192                     
    adj_cmap_ST(AnglesIP,:) = cmap_ST(63+AnglesIP,:);  
end 

S0Normcol = [-1 1];
S0col = [-max(S0, [], 'all') max(S0, [], 'all')];
S0SourceNormcol = [-max(S0SourceNorm, [], 'all') max(S0SourceNorm, [], 'all')];
DOPcol = [0 1];

status = fclose('all');
%% SO Norm
f1 = figure(1);
f1.Position = [200 0 500 800];
f1.Resize = 'off';

subplot(4,1,1);
surf(waveValues,unique(IPValues),reshape(S0Norm,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title(append(sampleTitleST, ' S0 Normalized', newline,'S0'));
ylabel('Incident Pol (Degrees)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(4,1,2);
surf(waveValues,unique(IPValues),reshape(S1Norm,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S1');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(4,1,3);
surf(waveValues,unique(IPValues),reshape(S2Norm,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S2');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(4,1,4);
surf(waveValues,unique(IPValues),reshape(S3Norm,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S3');
xlabel('Wavelength (nm)')
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([waveMin waveMax]);
ylim([0 90]);

set(f1, 'Name', sampleTitleST + " StokesS0Norm", 'NumberTitle', 'off');
savefig(f1, fullfile(pwd, saveFolderpathST, sampleTitleST + " StokesS0Norm.fig"));
if Latex == 1
    exportgraphics(f1, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " StokesS0Norm.png"), 'Resolution', 300);
end

%% Stokes Vector
f2 = figure(2);
f2.Position = [200 0 500 800];
f2.Resize = 'off';

subplot(4,1,1);
surf(waveValues,unique(IPValues),reshape(S0,numIncident,[]));
shading interp
colormap jet
title(append(sampleTitleST, ' Stokes Vector', newline,'S0'));
ylabel('Incident Pol (Degrees)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(4,1,2);
surf(waveValues,unique(IPValues),reshape(S1,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S1');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(4,1,3);
surf(waveValues,unique(IPValues),reshape(S2,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S2');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(4,1,4);
surf(waveValues,unique(IPValues),reshape(S3,numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S3');
xlabel('Wavelength(nm)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([waveMin waveMax]);
ylim([0 90]);

set(f2, 'Name', sampleTitleST + " StokesVector", 'NumberTitle', 'off');
savefig(f2, fullfile(pwd, saveFolderpathST, sampleTitleST + " StokesVector.fig"));
if Latex == 1
    exportgraphics(f2, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " StokesVector.png"), 'Resolution', 300);
end

%% Source Norm
if Norm == 1
    f3 = figure(3);
    f3.Position = [200 0 500 800];
    f3.Resize = 'off';

    subplot(4,1,1);
    surf(waveValues,unique(IPValues),reshape(S0SourceNorm,numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title(append(sampleTitleST, ' Source Normalized', newline,'S0'));
    ylabel('Incident Pol (Degrees)');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim([0 S0SourceNormcol(2)])
    xlim([waveMin waveMax]);
    ylim([0 90]);
    
    subplot(4,1,2);
    surf(waveValues,unique(IPValues),reshape(S1SourceNorm,numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title('S1');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(S0SourceNormcol)
    xlim([waveMin waveMax]);
    ylim([0 90]);
    
    subplot(4,1,3);
    surf(waveValues,unique(IPValues),reshape(S2SourceNorm,numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title('S2');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(S0SourceNormcol)
    xlim([waveMin waveMax]);
    ylim([0 90]);

    subplot(4,1,4);
    surf(waveValues,unique(IPValues),reshape(S3SourceNorm,numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title('S3');
    xlabel('Wavelength(nm)');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(S0SourceNormcol)
    xlim([waveMin waveMax]);
    ylim([0 90]);
    
    set(f3, 'Name', sampleTitleST + " StokesVectorSourceNorm", 'NumberTitle', 'off');
    savefig(f3, fullfile(pwd, saveFolderpathST, sampleTitleST + " StokesVectorSourceNorm.fig"));
    if Latex == 1
        exportgraphics(f3, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " StokesVectorSourceNorm.png"), 'Resolution', 300);
    end
end


%% DOP
f4 = figure(4);
f4.Position = [200 0 500 800];
f4.Resize = 'off';

subplot(3,1,1);
surf(waveValues,unique(IPValues),SDOP);
shading interp
colormap(adj_cmap_ST)
title(append(sampleTitleST, ' Degree of Polarization', newline,'DOP'));
ylabel('Incident Pol (Degrees)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(DOPcol)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(3,1,2);
surf(waveValues, unique(IPValues), SDOLP);
shading interp
colormap(adj_cmap_ST)
title(append('DOLP'));
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(DOPcol)
xlim([waveMin waveMax]);
ylim([0 90]);

subplot(3,1,3);
surf(waveValues, unique(IPValues), SDOCP);
shading interp
colormap(adj_cmap_ST)
title(append('DOCP'));
xlabel('Wavelength (nm)')
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(DOPcol)
xlim([waveMin waveMax]);
ylim([0 90]);

set(f4, 'Name', sampleTitleST + " DOP", 'NumberTitle', 'off');
savefig(f4, fullfile(pwd, saveFolderpathST, sampleTitleST + " DOP.fig"));
if Latex == 1
    exportgraphics(f4, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " DOP.png"), 'Resolution', 300);
end

close('all');
