clc;
clear all;
close all;

Norm = 1;   Latex = 0;

sampleName = "RG092c";
sampleReg = 'A';
Side = "y";

waveMin = 550;
waveMax = 951;

startLineST = 145;
endLineST = 806;

numSteps = 41;
stepSize = 0.5;
startPos = 0;
numIncident = 10;
incidentSpacing = 10;
startIncident = 0;

QEPro_inc = 0.7320;
Flame_inc = 6;

saveFolderST = mkdir('Stokes (retake)');
saveFolderpathST = fullfile('Stokes (retake)');

if Latex == 1
    saveFolderLatex = mdkir('Latex');
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

h5dataPath = append('Stokes (retake)/', Side, '/', sampleName, '_Region', sampleReg, '_', Side, '_stokesScan.h5');
IPValues = unique(h5read(h5dataPath, '/IP_Theta'));
IWValues = unique(h5read(h5dataPath, '/IW_Theta'));
CWValues = unique(h5read(h5dataPath, '/CW_Theta'));
CPValues = unique(h5read(h5dataPath, '/CP_Theta'));
waveValues = unique(h5read(h5dataPath, '/wavelength'));
intensityValues = h5read(h5dataPath, '/intensity');
wavelengthValues = h5read(h5dataPath, '/wavelength');

waveMask = waveValues >= waveMin & waveValues <= waveMax;
waveValues = waveValues(waveMask);

for n = 1:length(IPValues)
    ip(n) = IPValues(n);
    for m = 1:length(CWValues)
        cw(m) = CWValues(m);
        for k = 1:length(CPValues)
            cp(k) = CPValues(k);

            g = 4*(n-1)+1+(m-1)+(k-1);

            data(n,m,k).IP_Theta = ip(n);
            data(n,m,k).CW_Theta = cw(m);
            data(n,m,k).CP_Theta = cp(k);
            data(n,m,k).wavelength = wavelengthValues;
            data(n,m,k).intensity = intensityValues(:,g);

        end
    end
end

