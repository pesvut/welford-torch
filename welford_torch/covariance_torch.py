# Source: https://carstenschelp.github.io/2019/05/12/Online_Covariance_Algorithm_002.html

import torch

class OnlineCovariance:
    """
    A class to calculate the mean and the covariance matrix
    of the incrementally added, n-dimensional data.
    """
    def __init__(self, elements=None, dtype=torch.float32, device=None):
        """
        Parameters
        ----------
        elements (array(S, D)): data samples.
        dtype (torch.dtype): data type to use for calculations.
            default: torch.float32.
        device: str, device to use for calculations. Default is None.
        """

        self.__dtype = dtype
        self.__detached = False


        if elements is None:
            self.__device = device
            self.__order = None
            self.__shape = None
            self.__count = 0
            self.__mean = None
            self.__cov = None
            self.__identity = None

        else:
            self.init_zeros(elements[0], device)

            for elem in elements:
                self.add(elem)

    def init_zeros(self, element, device=None):
        self.__device = element.device if (device is None) else device
        self.__order = element.shape
        self.__shape = torch.Size((*self.__order, self.__order[-1]))
        self.__count = 0
        self.__mean = torch.zeros(self.__order, dtype=self.__dtype, device=self.__device)
        self.__cov = torch.zeros((self.__shape), dtype=self.__dtype, device=self.__device)
        self.__identity = \
            torch.eye(
                self.__shape[-1], dtype=self.__dtype, device=self.__device
            ).repeat((*self.__shape[:-2], 1, 1))

    @property
    def count(self):
        """
        int, The number of observations that has been added
        to this instance of OnlineCovariance.
        """
        return self.__count

    @property
    def mean(self):
        """
        double, The mean of the added data.
        """
        return self.__mean

    @property
    def cov(self):
        """
        tensor, The covariance matrix of the added data.
        """
        return self.__cov

    @property
    def corrcoef(self):
        """
        tensor, The normalized covariance matrix of the added data.
        Consists of the Pearson Correlation Coefficients of the data's features.
        """
        if self.__count < 1:
            return None
        variances = torch.diagonal(self.__cov, dim1=-2, dim2=-1)
        denominator = torch.sqrt(variances[..., None, :] * variances[..., :, None])
        return self.__cov / denominator

    def add(self, observation):
        """
        Add the given observation to this object.

        Parameters
        ----------
        observation: tensor, The observation to add.
        """
        if self.__shape is None:
            self.init_zeros(observation, device=self.__device)

        assert observation.shape == self.__order

        self.__count += 1
        delta_at_nMin1 = observation - self.__mean
        self.__mean += delta_at_nMin1 / self.__count
        weighted_delta_at_n = (observation - self.__mean) / self.__count

        D_at_n = weighted_delta_at_n.expand(self.__shape).transpose(-2, -1)
        D = (delta_at_nMin1 * self.__identity).matmul(D_at_n.transpose(-2, -1))
        self.__cov = self.__cov * (self.__count - 1) / self.__count + D

    def merge(self, other):
        """
        Merges the current object and the given other object into the current object.

        Parameters
        ----------
        other: OnlineCovariance, The other OnlineCovariance to merge this object with.

        Returns
        -------
        self
        """
        if other.__order != self.__order:
            raise ValueError(
                   f'''
                   Cannot merge two OnlineCovariances with different orders.
                   ({self.__order} != {other.__order})
                   ''')

        assert other.__shape == self.__shape
        assert other.__dtype == self.__dtype

        # Compute the merged covariance matrix.
        __merged_count = self.count + other.count

        count_corr = (other.count * self.count) / __merged_count
        __merged_mean = (self.mean/other.count + other.mean/self.count) * count_corr

        flat_mean_diff = self.__mean - other.__mean
        repeat_shape = ( *( [1]*len(self.__shape[:-1]) ), self.__shape[-1] )
        mean_diffs = flat_mean_diff.unsqueeze(-1).repeat(repeat_shape)
        __merged_cov = (self.__cov * self.count \
                           + other.__cov * other.count \
                           + mean_diffs * mean_diffs.transpose(-2, -1) * count_corr) \
                          / __merged_count

        # Update the current object.
        self.__count = __merged_count
        self.__mean = __merged_mean
        self.__cov = __merged_cov

        return self
