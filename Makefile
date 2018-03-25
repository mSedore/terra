all:
	cd terra/FFA/ && /Users/merrinpeterson/anaconda2/bin/python setup.py build_ext --inplace
	cd terra/transit/ && f2py -c occultsmall.f -m occultsmall

