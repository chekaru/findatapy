__author__ = 'saeedamen' # Saeed Amen

#
# Copyright 2016 Cuemacro
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and limitations under the License.
#the License for the specific language governing permissions and limitations under the License.
#

import datetime
import functools
import math

import numpy
import pandas
import pandas.tseries.offsets

try:
    from pandas.stats.api import ols
except:
    # temporary fix to get compilation, need to rewrite regression code to get this to work
    # later versions of pandas no longer support OLS
    from statsmodels.formula.api import ols

from findatapy.timeseries.filter import Filter
from findatapy.timeseries.filter import Calendar

from pandas import compat

class Calculations(object):
    """Calculations on time series, such as calculating strategy returns and various wrappers on pandas for rolling sums etc.

    """

    ##### calculate

    def calculate_signal_tc(self, signal_data_frame, tc, period_shift = 1):
        """Calculates the transaction costs for a particular signal

        Parameters
        ----------
        signal_data_frame : DataFrame
            contains trading signals
        tc : float
            transaction costs
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        return (signal_data_frame.shift(period_shift) - signal_data_frame).abs().multiply(tc)

    def calculate_entry_tc(self, entry_data_frame, tc, period_shift = 1):
        """Calculates the transaction costs for defined trading points

        Parameters
        ----------
        entry_data_frame : DataFrame
            contains points where we enter/exit trades
        tc : float
            transaction costs
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        return entry_data_frame.abs().multiply(tc)

    def calculate_signal_returns(self, signal_data_frame, returns_data_frame, period_shift = 1):
        """Calculates the trading startegy returns for given signal and asset

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        returns_data_frame: DataFrame
            returns of asset to be traded
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """

        # can cause issues, if the names of the columns are not identical
        return signal_data_frame.shift(period_shift) * returns_data_frame

    def calculate_signal_returns_as_matrix(self, signal_data_frame, returns_data_frame, period_shift = 1):

        return pandas.DataFrame(
            signal_data_frame.shift(period_shift).values * returns_data_frame.values, index=returns_data_frame.index,
            columns=returns_data_frame.columns)


    def calculate_individual_trade_gains(self, signal_data_frame, strategy_returns_data_frame):
        """Calculates profits on every trade (experimental code)

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        strategy_returns_data_frame: DataFrame
            returns of strategy to be tested

        Returns
        -------
        DataFrame contains the P&L for every trade
        """

        # signal need to be aligned to NEXT period for returns
        # signal_data_frame_pushed = signal_data_frame.shift(1)

        # find all the trade points
        trade_points = ((signal_data_frame - signal_data_frame.shift(1)).abs())
        cumulative = self.create_mult_index(strategy_returns_data_frame)

        indices = trade_points > 0
        indices.columns = cumulative.columns

        # get P&L for every trade (from the end point - start point)
        trade_returns = numpy.nan * cumulative
        trade_points_cumulative = cumulative[indices]

        # for each set of signals/returns, calculate the trade returns - where there isn't a trade
        # assign a NaN
        # TODO do in one vectorised step without for loop
        for col_name in trade_points_cumulative:
            col = trade_points_cumulative[col_name]
            col = col.dropna()
            col = col / col.shift(1) - 1

            # TODO experiment with quicker ways of writing below?
            # for val in col.index:
                # trade_returns.set_value(val, col_name, col[val])
                # trade_returns.ix[val, col_name] = col[val]

            date_indices = trade_returns.index.searchsorted(col.index)
            trade_returns.ix[date_indices, col_name] = col

        return trade_returns

    def calculate_cum_rets_trades(self, signal_data_frame, strategy_returns_data_frame):
        """Calculates cumulative returns resetting at each new trade

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        strategy_returns_data_frame: DataFrame
            returns of strategy to be tested
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """

        # signal need to be aligned to NEXT period for returns
        signal_data_frame_pushed = signal_data_frame.shift(1)

        # find all the trade points
        reset_points = ((signal_data_frame_pushed - signal_data_frame_pushed.shift(1)).abs())

        reset_points = reset_points.cumsum()

        # make sure they have the same column names (otherwise issues around pandas calc - assume same ordering for cols)
        old_cols = strategy_returns_data_frame.columnsii
        strategy_returns_data_frame.columns = signal_data_frame_pushed.columns

        for c in reset_points.columns:
            strategy_returns_data_frame[c + 'cumsum'] = reset_points[c]
            strategy_returns_data_frame[c] = strategy_returns_data_frame.groupby([c + 'cumsum'])[c].cumsum()
            strategy_returns_data_frame = strategy_returns_data_frame.drop([c + 'cumsum'], axis=1)

        strategy_returns_data_frame.columns = old_cols

        return strategy_returns_data_frame

    def calculate_trade_no(self, signal_data_frame):

        ####### how many trades have there been (ignore size of the trades)
        trades = abs(signal_data_frame - signal_data_frame.shift(-1))
        trades = trades[trades > 0].count()

        signal_data_frame = pandas.DataFrame(index=trades.index, columns=['Trades'], data=trades)

        return signal_data_frame

    def calculate_trade_duration(self, signal_data_frame):
        """Calculates cumulative trade durations

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        strategy_returns_data_frame: DataFrame
            returns of strategy to be tested
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """

        # TODO
        # # signal need to be aligned to NEXT period for returns
        # signal_data_frame_pushed = signal_data_frame.shift(1)
        #
        # # find all the trade points
        # reset_points = ((signal_data_frame_pushed - signal_data_frame_pushed.shift(1)).abs())
        #
        # reset_points = reset_points.cumsum()
        #
        # time_data_frame = pandas.DataFrame(index = signal_data_frame.index, columns = signal_data_frame.columns,
        #                                    data=numpy.ones([len(signal_data_frame.index), len(signal_data_frame.columns)]))
        #
        # # make sure they have the same column names (otherwise issues around pandas calc - assume same ordering for cols)
        # old_cols = time_data_frame.columns
        # time_data_frame.columns = signal_data_frame_pushed.columns
        #
        # for c in reset_points.columns:
        #     time_data_frame[c + 'cumperiods'] = reset_points[c]
        #     time_data_frame[c] = time_data_frame.groupby([c + 'cumperiods'])[c].cumsum()
        #     time_data_frame = time_data_frame.drop([c + 'cumperiods'], axis=1)
        #
        # time_data_frame.columns = old_cols
        #
        # return time_data_frame

    def calculate_final_trade_duration(self, signal_data_frame):
        """Calculates cumulative trade durations

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        strategy_returns_data_frame: DataFrame
            returns of strategy to be tested
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """

        # signal need to be aligned to NEXT period for returns
        signal_data_frame_pushed = signal_data_frame.shift(1)

        # find all the trade points
        reset_points = ((signal_data_frame_pushed - signal_data_frame_pushed.shift(1)).abs())

        reset_points = reset_points.cumsum()

        time_data_frame = pandas.DataFrame(index=signal_data_frame.index, columns=signal_data_frame.columns,
                                           data=numpy.ones(
                                               [len(signal_data_frame.index), len(signal_data_frame.columns)]))

        # make sure they have the same column names (otherwise issues around pandas calc - assume same ordering for cols)
        old_cols = time_data_frame.columns
        time_data_frame.columns = signal_data_frame_pushed.columns

        for c in reset_points.columns:
            time_data_frame[c + 'cumperiods'] = reset_points[c]
            time_data_frame[c] = time_data_frame.groupby([c + 'cumperiods'])[c].cumsum()
            time_data_frame = time_data_frame.drop([c + 'cumperiods'], axis=1)

        time_data_frame.columns = old_cols

        return time_data_frame

    def calculate_risk_stop_signals(self, signal_data_frame, cum_rets_trades, stop_loss, take_profit):
        """

        Parameters
        ----------
        signal_data_frame : DataFrame
            Contains all the trade signals (typically mix of 0, +1 and +1

        cum_rets_trades : DataFrame
            Cumulative returns of strategy reset at every new trade

        stop_loss : float (or DataFrame)
            Stop loss level eg. -0.02

        take_profit : float (or DataFrame)
            Take profit level eg. +0.03

        Returns
        -------
        DataFrame containing amended signals that take into account stops and take profits

        """
        
        signal_data_frame_pushed = signal_data_frame # signal_data_frame.shift(1)
        reset_points = ((signal_data_frame_pushed - signal_data_frame_pushed.shift(1)).abs())

        ind = (cum_rets_trades > take_profit) | (cum_rets_trades < stop_loss)

        # to allow indexing, need to match column names
        ind.columns = signal_data_frame.columns
        signal_data_frame[ind] = 0

        reset_points[ind] = 1

        signal_data_frame[reset_points == 0] = numpy.nan
        signal_data_frame = signal_data_frame.ffill()
        # signal_data_frame = signal_data_frame.shift(-1)

        return signal_data_frame

    def calculate_risk_stop_dynamic_signals(self, signal_data_frame, asset_data_frame, stop_loss_df, take_profit_df):
        """

        Parameters
        ----------
        signal_data_frame : DataFrame
            Contains all the trade signals (typically mix of 0, +1 and +1

        stop_loss_df : DataFrame
            Continuous stop losses in the asset (in price amounts eg +2, +2.5, +2.6 USD - as opposed to percentages)

        take_profit_df : DataFrame
            Continuous take profits in the asset (in price amounts eg -2, -2.1, -2.5 USD - as opposed to percentages)

        Returns
        -------
        DataFrame containing amended signals that take into account stops and take profits

        """

        signal_data_frame_pushed = signal_data_frame  # signal_data_frame.shift(1)
        reset_points = ((signal_data_frame_pushed - signal_data_frame_pushed.shift(1)).abs())

        # ensure all the inputs are pandas DataFrames (rather than mixture of Series and DataFrames)
        asset_data_frame = pandas.DataFrame(asset_data_frame)
        signal_data_frame = pandas.DataFrame(signal_data_frame)
        stop_loss_df = pandas.DataFrame(stop_loss_df)
        take_profit_df = pandas.DataFrame(take_profit_df)

        non_trades = reset_points == 0

        # need to temporarily change column names to allow indexing (ASSUMES: columns in same order!)
        non_trades.columns = take_profit_df.columns

        # where we don't have a trade fill with NaNs
        take_profit_df[non_trades] = numpy.nan

        non_trades.columns = stop_loss_df.columns
        stop_loss_df[non_trades] = numpy.nan

        asset_df_copy = asset_data_frame.copy(deep=True)

        non_trades.columns = asset_df_copy.columns
        asset_df_copy[non_trades] = numpy.nan

        take_profit_df = take_profit_df.ffill()
        stop_loss_df = stop_loss_df.ffill()
        asset_df_copy = asset_df_copy.ffill()

        # take profit for buys
        ind1 = (asset_data_frame.values > (asset_df_copy.values + take_profit_df.values)) & (signal_data_frame.values > 0)

        # take profit for sells
        ind2 = (asset_data_frame.values < (asset_df_copy.values - take_profit_df.values)) & (signal_data_frame.values < 0)

        # stop loss for buys
        ind3 = (asset_data_frame.values < (asset_df_copy.values + stop_loss_df.values)) & (signal_data_frame.values > 0)

        # stop loss for sells
        ind4 = (asset_data_frame.values > (asset_df_copy.values - stop_loss_df.values)) & (signal_data_frame.values < 0)

        # when has there been a stop loss or take profit? assign those as being flat points
        ind = ind1 | ind2 | ind3 | ind4

        ind = pandas.DataFrame(data= ind, columns = signal_data_frame.columns, index = signal_data_frame.index)

        # for debugging
        # sum_ind = (ind == True).sum(); print(sum_ind)

        signal_data_frame[ind] = 0

        # those places where we have been stopped out/taken profit are additional trade "reset points", which we need to define
        # (already have ordinary buy/sell trades defined)
        reset_points[ind] = 1

        # where we don't have trade make these NaN and then fill down
        signal_data_frame[reset_points == 0] = numpy.nan
        signal_data_frame = signal_data_frame.ffill()

        return signal_data_frame

    # TODO
    def calculate_risk_stop_defined_signals(self, signal_data_frame, stops_data_frame):
        """

        Parameters
        ----------
        signal_data_frame : DataFrame
            Contains all the trade signals (typically mix of 0, +1 and +1

        stops_data_frame : DataFrame
            Contains 1/-1 to indicate where trades would be stopped out

        Returns
        -------
        DataFrame containing amended signals that take into account stops and take profits

        """

        signal_data_frame_pushed = signal_data_frame # signal_data_frame.shift(1)
        reset_points = ((signal_data_frame_pushed - signal_data_frame_pushed.shift(1)).abs())

        stops_data_frame = stops_data_frame.abs()
        ind = stops_data_frame >= 1

        ind.columns = signal_data_frame.columns
        signal_data_frame[ind] = 0

        reset_points[ind] = 1

        signal_data_frame[reset_points == 0] = numpy.nan
        signal_data_frame = signal_data_frame.ffill()

        return signal_data_frame

    def calculate_signal_returns_matrix(self, signal_data_frame, returns_data_frame, period_shift = 1):
        """Calculates the trading strategy returns for given signal and asset
        as a matrix multiplication

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        returns_data_frame: DataFrame
            returns of asset to be traded
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        return pandas.DataFrame(
            signal_data_frame.shift(period_shift).values * returns_data_frame.values, index = returns_data_frame.index)

    def calculate_signal_returns_with_tc(self, signal_data_frame, returns_data_frame, tc, period_shift = 1):
        """Calculates the trading startegy returns for given signal and asset including
        transaction costs

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        returns_data_frame: DataFrame
            returns of asset to be traded
        tc : float
            transaction costs
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        tc_costs = self.calculate_signal_tc(signal_data_frame, tc, period_shift)
        return signal_data_frame.shift(period_shift) * returns_data_frame - tc_costs

    def calculate_signal_returns_with_tc_matrix(self, signal_data_frame, returns_data_frame, tc, period_shift = 1):
        """Calculates the trading startegy returns for given signal and asset with transaction costs with matrix multiplication

        Parameters
        ----------
        signal_data_frame : DataFrame
            trading signals
        returns_data_frame: DataFrame
            returns of asset to be traded
        tc : float
            transaction costs
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        tc_costs = (numpy.abs(signal_data_frame.shift(period_shift).values - signal_data_frame.values) * tc)

        return pandas.DataFrame(
            signal_data_frame.shift(period_shift).values * returns_data_frame.values - tc_costs, index = returns_data_frame.index)

    def calculate_returns(self, data_frame, period_shift = 1):
        """Calculates the simple returns for an asset

        Parameters
        ----------
        data_frame : DataFrame
            asset price
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        return data_frame / data_frame.shift(period_shift) - 1

    def calculate_diff_returns(self, data_frame, period_shift = 1):
        """Calculates the differences for an asset

        Parameters
        ----------
        data_frame : DataFrame
            asset price
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        return data_frame - data_frame.shift(period_shift)

    def calculate_log_returns(self, data_frame, period_shift = 1):
        """Calculates the log returns for an asset

        Parameters
        ----------
        data_frame : DataFrame
            asset price
        period_shift : int
            number of periods to shift signal

        Returns
        -------
        DataFrame
        """
        return math.log(data_frame / data_frame.shift(period_shift))

    def create_mult_index(self, df_rets):
        """ Calculates a multiplicative index for a time series of returns

        Parameters
        ----------
        df_rets : DataFrame
            asset price returns

        Returns
        -------
        DataFrame
        """
        df = 100.0 * (1.0 + df_rets).cumprod()

        # get the first non-nan values for rets and then start index
        # one before that (otherwise will ignore first rets point)
        # first_date_indices = df_rets.apply(lambda series: series.first_valid_index())
        # first_ord_indices = list()
        #
        # for i in first_date_indices:
        #     try:
        #         ind = df.index.searchsorted(i)
        #     except:
        #         ind = 0
        #
        #     if ind > 0: ind = ind - 1
        #
        #     first_ord_indices.append(ind)
        #
        # for i in range(0, len(df.columns)):
        #     df.iloc[first_ord_indices[i],i] = 100

        # probably a quicker way to do this, maybe using group by?
        for c in df.columns:
            df.loc[df[c].first_valid_index(), c] = 100

        return df

    def create_mult_index_from_prices(self, data_frame):
        """Calculates a multiplicative index for a time series of prices

        Parameters
        ----------
        df_rets : DataFrame
            asset price

        Returns
        -------
        DataFrame
        """
        return self.create_mult_index(self.calculate_returns(data_frame))

    def rolling_z_score(self, data_frame, periods):
        """Calculates the rolling z score for a time series

        Parameters
        ----------
        data_frame : DataFrame
            asset prices
        periods : int
            rolling window for z score computation

        Returns
        -------
        DataFrame
        """
        return (data_frame - data_frame.rolling(center=False, window = periods).mean()) / data_frame.rolling(center=False, window = periods).std()

    def rolling_volatility(self, data_frame, periods, obs_in_year = 252):
        """
        rolling_volatility - Calculates the annualised rolling volatility

        Parameters
        ----------
        data_frame : DataFrame
            contains returns time series
        obs_in_year : int
            number of observation in the year

        Returns
        -------
        DataFrame
        """

        # return pandas.rolling_std(data_frame, periods) * math.sqrt(obs_in_year)
        return data_frame.rolling(window=periods,center=False).std() * math.sqrt(obs_in_year)

    def rolling_mean(self, data_frame, periods):
        return self.rolling_average(data_frame, periods)

    def rolling_average(self, data_frame, periods):
        """Calculates the rolling moving average

        Parameters
        ----------
        data_frame : DataFrame
            contains time series
        periods : int
            periods in the average

        Returns
        -------
        DataFrame
        """
        return pandas.rolling_mean(data_frame, periods)

    def rolling_sparse_average(self, data_frame, periods):
        """Calculates the rolling moving average of a sparse time series

        Parameters
        ----------
        data_frame : DataFrame
            contains time series
        periods : int
            number of periods in the rolling sparse average

        Returns
        -------
        DataFrame
        """

        # 1. calculate rolling sum (ignore NaNs)
        # 2. count number of non-NaNs
        # 3. average of non-NaNs
        foo = lambda z: z[pandas.notnull(z)].sum()

        # rolling_sum = pandas.rolling_apply(data_frame, periods, foo, min_periods=1)
        # rolling_non_nans = pandas.stats.moments.rolling_count(data_frame, periods, freq=None, center=False, how=None) \
        rolling_sum = data_frame.rolling(center=False, window=periods, min_periods=1).apply(func=foo)
        rolling_non_nans = data_frame.rolling(window=periods,center=False).count()

        # For pandas 0.18 onwards (TODO)
        # rolling_non_nans = data_frame.rolling(span=periods, freq=None, center=False, how=None).count()

        return rolling_sum / rolling_non_nans

    def rolling_sparse_sum(self, data_frame, periods):
        """Calculates the rolling moving sum of a sparse time series

        Parameters
        ----------
        data_frame : DataFrame
            contains time series
        periods : int
            period for sparse rolling sum

        Returns
        -------
        DataFrame
        """

        # 1. calculate rolling sum (ignore NaNs)
        # 2. count number of non-NaNs
        # 3. average of non-NaNs
        foo = lambda z: z[pandas.notnull(z)].sum()

        rolling_sum = pandas.rolling_apply(data_frame, periods, foo, min_periods=1)

        return rolling_sum

    def rolling_median(self, data_frame, periods):
        """Calculates the rolling moving average

        Parameters
        ----------
        data_frame : DataFrame
            contains time series
        periods : int
            number of periods in the median

        Returns
        -------
        DataFrame
        """
        return pandas.rolling_median(data_frame, periods)

    def rolling_sum(self, data_frame, periods):
        """Calculates the rolling sum

        Parameters
        ----------
        data_frame : DataFrame
            contains time series
        periods : int
            period for rolling sum

        Returns
        -------
        DataFrame
        """
        return pandas.rolling_sum(data_frame, periods)

    def cum_sum(self, data_frame):
        """Calculates the cumulative sum

        Parameters
        ----------
        data_frame : DataFrame
            contains time series

        Returns
        -------
        DataFrame
        """
        return data_frame.cumsum()

    def rolling_ewma(self, data_frame, periods):
        """Calculates exponentially weighted moving average

        Parameters
        ----------
        data_frame : DataFrame
            contains time series
        periods : int
            periods in the EWMA

        Returns
        -------
        DataFrame
        """

        # span = 2 / (1 + periods)

        return pandas.ewma(data_frame, span=periods)

    ##### correlation methods
    def rolling_corr(self, data_frame1, periods, data_frame2 = None, pairwise = False, flatten_labels = True):
        """Calculates rolling correlation wrapping around pandas functions

        Parameters
        ----------
        data_frame1 : DataFrame
            contains time series to run correlations on
        periods : int
            period of rolling correlations
        data_frame2 : DataFrame (optional)
            contains times series to run correlation against
        pairwise : boolean
            should we do pairwise correlations only?

        Returns
        -------
        DataFrame
        """

        # this is the new bit of code here
        if pandas.__version__ < '0.17':
            if pairwise:
                panel = pandas.rolling_corr_pairwise(data_frame1.join(data_frame2), periods)
            else:
                panel = pandas.rolling_corr(data_frame1, data_frame2, periods)
        else:
            # panel = pandas.rolling_corr(data_frame1, data_frame2, periods, pairwise = pairwise)
            panel = data_frame1.rolling(window=periods).corr(other=data_frame2, pairwise=True)

        try:
            df = panel.to_frame(filter_observations=False).transpose()

        except:
            df = panel

        if flatten_labels:
            if pairwise:
                series1 = df.columns.get_level_values(0)
                series2 = df.columns.get_level_values(1)
                new_labels = []

                for i in range(len(series1)):
                    new_labels.append(series1[i] + " v " + series2[i])

            else:
                new_labels = []

                try:
                    series1 = data_frame1.columns
                except:
                    series1 = [data_frame1.name]

                series2 = data_frame2.columns

                for i in range(len(series1)):
                    for j in range(len(series2)):
                        new_labels.append(series1[i] + " v " + series2[j])

            df.columns = new_labels

        return df

    def calculate_column_matrix_signal_override(self, override_df, signal_df):
        length_cols = len(signal_df.columns)
        override_matrix = numpy.repeat(override_df.values.flatten()[numpy.newaxis,:], length_cols, 0)

        # final portfolio signals (including signal & override matrix)
        return pandas.DataFrame(
            data = numpy.multiply(numpy.transpose(override_matrix), signal_df.values),
            index = signal_df.index, columns = signal_df.columns)

    # several types of outer join (TODO finalise which one should appear!)
    def pandas_outer_join(self, df_list):
        if df_list is None: return None

        # remove any None elements (which can't be joined!)
        df_list = [i for i in df_list if i is not None]

        if len(df_list) == 0: return None
        elif len(df_list) == 1: return df_list[0]

        # df_list = [dd.from_pandas(df) for df in df_list]

        return df_list[0].join(df_list[1:], how="outer")

    # several types of outer join (TODO finalise which one should appear!)

    def join_left_fill_right(self, df_left, df_right):

        # say our right series is a signal
        # say our left series is an asset to be traded

        # first do an outer join then fill down our right signal
        df_left_1, df_right = df_left.align(df_right, join='outer', axis=0)
        df_right = df_right.fillna(method='ffill')

        # now realign back to days when we trade
        # df_left.to_csv('left.csv'); df_right.to_csv('right.csv')

        df_left, df_right = df_left.align(df_right, join='left', axis=0)



        return df_left, df_right

    def functional_outer_join(self, df_list):
        def join_dfs(ldf, rdf):
            return ldf.join(rdf, how='outer')

        return functools.reduce(join_dfs, df_list)

    # experimental!
    # splits dataframe list into halves
    def iterative_outer_join_second(self, df_list):
        if df_list is None: return None

        # remove any None elements (which can't be joined!)
        df_list = [i for i in df_list if i is not None]

        if len(df_list) == 0:
            return None

        elif len(df_list) == 1:
            return df_list[0]

        while (True):
            length = len(df_list)

            if length == 1: break

            df_list_out = []

            for i in range(0, length, 2):
                df_list_out.append(self.join_aux(i, df_list))

            df_list = df_list_out

        return df_list[0]

    def iterative_outer_join(self, df_list, pool = None):

        if not(isinstance(df_list, list)):
            return df_list

        if pool is None:
            from multiprocessing.dummy import Pool
            pool = Pool(4)

        if (len(df_list) < 3):
            return self.pandas_outer_join(df_list)

        while(True):
            # split into two
            length = len(df_list)

            if length == 1: break

            job_args = [(item_a, df_list) for i, item_a in enumerate(range(0, length, 2))]
            df_list = pool.map_async(self.join_aux_helper, job_args).get()

        pool.close()
        pool.join()

        return df_list[0]

    def join_aux_helper(self, args):
        return self.join_aux(*args)

    def join_aux(self, i, df_list):
        if i == len(df_list) - 1: return df_list[i]

        return df_list[i].join(df_list[i + 1], how="outer")

    def linear_regression(self, df_y, df_x):
        return pandas.stats.api.ols(y = df_y, x = df_x)

    def linear_regression_single_vars(self, df_y, df_x, y_vars, x_vars, use_stats_models = True):
        """Do a linear regression of a number of y and x variable pairs in different dataframes, report back the coefficients.

        Parameters
        ----------
        df_y : DataFrame
            y variables to regress
        df_x : DataFrame
            x variables to regress
        y_vars : str (list)
            Which y variables should we regress
        x_vars : str (list)
            Which x variables should we regress
        use_stats_models : bool (default: True)
            Should we use statsmodels library directly or pandas.stats.api.ols wrapper (warning: deprecated)

        Returns
        -------
        List of regression statistics

        """

        stats = []

        for i in range(0, len(y_vars)):
            y = df_y[y_vars[i]]
            x = df_x[x_vars[i]]

            try:
                if pandas.__version__ < '0.17' or not(use_stats_models):
                    out = pandas.stats.api.ols(y = y, x = x)
                else:
                    # pandas.stats.api is now being depreciated, recommended replacement package
                    # http://www.statsmodels.org/stable/regression.html

                    # we follow the example from there - Fit and summarize OLS model

                    import statsmodels.api as sm
                    import statsmodels

                    # to remove NaN values (otherwise regression is undefined)
                    (y, x, a, b, c, d) = self._filter_data(y, x)

                    # assumes we have a constant (remove add_constant wrapper to have no intercept reported)
                    mod = sm.OLS(y.get_values(), statsmodels.tools.add_constant(x.get_values()))
                    out = mod.fit()
            except:
                out = None

            stats.append(out)

        return stats

    def strip_linear_regression_output(self, indices, ols_list, var):

        # TODO deal with output from statsmodel as opposed to pandas.stats.ols
        if not(isinstance(var, list)):
            var = [var]

        df = pandas.DataFrame(index = indices, columns=var)

        for v in var:
            list_o = []

            for o in ols_list:
                if o is None:
                    list_o.append(numpy.nan)
                else:
                    if v == 't_stat':
                        list_o.append(o.t_stat.x)
                    elif v == 't_stat_intercept':
                        list_o.append(o.t_stat.intercept)
                    elif v == 'beta':
                        list_o.append(o.beta.x)
                    elif v == 'beta_intercept':
                        list_o.append(o.beta.intercept)
                    elif v == 'r2':
                        list_o.append(o.r2)
                    elif v == 'r2_adj':
                        list_o.append(o.r2_adj)
                    else:
                        return None

            df[v] = list_o

        return df

    ##### various methods for averaging time series by hours, mins and days (or specific columns) to create summary time series
    def average_by_columns_list(self, data_frame, columns):
        return data_frame.\
            groupby(columns).mean()

    def average_by_hour_min_of_day(self, data_frame):
        return data_frame.\
            groupby([data_frame.index.hour, data_frame.index.minute]).mean()

    def average_by_hour_min_of_day_pretty_output(self, data_frame):
        data_frame = data_frame.\
            groupby([data_frame.index.hour, data_frame.index.minute]).mean()

        data_frame.index = data_frame.index.map(lambda t: datetime.time(*t))

        return data_frame

    def all_by_hour_min_of_day_pretty_output(self, data_frame):

        df_new = []

        for group in data_frame.groupby(data_frame.index.date):
            df_temp = group[1]
            df_temp.index = df_temp.index.time
            df_temp.columns = [group[0]]
            df_new.append(df_temp)

        return pandas.concat(df_new, axis=1)

    def average_by_year_hour_min_of_day_pretty_output(self, data_frame):
        # years = range(data_frame.index[0].year, data_frame.index[-1].year)
        #
        # time_of_day = []
        #
        # for year in years:
        #     temp = data_frame.ix[data_frame.index.year == year]
        #     time_of_day.append(temp.groupby(temp.index.time).mean())
        #
        # data_frame = pandas.concat(time_of_day, axis=1, keys = years)
        data_frame = data_frame.\
            groupby([data_frame.index.year, data_frame.index.hour, data_frame.index.minute]).mean()

        data_frame = data_frame.unstack(0)

        data_frame.index = data_frame.index.map(lambda t: datetime.time(*t))

        return data_frame

    def average_by_annualised_year(self, data_frame, obs_in_year = 252):
        data_frame = data_frame.\
            groupby([data_frame.index.year]).mean() * obs_in_year

        return data_frame

    def average_by_month(self, data_frame):
        data_frame = data_frame.\
            groupby([data_frame.index.month]).mean()

        return data_frame

    def average_by_bus_day(self, data_frame, cal = "FX"):
        date_index = data_frame.index

        return data_frame.\
            groupby([Calendar().get_bus_day_of_month(date_index, cal)]).mean()

    def average_by_month_day_hour_min_by_bus_day(self, data_frame, cal = "FX"):
        date_index = data_frame.index

        return data_frame.\
            groupby([date_index.month,
                     Calendar().get_bus_day_of_month(date_index, cal),
                     date_index.hour, date_index.minute]).mean()

    def average_by_month_day_by_bus_day(self, data_frame, cal = "FX"):
        date_index = data_frame.index

        return data_frame.\
            groupby([date_index.month,
                     Calendar().get_bus_day_of_month(date_index, cal)]).mean()

    def average_by_month_day_by_day(self, data_frame, cal = "FX"):
        date_index = data_frame.index

        return data_frame.\
            groupby([date_index.month, date_index.day]).mean()

    def group_by_year(self, data_frame):
        date_index = data_frame.index

        return data_frame.\
            groupby([date_index.year])

    def average_by_day_hour_min_by_bus_day(self, data_frame):
        date_index = data_frame.index

        return data_frame.\
            groupby([Calendar().get_bus_day_of_month(date_index),
                     date_index.hour, date_index.minute]).mean()

    def remove_NaN_rows(self, data_frame):
        return data_frame.dropna()

    def get_top_valued_sorted(self, df, order_column, n = 20):
        df_sorted = df.sort(columns=order_column)
        df_sorted = df_sorted.tail(n=n)

        return df_sorted

    def get_bottom_valued_sorted(self, df, order_column, n = 20):
        df_sorted = df.sort(columns=order_column)
        df_sorted = df_sorted.head(n=n)

        return df_sorted

    def convert_month_day_to_date_time(self, df, year = 1970):
        new_index = []

        # TODO use map?
        for i in range(0, len(df.index)):
            x = df.index[i]
            new_index.append(datetime.date(year, x[0], int(x[1])))

        df.index = pandas.DatetimeIndex(new_index)

        return df

    ###### preparing data for OLS statsmodels ######
    ###### these methods are originally from pandas.stats.ols
    ###### which is being deprecated
    def _filter_data(self, lhs, rhs, weights=None):
        """
        Cleans the input for single OLS.
        Parameters
        ----------
        lhs : Series
            Dependent variable in the regression.
        rhs : dict, whose values are Series, DataFrame, or dict
            Explanatory variables of the regression.
        weights : array-like, optional
            1d array of weights.  If None, equivalent to an unweighted OLS.
        Returns
        -------
        Series, DataFrame
            Cleaned lhs and rhs
        """

        if not isinstance(lhs, pandas.Series):
            if len(lhs) != len(rhs):
                raise AssertionError("length of lhs must equal length of rhs")
            lhs = pandas.Series(lhs, index=rhs.index)

        rhs = self._combine_rhs(rhs)
        lhs = pandas.DataFrame({'__y__': lhs}, dtype=float)
        pre_filt_rhs = rhs.dropna(how='any')

        combined = rhs.join(lhs, how='outer')

        if weights is not None:
            combined['__weights__'] = weights

        valid = (combined.count(1) == len(combined.columns)).values
        index = combined.index
        combined = combined[valid]

        if weights is not None:
            filt_weights = combined.pop('__weights__')
        else:
            filt_weights = None

        filt_lhs = combined.pop('__y__')
        filt_rhs = combined

        if hasattr(filt_weights, 'to_dense'):
            filt_weights = filt_weights.to_dense()

        return (filt_lhs.to_dense(), filt_rhs.to_dense(), filt_weights,
                pre_filt_rhs.to_dense(), index, valid)

    def _safe_update(self, d, other):
        """
        Combine dictionaries with non-overlapping keys
        """
        for k, v in compat.iteritems(other):
            if k in d:
                raise Exception('Duplicate regressor: %s' % k)

            d[k] = v

    def _combine_rhs(self, rhs):
        """
        Glue input X variables together while checking for potential
        duplicates
        """
        series = {}

        if isinstance(rhs, pandas.Series):
            series['x'] = rhs
        elif isinstance(rhs, pandas.DataFrame):
            series = rhs.copy()
        elif isinstance(rhs, dict):
            for name, value in pandas.compat.iteritems(rhs):
                if isinstance(value, pandas.Series):
                    self._safe_update(series, {name: value})
                elif isinstance(value, (dict, pandas.DataFrame)):
                    self._safe_update(series, value)
                else:  # pragma: no cover
                    raise Exception('Invalid RHS data type: %s' % type(value))
        else:  # pragma: no cover
            raise Exception('Invalid RHS type: %s' % type(rhs))

        if not isinstance(series, pandas.DataFrame):
            series = pandas.DataFrame(series, dtype=float)

        return series


if __name__ == '__main__':

    # test functions
    calc = Calculations()
    tsf = Filter()

    # test rolling ewma
    date_range = pandas.bdate_range('2014-01-01', '2014-02-28')

    print(calc.get_bus_day_of_month(date_range))

    foo = pandas.DataFrame(numpy.arange(0.0,13.0))
    print(calc.rolling_ewma(foo, span=3))