for IPAngles = 1:length(IPValues)
    for CWAngles = 1:length(CWValues)
        for CPAngles = 1:length(CPValues)

            dataST(IPAngles,CWAngles,CPAngles).IP_Theta = data(IPAngles,CWAngles,CPAngles).IP_Theta;
            dataST(IPAngles,CWAngles,CPAngles).CW_Theta = data(IPAngles,CWAngles,CPAngles).CW_Theta;
            dataST(IPAngles,CWAngles,CPAngles).CP_Theta = data(IPAngles,CWAngles,CPAngles).CP_Theta;
            dataST(IPAngles,CWAngles,CPAngles).wavelength = data(IPAngles,CWAngles,CPAngles).wavelength;
            dataST(IPAngles,CWAngles,CPAngles).intensity = data(IPAngles,CWAngles,CPAngles).intensity;
            
            I(IPAngles,CWAngles,CPAngles,:) = smooth(dataST(IPAngles,CWAngles,CPAngles).intensity(waveMask), 21);
        end
    end
    
    S0(IPAngles,:) = I(IPAngles,2,1,:) + I(IPAngles,1,2,:);
    S1(IPAngles,:) = 2*(I(IPAngles,1,1,:) - 0.5*(I(IPAngles,2,1,:) + I(IPAngles,1,2,:)));
    S2(IPAngles,:) = 2*(I(IPAngles,2,2,:) - 0.5*(I(IPAngles,2,1,:) + I(IPAngles,1,2,:)));
    S3(IPAngles,:) = 2*(I(IPAngles,1,2,:) - 0.5*(I(IPAngles,2,1,:) + I(IPAngles,1,2,:)));
    
    S0Norm(IPAngles,:) = S0(IPAngles,:)./S0(IPAngles,:);
    S1Norm(IPAngles,:) = S1(IPAngles,:)./S0(IPAngles,:);
    S2Norm(IPAngles,:) = S2(IPAngles,:)./S0(IPAngles,:);
    S3Norm(IPAngles,:) = S3(IPAngles,:)./S0(IPAngles,:);

    if Norm == 1
        S0SourceNorm(IPAngles,:) = S0(IPAngles,:)./(Norm_VIS');
        S1SourceNorm(IPAngles,:) = S1(IPAngles,:)./(Norm_VIS');
        S2SourceNorm(IPAngles,:) = S2(IPAngles,:)./(Norm_VIS');
        S3SourceNorm(IPAngles,:) = S3(IPAngles,:)./(Norm_VIS');
    end
end

SDOP(:,:) = sqrt((reshape(S1(:,:),numIncident,[]).^2 + reshape(S2(:,:),numIncident,[]).^2 + reshape(S3(:,:),numIncident,[]).^2)) ./ reshape(S0(:,:),numIncident,[]);
SDOLP(:,:) = sqrt((reshape(S1(:,:),numIncident,[]).^2 + reshape(S2(:,:),numIncident,[]).^2)) ./ reshape(S0(:,:),numIncident,[]);
SDOCP(:,:) = sqrt(reshape(S3(:,:),numIncident,[]).^2) ./ reshape(S0(:,:),numIncident,[]);

cmap_ST = jet;
for AnglesIP = 1:192                     
    adj_cmap_ST(AnglesIP,:) = cmap_ST(63+AnglesIP,:);  
end 

S0Normcol = [-1 1];
S0col = [-0.75*max(S0, [], 'all') 0.75*max(S0, [], 'all')];
S0SourceNormcol = [-0.75*max(S0SourceNorm, [], 'all') 0.75*max(S0SourceNorm, [], 'all')];
DOPcol = [0 1];

status = fclose('all');
%% SO Norm
f1 = figure(1);
f1.Position = [200 -25 400 800];
f1.Resize = 'off';

subplot(4,1,1);
surf(waveValues,IPValues,reshape(S0Norm(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title(append(sampleTitleST, ' S0 Normalized', newline,'S0'));
ylabel('Incident Pol (Degrees)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(4,1,2);
surf(waveValues,IPValues,reshape(S1Norm(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S1');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(4,1,3);
surf(waveValues,IPValues,reshape(S2Norm(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S2');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(4,1,4);
surf(waveValues,IPValues,reshape(S3Norm(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S3');
xlabel('Wavelength (nm)')
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0Normcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

set(f1, 'Name', sampleTitleST + " StokesS0Norm", 'NumberTitle', 'off');
savefig(f1, fullfile(pwd, saveFolderpathST, sampleTitleST + " StokesS0Norm.fig"));
if Latex == 1
    exportgraphics(f1, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " StokesS0Norm.png"), 'Resolution', 300);
end

%% Stokes Vector
f2 = figure(2);
f2.Position = [200 -25 400 800];
f2.Resize = 'off';

subplot(4,1,1);
surf(waveValues,IPValues,reshape(S0(:,:),numIncident,[]));
shading interp
colormap jet
title(append(sampleTitleST, ' Stokes Vector', newline,'S0'));
ylabel('Incident Pol (Degrees)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(4,1,2);
surf(waveValues,IPValues,reshape(S1(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S1');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(4,1,3);
surf(waveValues,IPValues,reshape(S2(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S2');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(4,1,4);
surf(waveValues,IPValues,reshape(S3(:,:),numIncident,[]));
shading interp
colormap(adj_cmap_ST)
title('S3');
xlabel('Wavelength(nm)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(S0col)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

set(f2, 'Name', sampleTitleST + " StokesVector", 'NumberTitle', 'off');
savefig(f2, fullfile(pwd, saveFolderpathST, sampleTitleST + " StokesVector.fig"));
if Latex == 1
    exportgraphics(f2, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " StokesVector.png"), 'Resolution', 300);
end

%% Source Norm
if Norm == 1
    f3 = figure(3);
    f3.Position = [200,-25,400,800];
    f3.Resize = 'off';

    subplot(4,1,1);
    surf(waveValues,IPValues,reshape(S0SourceNorm(:,:),numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title(append(sampleTitleST, ' Source Normalized', newline,'S0'));
    ylabel('Incident Pol (Degrees)');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim([0 S0SourceNormcol(2)])
    xlim([min(min(waveMin)) max(max(waveMax))]);
    ylim([0 90]);
    
    subplot(4,1,2);
    surf(waveValues,IPValues,reshape(S1SourceNorm(:,:),numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title('S1');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(S0SourceNormcol)
    xlim([min(min(waveMin)) max(max(waveMax))]);
    ylim([0 90]);
    
    subplot(4,1,3);
    surf(waveValues,IPValues,reshape(S2SourceNorm(:,:),numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title('S2');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(S0SourceNormcol)
    xlim([min(min(waveMin)) max(max(waveMax))]);
    ylim([0 90]);

    subplot(4,1,4);
    surf(waveValues,IPValues,reshape(S3SourceNorm(:,:),numIncident,[]));
    shading interp
    colormap(adj_cmap_ST)
    title('S3');
    xlabel('Wavelength(nm)');
    view(0,90)
    c = colorbar;
    c.Ruler.Exponent = 0;
    clim(S0SourceNormcol)
    xlim([min(min(waveMin)) max(max(waveMax))]);
    ylim([0 90]);
    
    set(f3, 'Name', sampleTitleST + " StokesVectorSourceNorm", 'NumberTitle', 'off');
    savefig(f3, fullfile(pwd, saveFolderpathST, sampleTitleST + " StokesVectorSourceNorm.fig"));
    if Latex == 1
        exportgraphics(f3, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " StokesVectorSourceNorm.png"), 'Resolution', 300);
    end
end


%% DOP
f4 = figure(4);
f4.Position = [200 -25 400 800];
f4.Resize = 'off';

subplot(3,1,1);
surf(waveValues,IPValues,SDOP(:,:));
shading interp
colormap(adj_cmap_ST)
title(append(sampleTitleST, ' Degree of Polarization', newline,'DOP'));
ylabel('Incident Pol (Degrees)');
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(DOPcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(3,1,2);
surf(waveValues, IPValues, SDOLP(:,:));
shading interp
colormap(adj_cmap_ST)
title(append('DOLP'));
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(DOPcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

subplot(3,1,3);
surf(waveValues, IPValues, SDOCP(:,:));
shading interp
colormap(adj_cmap_ST)
title(append('DOCP'));
xlabel('Wavelength (nm)')
view(0,90)
c = colorbar;
c.Ruler.Exponent = 0;
clim(DOPcol)
xlim([min(min(waveMin)) max(max(waveMax))]);
ylim([0 90]);

set(f4, 'Name', sampleTitleST + " DOP", 'NumberTitle', 'off');
savefig(f4, fullfile(pwd, saveFolderpathST, sampleTitleST + " DOP.fig"));
if Latex == 1
    exportgraphics(f4, fullfile(pwd, saveFolderpathLatex, sampleTitleST + " DOP.png"), 'Resolution', 300);
end