""" Other helpful functions. """

import timeit
import numpy as np
import numexpr as ne
from numba import jit
import threading


def test_speed(f, *args):
    """ Test the speed of a function. """
    t = timeit.repeat(lambda: f(*args), repeat=5, number=1)
    print 'Fastest out of 5: {} s'.format(min(t))


def metricize(dist):
    """
    Metricize a matrix of "squared distances".

    Modifies the array in-place.

    Only minimizes over two-stop paths not all.
    """
    ne.evaluate("sqrt(dist)", out=dist)
    error = 1
    new = np.zeros_like(dist)
    while error > 1E-12:
        error = 0.0
        for i in xrange(len(dist)):
            new[i, :] = np.amin(dist[i, :, None] + dist, axis=0)
            np.minimum(dist[i, :], new[i, :], out=new[i, :])
            error += np.sum(dist[i, :] - new[i, :])
        dist[:, :] = new
    ne.evaluate('dist**2', out=dist)


def parallel(num, numthreads=8):
    """
    Decorator to execute a function with the first few split into chunks.

    All arguments should be numpy arrays.

    The chunks should be independent computationally.

    Can be used as a replacement for OpenMP parallel for applied to outer loop.

    Arguments:
        num        - number of function arguments to split
        numthreads - number of threads

    One of the arguments should be the output array. This one should be split
    together with at least one of the input arguments.

    Example:
        (n,k), (k,l) -> (n, l) : Put output as first argument, and choose to
                    split 2 arguments. Then the problem will be split into
                    numthreads subproblems with n replaced by n/numthreads.

    Notes:
        Function relies on array_split returning views so that each chunk
        is placed in the appropriate part of the output array automatically.

        Chunks will run parallel only if GIL is released by the function.
        E.g. use nopython and nogil mode in numba jit.
    """
    def chunks_decorator(fun):
        def func_wrapper(*args):
            # FIXME switch to Queue/workers setup for smaller chunks ?
            chunks = [np.array_split(arg, numthreads) for arg in args[:num]]
            chunks = map(list, zip(*chunks))
            for chunk in chunks:
                chunk.extend(args[num:])
            threads = [threading.Thread(target=fun, args=chunk)
                       for chunk in chunks]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        return func_wrapper
    return chunks_decorator


@parallel(2, numthreads=4)
@jit("void(f8[:,:], f8[:,:], f8[:,:])", nopython=True, nogil=True)
def _inner_loops(dist, new, distunsplit):
    for i in xrange(len(dist)):
        for j in xrange(len(distunsplit)):
            d_ij = dist[i, j]
            for k in xrange(len(distunsplit)):
                dijk = dist[i, k] + distunsplit[k, j]
                if dijk < d_ij:
                    d_ij = dijk
            new[i, j] = d_ij


def metricize2(dist):
    """
    Metricize a matrix of "squared distances".

    Only minimizes over two-stop paths not all.
    """
    ne.evaluate("sqrt(dist)", out=dist)
    error = 1
    new = np.zeros_like(dist)
    while error > 1E-12:
        _inner_loops(dist, new, dist)
        error = ne.evaluate("sum(dist-new)")
        dist[:, :] = new
    ne.evaluate('dist**2', out=dist)


def is_metric(sqdist, eps=1E-10):
    """ Check if the matrix is a true squared distance matrix. """
    dist = ne.evaluate("sqrt(dist)")
    for i in xrange(len(dist)):
        temp = ne.evaluate("diT + dist - di < -eps",
                           global_dict={'diT': dist[i, :, None],
                                        'di': dist[i, :]})
        if np.any(temp):
            return False
    return True