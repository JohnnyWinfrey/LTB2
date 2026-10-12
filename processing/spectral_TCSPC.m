%Reads a TCSPC_Spectral HDF5 scan, fits a Gaussian to the emission
%spectrum at fixed times through the decay, and plots the fits.

clc;
clear;
close all;

h5dataPath  = 'sample_RegionA_tcspcSpectral.h5';
sampleTitle = '';      %leave empty to use the sample name stored in the file

cutoffNs    = 50;      %data ends here (one laser period), from histogram time 0
timeStep    = 5;       %spacing of the fitted time slices (ns)
halfWindow  = 0.5;     %counts averaged over +/- this many ns before fitting

%------------------------------------------------------------------------
%read the file

%counts is stored wavelengths x bins, so h5read returns bins x wavelengths:
%one column per wavelength, the same layout as the old TH260 text export
wavelengths = h5read(h5dataPath, '/wavelength')';
CountMatrix = double(h5read(h5dataPath, '/counts'));
binwidth    = double(h5readatt(h5dataPath, '/', 'resolution_ps')) / 1000;  %ns per bin

if isempty(sampleTitle)
    sampleTitle = char(h5readatt(h5dataPath, '/', 'name'));
end

numWavelengths = numel(wavelengths);

%------------------------------------------------------------------------
%trim to the histogram and smooth

%auto-detect where the histogram starts: the brightest bin summed over all
%wavelengths, lightly smoothed first so a single noisy bin cannot win
[~, startline] = max(movmean(sum(CountMatrix,2), 5));
%last bin before the cut-off, from the bin width: 50 ns is bin 250 at 200 ps
lastline = min(floor(cutoffNs / binwidth), size(CountMatrix,1));

filt = [0 1 0; 0 1 0; 0 1 0]/3;
usefulData = imfilter(CountMatrix(startline:lastline,:), filt);

TimeScale = (0:size(usefulData,1)-1) * binwidth;

%------------------------------------------------------------------------
%Gaussian fit at each time slice

timePoints = 0:timeStep:floor(max(TimeScale));
lamFine    = linspace(min(wavelengths)-10, max(wavelengths)+10, 200);

fitSurface = zeros(numel(timePoints), numel(lamFine));
sliceData  = zeros(numel(timePoints), numWavelengths);
fitPeaks   = zeros(numel(timePoints), 2);   %[center_nm amplitude]

x = wavelengths(:);

for k = 1:numel(timePoints)
    %average the bins inside the window to damp shot noise before fitting
    inWindow = abs(TimeScale - timePoints(k)) <= halfWindow;
    y = mean(usefulData(inWindow,:), 1)';

    [~, iPeak] = max(y);
    gaussFit = fit(x, y, 'gauss1', 'StartPoint', [y(iPeak), x(iPeak), 20]);

    fitSurface(k,:) = feval(gaussFit, lamFine)';
    sliceData(k,:)  = y';
    fitPeaks(k,:)   = [gaussFit.b1, gaussFit.a1];
end

%------------------------------------------------------------------------
%plot

fig = figure(1);
fig.Position = [100 100 800 500];
hold on
for k = 1:numel(timePoints)
    plot3(timePoints(k)*ones(size(lamFine)), lamFine, fitSurface(k,:), ...
          'LineWidth', 1.5);
    plot3(timePoints(k)*ones(size(x)), x, sliceData(k,:), ...
          'k.', 'MarkerSize', 10);
end

%mark the peak of the first and last fitted Gaussian with a vertical line
for k = [1 numel(timePoints)]
    plot3([timePoints(k) timePoints(k)], fitPeaks(k,1)*[1 1], ...
          [0 fitPeaks(k,2)], 'r-', 'LineWidth', 2);
end
hold off

%default to looking straight down the time axis: counts vs wavelength
view(90,0)
grid minor;
grid on;
title(append(sampleTitle, ' - Gaussian fits every ', num2str(timeStep), ' ns'));
xlabel('Time (ns)');
ylabel('Wavelength(nm)');
zlabel('Counts');
