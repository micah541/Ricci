""" A few examples of squared distance matrices. """

from numba import jit
import numpy as np
import numexpr as ne


@jit("void(f8[:,:], f8, f8)", nopython=True, nogil=True)
def symmetric_gen(A, sigma, sep):
    """ Compiled matrix generator. """
    n = len(A) / 2
    # blocks around diagonal (symmetric, 0 diagonal at first)
    for i in range(n):
        for j in range(i + 1, n):
            A[i, j] = A[j, i] = A[i + n, j + n] = A[j + n, i + n] = \
                np.random.normal(1.0, sigma)
    # off diagonal blocks: sep from other cluster
    for i in range(n):
        for j in range(n):
            A[i, j + n] = A[j + n, i] = np.random.normal(sep, sigma)


def onedimensionpair(k, l, sigma):
    """
    Retuern squared distances for two clusters from normal distribution.

    k, l - sizes of clusters,
    sigma>0 - distance between clusters.
    """
    X = np.random.normal(size=(k, 1))
    Y = np.random.normal(size=(l, 1)) + 2 / sigma
    Z = np.concatenate((X, Y))
    # print X
    # print Y
    dist = ne.evaluate("(Z - ZT)**2", global_dict={'ZT': Z.transpose()})
    # for i in range(n):
    #    for j in range(n):
    #         dist[i, j] = (Z[i] - Z[j]) * (Z[i] - Z[j])
    dist = sigma * dist
    return dist


def cyclegraph(n, noise):
    """
    Return squared distances for cuclic graph with n points.

    noise - amount of noise added.
    """
    dist = np.zeros((n, n))
    ndist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist[i, j] = np.amin([(i - j) % n, (j - i) % n])
            ndist[i, j] = dist[i, j] * noise * np.random.randn(1)
    dist = dist * dist
    dist = dist + ndist + ndist.transpose()
    return dist


def closefarsimplices(n, noise, separation):
    """
    Return squared distances for a pair od simplices.

    noise - amount of noise,
    separation - distance between simplices.
    """
    dist = np.zeros((2 * n, 2 * n))
    symmetric_gen(dist, noise, separation)
    return dist


def small_tests():
    """ Generate a few small data sets for testing. """
    yield onedimensionpair(3, 2, 0.1)
    yield cyclegraph(5, 0.1)
    yield closefarsimplices(3, 0.1, 5)
