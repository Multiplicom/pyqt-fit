from __future__ import print_function
import sys
import argparse
import json
import numpy
import six
from collections import defaultdict

import pyqt_fit.nonparam_regression as smooth
from pyqt_fit import npr_methods


class CachedFunction(object):
    """
    Class used to cache single-parameter functions: keeps track of previous parameter values and only calculates the
     function if the function was not called yet with given input.
    """
    def __init__(self, fnc):
        self.fnc = fnc
        self.values_map = {}

    def eval(self, x):
        if x in self.values_map:
            return self.values_map[x]
        else:
            y = self.fnc(x)
            self.values_map[x] = y
            return y


def fit_data(input_json, add_plot_data=False, verbose=False, stderr=False):
    """
    Fit the data contained in the JSON file.
    """
    print_kwargs = {}
    if verbose and stderr:
        print_kwargs['file'] = sys.stderr

    with open(input_json, 'r') as fh:
        data = json.load(fh)

    smooth_fraction = data.get('smooth_fraction')
    polynomial_degree = data.get('polynomial_degree')

    output_json = defaultdict(lambda: defaultdict(dict))
    for sample_id, plex_data in six.iteritems(data.get('samples', {})):
        if verbose:
            print("Processing sample {}".format(sample_id), **print_kwargs)

        for plex_number, data in six.iteritems(plex_data):
            if verbose:
                print("\tProcessing plex {}".format(plex_number), **print_kwargs)

            fullset_amplicon_prop = data.get('fullset_amplicon_prop')
            testset_amplicon_prop_min = min(data.get('testset_amplicon_prop'))
            testset_amplicon_prop_max = max(data.get('testset_amplicon_prop'))
            if verbose:
                print("\t\tloading full amplicon property set: {}".format(fullset_amplicon_prop), **print_kwargs)

            try:
                regress = smooth.NonParamRegression(
                    data.get('testset_amplicon_prop'),
                    data.get('testset_amplicon_cov'),
                    bandwidth=(testset_amplicon_prop_max - testset_amplicon_prop_min) * smooth_fraction,
                    method=npr_methods.LocalPolynomialKernel(q=polynomial_degree)
                )
                regress.fit()
                regress_cached = CachedFunction(regress)

                # average predicted value
                mean_predicted = float(numpy.mean([regress_cached.eval(prop_val) for prop_val in fullset_amplicon_prop]))
                if verbose:
                    print("\t\tNonParamRegression mean predicted value: {}".format(mean_predicted), **print_kwargs)

                output_json[sample_id][plex_number] = {'mean_predicted': mean_predicted,
                                                       'singularmatrix': False,
                                                       'values': [],
                                                       'plot': {'x': [], 'y': []}}
                if mean_predicted > 0:
                    for amplicon_prop in fullset_amplicon_prop:
                        regress_value = float(regress_cached.eval(amplicon_prop))
                        output_json[sample_id][plex_number]['values'].append(regress_value)
                    if verbose:
                        print("\t\tNonParamRegression individual values: {}"
                              .format(output_json[sample_id][plex_number]['values']), **print_kwargs)

                if add_plot_data:
                    testset_amplicon_prop_range = numpy.linspace(testset_amplicon_prop_min, testset_amplicon_prop_max, 200)
                    output_json[sample_id][plex_number]['plot']['x'] = testset_amplicon_prop_range
                    for testset_amplicon_prop in testset_amplicon_prop_range:
                        output_json[sample_id][plex_number]['plot']['y'].append(float(regress_cached.eval(testset_amplicon_prop)))

            except numpy.linalg.linalg.LinAlgError as err:
                if 'singular matrix' in err.message.lower():
                    output_json[sample_id][plex_number] = {'mean_predicted': 0, 'singularmatrix': True}
                else:
                    raise
    return output_json


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Non-parametric regression for amplicon coverages')

    parser.add_argument("-i", "--input", required=True,
                        help="The input JSON file containing the x and y data values")
    parser.add_argument("-o", "--output", required=True,
                        help="The output JSON file containing the fitted data values")
    parser.add_argument("--plotdata", action="store_true", default=False,
                        help="Add plot data")
    parser.add_argument("-v", '--verbose', action="store_true",
                        help="Verbose logging", default=False)
    parser.add_argument("--stderr", action="store_true", default=False,
                        help="Send verbose logging to STDERR instead to STDOUT.")
    args = parser.parse_args()
    output_json = fit_data(args.input, add_plot_data=args.plotdata, verbose=args.verbose, stderr=args.stderr)
    with open(args.output, 'w') as fh:
        json.dump(output_json, fh)

