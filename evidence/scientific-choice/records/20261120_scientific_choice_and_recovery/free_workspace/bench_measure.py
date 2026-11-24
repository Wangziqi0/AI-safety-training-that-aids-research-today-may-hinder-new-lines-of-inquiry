from measurements import measure
from prepare import initial
for name in ('fold','spectrum','harmonics','temporal','window','residual','uncertainty','fap','pixel','apertures','centroid','catalogue'):
    out=measure('P01',name,initial('P01')['rough_periodogram_maxima'][0]['period_days'])
    assert out['values'],name
print('12 primary measurement functions returned numerical archive evidence.')
