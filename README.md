# sfspy

Some Python utilities for working with site frequency spectra (SFS). Most features are exposed by the class `Sfs`, which is just a Numpy array decorated with some extra properties and methods. In the expected use case, SFS -- which may be of arbitrary dimension, ie. may be joint spectra over multiple populations -- are "flattened" and saved as text in a single whitespace-separated line each. (This is the behavior of `vcfdo sfs` and `ANGSD`.) Most of the summary statistics of classical population genetics -- Watterson's $\theta$, Tajima's (pairwise) $\theta$, Tajima's *D*, Fu and Li's *F*, *F<sub>st</sub>* -- can be recovered from the SFS. A command-line utility is provided for processing SFS stored on disk.

## File formats
SFS can be read and written as plain-text files. Entries may be integers or floats, and should be separated by whitespace. Joint SFS should be "flattened" to a vector so that the whole spectrum can be represented as one line. The flattening is expected to occur row-wise because this is the default in Numpy. The expected dimensions of the unflattened spectrum can be specified in the header with a line like `##dims=N1,N2,...,Nk` for a spectrum with *k* dimensions. The *N<sub>i</sub>* here are the number of *haploid* chromosomes in the sample plus one, since the SFS for *N* sequences has *N*+1 entries.

For instance, consider the following example, a joint SFS over two populations with sample sizes 3 and 2:
```
##dims=4,3
1 3 5 2 4 6 4 6 8 5 7 9
```

## Example code
The above file corresponds to the following manual construction (in an interactive Python terminal):
```
>>> from sfspy import sfs
>>> x = sfs.Sfs([1,3,5,2,4,6,4,6,8,5,7,9], (4,3))
>>> x.shape
(4, 3)
>>> x.pop_sizes
[3, 2]
>>> x
Sfs([[1, 3, 5],
     [2, 4, 6],
     [4, 6, 8],
     [5, 7, 9]])
>>> x.flatten()
Sfs([1, 3, 5, 2, 4, 6, 4, 6, 8, 5, 7, 9])
>>> x.flatten().reshape((4,3))
Sfs([[1, 3, 5],
     [2, 4, 6],
     [4, 6, 8],
     [5, 7, 9]])
```
Note the distinction between the dimensions of the SFS (`x.shape`) and the sample sizes in each population (`x.pop_sizes`). See also that the SFS can be flattened and unflattened without getting scrambled, provided its dimensions are known.

We can *marginalize* over the SFS if we want univariate statistics. Here we obtain the marginal SFS for the first population (at index 0) and then do some calculations. See that the resulting spectrum has 4 entries, equal to the number of rows (ie. axis 0) in the joint SFS.
```
>>> pop1 = x.marginalize([0])
>>> pop1
Sfs([ 9, 12, 18, 21])
>>> pop1.theta_pi()
20.0
>>> pop1.theta_w()
20.0
```
For this simple case, the Watterson and pairwise estimators for $\theta$ take the same value. Note that these values are *unscaled* by default: `sfspy` assumes that the total number of sites, including those fixed for the ancestral allele (typically the hardest class to count), is not known. If we know the total number of callable sites in the genomic interval in question, we can set it manually and then request scaled versions of our estimators:
```
>>> pop1.set_length(10000)
>>> pop1.theta_pi(persite = True)
0.002
```
It may be the case that the SFS includes an accurate count of the number of sites in the lowest bin (fixed for ancestral allele); `ANGSD`, for instance, produces SFS like this. In that case we can indicate that the denominator of the SFS can be inferred from the SFS.
```
>>> pop1.assume_length()
```

## Command-line utilities
The executable `sfspy` will be installed along with the package. It has a subcommand structure like `samtools` and `bcftools`.

Run `sfspy --help` to see a usage message like this:
```
sfspy <command> [options]

Commands:

	summarize         generate a vector of summary statistics (length, pairwise theta, Watterson's theta, Tajima's D)
	boot              generate bootstrap samples from a set of SFS
	aggregate         combine SFS from multiple regions by just summing the values in each bin
	smooth            smooth and subsample SFS using beta-binomial model (like SoFoS).
	backfill          [TODO] fill in the lowest bin (fixed for ancestral allele) given number of callable sites
	convert           convert between different SFS representations (currently only SoFoS --> ANGSD)
	polydfe           make input file for polyDFE from pair of 'neutral' and 'selected' SFS

Notes:
* Spectra are assumed to be UNFOLDED, ie. lowest and highest bin are counts of ancestral and derived allele, respectively.
* When weights (ie. callable sites) are provided, they are assumed to correspond 1:1 to the file of input spectra.
```

The workhorse is `sfspy summarize`, which produces a vector of summary statistics for each SFS in an input file containing possibly many spectra.  Use it like this:
```
sfspy summarize -i input.sfs
```
If the input file has a header line `##dims=...`, it will be used to set the dimensions of the SFS. To override this header, or if it is not present, pass the `-n/--sample-sizes` flag. Otherwise SFS will be assumed one-dimensional.

**TODO:** document output of `summarize`.
