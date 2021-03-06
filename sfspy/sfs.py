#! /usr/bin/env python

import numpy as np

from itertools import product, combinations, chain
from scipy.misc import comb

class Sfs(np.ndarray):

	def __new__(subtype, data, dims = None, L = None, repolarize = False):
		obj = np.asarray(data).view(subtype)
		# try coercing to specified size
		if dims is not None:
			obj = obj.reshape(dims)
		# set custom properties
		obj.L = L
		obj.npops = len(obj.shape)
		obj.is_1d = ( len(obj.shape) == 1 )
		obj.pop_sizes = [ n-1 for n in obj.shape ]

		if repolarize:
			obj.repolarize()
		return obj

	def __str__(self):
		return " ".join( str(_) for _ in self.flatten() )

	def match_dims(self, query_dims):
		flag = True
		if len(query_dims) != len(self.shape):
			if len(self.shape) == 1:
				flag = np.prod(query_dims) == np.prod(self.shape)
			else:
				for ii,d in enumerate(self.shape):
					if query_dims[ii] != d:
						flag = False
		return flag

	def set_length(self, L = None):
		obs = np.sum(self)
		if L is None:
			self.L = None
		elif L > obs:
			fixed_anc = tuple(0 for _ in self.shape)
			self[fixed_anc] = L-obs-self[fixed_anc]
			self.L = L

	def assume_length(self):
		self.L = np.sum(self)

	def _get_corner_mask(self):
		fixed_anc = tuple(0 for _ in self.shape)
		fixed_der = tuple(jj-1 for jj in self.shape)
		return fixed_anc, fixed_der

	def mask_corners(self):
		fixed_anc, fixed_der = self._get_corner_mask()
		new_sfs = self.copy()
		new_sfs[fixed_anc] = 0
		new_sfs[fixed_der] = 0
		return new_sfs

	def repolarize(self):
		old_sfs = self.copy()
		dims = [ np.arange(a) for a in self.shape ]
		idx = list(product(*dims))
		for i_old, i_new in zip(idx, reversed(idx)):
			self[ i_new ] = old_sfs[ i_old ]

	def count_segsites(self):
		fixed_anc, fixed_der = self._get_corner_mask()
		return int(np.sum(self) - np.sum(self[fixed_anc]) - np.sum(self[fixed_der]))

	def marginalize(self, dims = [1]):
		sum_over = tuple(d for d in range(0, len(self.shape)) if d not in dims)
		new_sfs = np.sum(self, sum_over)
		new_sfs.L = self.L
		new_sfs.npops = len(new_sfs.shape)
		new_sfs.pop_sizes = [ n-1 for n in new_sfs.shape ]
		return new_sfs

	def d_xy(self, persite = False):
		"""
		Average divergence to the ancestor? I don't think this is the usual d_xy, but will keep here for posterity.
		"""
		if self.npops > 1:
			raise ValueError("Can only calculate diversity stats for 1d SFS for now.")
		dxy = float( np.sum(self * np.arange(self.shape[0]))/self.pop_sizes[0] )
		#dxy = self[ ::-1 ][0]
		denom = self.L if persite and self.L is not None else 1.0
		return dxy/denom

	def theta_pi(self, persite = False, norm = False):
		"""
		Tajima's estimator of theta from pairwise differences
		"""
		if self.npops > 1:
			raise ValueError("Can only calculate diversity stats for 1d SFS for now.")
		n = self.pop_sizes[0]
		S = np.arange(n+1)[::-1] * np.arange(n+1)
		pihat = float(np.sum(self*S/comb(n,2)))
		denom = self.L if persite and self.L is not None else 1.0
		pihat = pihat/denom
		if norm:
			return pihat/self.d_xy(persite = persite)
		else:
			return pihat

	def D_xy(self, persite = False):
		"""
		Average number of pairwise diffs between populations
		"""
		if self.npops != 2:
			raise ValueError("D_xy only makes sense for two populations.")

		nx, ny = self.shape
		#N = np.outer( np.arange(nx), np.arange(ny) )
		N = nx*ny
		S = np.outer( np.arange(nx)[::-1], np.arange(ny) )
		Sp = np.outer( np.arange(nx), np.arange(ny)[::-1] )
		pihat = float(np.sum((self*S + self*Sp)/N))
		denom = self.L if persite and self.L is not None else 1.0
		pihat = pihat/denom
		return pihat

	def theta_w(self, persite = False):
		"""
		Watterson's estimator of theta from segregating sites
		"""
		if self.npops > 1:
			raise ValueError("Can only calculate diversity stats for 1d SFS for now.")
		n = self.pop_sizes[0]
		S = _watterson_sum(n)
		denom = self.L if persite and self.L is not None else 1.0
		return (self.count_segsites()/S)/denom

	def theta_zeta(self, persite = False):
		if self.npops > 1:
			raise ValueError("Can only calculate diversity stats for 1d SFS for now.")
		denom = self.L if persite and self.L is not None else 1.0
		return float(self[1])/denom

	def tajima_D(self):
		"""
		Tajima's D, normalized difference between observed and expected pairwise differences
		"""

		if self.npops > 1:
			raise ValueError("Can only calculate diversity stats for 1d SFS for now.")

		def _tajima_denom(n, S):
			return np.sqrt(_e1(n)*S + _e2(n)*S*(S-1))

		tp = self.theta_pi()
		tw = self.theta_w()
		S = self.count_segsites()
		n = self.pop_sizes[0]

		return (tp-tw)/_tajima_denom(n, S)

	def fuli_F(self):
		return None

	def fuli_D(self):
		"""
		Fu & Li's D, a variant on Tajima's
		"""

		if self.npops > 1:
			raise ValueError("Can only calculate diversity stats for 1d SFS for now.")

		def _nu(n):
			return 1 + float(_a1(n)**2)/(_a2(n)+(_a1(n)**2))*( _C(n)-float(n+1)/(n-1) )
		def _uu(n):
			return _a1(n) - 1 - _nu(n)

		n = self.pop_sizes[0]
		zeta = self.theta_zeta()
		S = self.count_segsites()
		numerator = S-zeta*_a1(n)
		denominator = np.sqrt( S*_uu(n) + (S**2)*_nu(n) )

		return numerator/denominator

	def f_st(self, weighted = True):
		"""
		Weighted and unweighted F_st according to ANGSD
		"""

		if self.npops != 2:
			raise ValueError("F_st only makes sense for >= 2 populations.")

		N1, N2 = [ x-1 for x in self.shape ]

		est0 = self[:]
		est0[0,0] = 0
		est0[N1,N2] = 0
		est0 = est0/np.sum(est0)

		aMat = np.full((N1+1,N2+1), np.nan)
		baMat = np.full((N1+1,N2+1), np.nan)
		for a1 in range(0, N1+1):
			for a2 in range(0, N2+1):
				p1 = a1/N1
				p2 = a2/N2
				q1 = 1 - p1
				q2 = 1 - p2
				alpha1 = 1 - (p1**2 + q1**2)
				alpha2 = 1 - (p2**2 + q2**2)

				al = 1.0/2 * ( (p1-p2)**2 + (q1-q2)**2) - (N1+N2) *  (N1*alpha1 + N2*alpha2) / (4*N1*N2*(N1+N2-1))
				bal = 1.0/2 * ( (p1-p2)**2 + (q1-q2)**2) + (4*N1*N2-N1-N2)*(N1*alpha1 + N2*alpha2) / (4*N1*N2*(N1+N2-1))
				aMat[a1,a2] = al
				baMat[a1,a2] = bal

		## unweighted average of single-locus ratio estimators
		gamma = est0*(aMat/baMat)
		fstU  = np.sum(gamma[ np.isfinite(gamma)  ])
		## weighted average of single-locus ratio estimators
		num = est0*aMat
		denom = est0*baMat
		fstW = np.sum(num[ np.isfinite(num) ])/np.sum(denom[ np.isfinite(denom) ])
		#print(fstW, fstU, self._old_f_st())
		if weighted:
			return fstW
		else:
			return fstU

	def _old_f_st(self):
		"""
		Weir & Cockerham's (1984) F_st estimator
		"""

		if self.npops < 2:
			raise ValueError("F_st only makes sense for >= 2 populations.")

		## quantities determined only by sample size
		n = np.array(self.pop_sizes)
		r = self.npops
		nbar = np.mean(self.pop_sizes)
		nc = (r*nbar - np.sum(n**2)/(r*nbar))/(r-1)

		## everything else we compute once for bin in the SFS
		fst = np.zeros(np.prod(self.shape))
		masked = self.mask_corners()
		dims = [ np.arange(a) for a in self.shape ]
		idx = product(*dims)
		w = np.ones(np.prod(self.shape))
		denom = np.sum(self)
		for ii, cell in enumerate(idx):
			# each tuple of indices is also a tuple of absolute allele counts
			w[ii] = self[cell]/denom
			pi = np.array(cell)/n # convert to frequencies
			pbar = np.mean(pi)
			s2 = np.var(pi)
			# next two lines may apply to haploids only ??
			hi = 1-pi**2
			hbar = np.mean(hi)
			# now the fun part
			a = (nbar/nc)*( s2 - (1/(nbar-1))*(pbar*(1-pbar) - s2*(r-1)/r - hbar/4) )
			b = (nbar/(nbar-1))*(pbar*(1-pbar) - s2*(r-1)/r - hbar*(2*nbar-1)/(4*nbar))
			c = hbar/2
			thetahat = a/(a+b+c)
			fst[ii] = thetahat

		## final value of Fst is that of each bin, times frequency of that bin
		## leave out first and last bin, as they are the zeroed-out corners of the SFS
		if np.sum(w[1:-1]) < 1e-9:
			return np.nan
		else:
			fst_all = np.average(fst[1:-1], weights = w[1:-1])
			return fst_all

	def big_summary(self, persite = False, dxy = False):
		"""
		Make a big vector of 1d and higher-order summary stats, for use with ABC downstream
		"""
		self.assume_length()
		marginals = [ self.marginalize([p]) for p in range(0, self.npops) ]
		stats = [ self.L ]
		for m in marginals:
			stats.extend([ m.theta_pi(persite = persite), m.theta_w(persite = persite), m.theta_zeta(persite = persite) ])
			stats.extend([ m.tajima_D(), m.fuli_D(), m.d_xy(persite = persite) ])
		pairs = list(combinations(range(0, self.npops), 2))
		for p1, p2 in pairs:
			new_sfs = self.marginalize([p1, p2])
			stats.append( new_sfs.f_st() )
		if dxy:
			for p1, p2 in pairs:
				new_sfs = self.marginalize([p1, p2])
				stats.append( new_sfs.D_xy() )

		return np.array(stats, dtype = np.float_)

## utility functions to simplify calculation of diversity stats
def _watterson_sum(n):
	return np.sum(1.0/(1+np.arange(n-1)))

def _e1(n):
	return _c1(n)/_a1(n)

def _e2(n):
	return _c2(n)/(_a1(n)**2+_a2(n))

def _b1(n):
	return float(n+1)/(3*(n-1))

def _b2(n):
	return float((2*(n**2+n+3)))/(9*n*(n-1))

def _a1(n):
	return float(np.sum(1.0/np.arange(n)[1:]))

def _a2(n):
	return float(np.sum(1.0/np.arange(n)[1:]**2))

def _c1(n):
	return _b1(n)-1.0/_a1(n)

def _c2(n):
	return _b2(n)-float(n+2)/(_a1(n)*n)+_a2(n)/_a1(n)**2

def _C(n):
	if (n == 2):
		return 1
	else:
		rez = 2*( float((n*_a1(n))-2*(n-1))/((n-1)*(n-2)) )
		return rez
