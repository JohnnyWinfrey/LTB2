sampleName = "RG103a'";
region     = "Center";
side       = "Y";

intensityData = h5read("RG103a'_RegionCenter_Y_CPscan.h5", '/intensity');
wavelengthData = h5read("RG103a'_RegionCenter_Y_CPscan.h5", '/wavelength');
stepSize = 0.5;

% Data layout: 8 spectra per position, ordered as
%   IP=-45/CP=-45, IP=-45/CP=0, IP=-45/CP=45, IP=-45/CP=90,
%   IP=+45/CP=-45, IP=+45/CP=0, IP=+45/CP=45, IP=+45/CP=90
s = size(intensityData);              % s(1) = wavelengths, s(2) = total spectra
numPos = s(2) / 8;                    % number of spatial positions
posScale = linspace(0, stepSize * (numPos - 1), numPos);

polLabels = ["LH", "RH"];
intensity = zeros(2, s(1), numPos);
for i = 0:(numPos - 1)
    % IP=-45: sum CP=0 (col 2) and CP=90 (col 4)
    intensity(1, :, i+1) = intensityData(:, 8*i + 2) + intensityData(:, 8*i + 4);
    % IP=+45: sum CP=0 (col 6) and CP=90 (col 8)
    intensity(2, :, i+1) = intensityData(:, 8*i + 6) + intensityData(:, 8*i + 8);
end

h = [0 0 0; 1 1 1; 0 0 0] / 3;
headerLine = sprintf('%s Region %s +%s Side CIRC VIS Profile', sampleName, region, side);
for k = 1:2
    dataPlot = imfilter(reshape(intensity(k, :, :), s(1), numPos), h);
    figure(k);
    surf(wavelengthData, posScale, dataPlot')
    view(0, 90)
    shading interp
    colormap jet
    colorbar
    xlabel('Wavelength (nm)')
    ylabel('Position (mm)')
    title({headerLine, sprintf('%s ° polarization (Raw)', polLabels(k))})
end
