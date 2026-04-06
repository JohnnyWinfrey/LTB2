intensityData = h5read("sample_RegionA_x_LPscan.h5", '/intensity');
wavelengthData = h5read("sample_RegionA_x_LPscan.h5", '/wavelength');
stepSize = 0.5;
inc = unique(h5read("sample_RegionA_x_LPscan.h5", '/IP_Theta'));
numInc = length(inc);
s= size(intensityData);
intensity = zeros(numInc,s(1),s(2)/(2*numInc));
posScale= linspace(0,stepSize*s(2)/(2*numInc),s(2)/(2*numInc)) - 10;
for i = 0:((s(2)/(2*numInc))-1)
    n = 8*i+1;
    for k = 1:numInc
        intensity(k,:,i+1) = intensityData(:,n+k-1) + intensityData(:,n+k);
    end
end
h = [0 0 0; 1 1 1 ; 0 0 0]/3;
for k = 1:numInc

    dataPlot = imfilter(reshape(intensity(k,:,:), s(1), s(2)/(numInc*2)),h);
    f1 = figure(k);
    surf(wavelengthData, posScale, dataPlot')
    view(0,90)
    shading interp
    colormap hot
end
