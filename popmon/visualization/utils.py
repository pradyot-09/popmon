# Copyright (c) 2022 ING Wholesale Banking Advanced Analytics
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import logging
import math
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from popmon.resources import templates_env

NUM_NS_DAY = 24 * 3600 * int(1e9)

logger = logging.getLogger()


def plot_bars_b64(data, labels=None, bounds=None, ylim=False, skip_empty=True):
    """Plotting histogram data.

    :param numpy.ndarray data: bin values of a histogram
    :param list labels: common bin labels for all histograms. default is None.
    :param bounds: traffic light bounds (y-coordinates). default is None.
    :param bool ylim: place y-axis limits for zooming into the data. default is False.
    :param bool skip_empty: if false, also plot empty plots with only nans or only zeroes. default is True.
    :return: base64 encoded plot image
    :rtype: str
    """
    # basic checks first
    n = data.size  # number of bins
    if labels is not None and len(labels) != n:
        raise ValueError("shape mismatch: x-axis labels do not match the data shape")

    # skip plot generation for empty datasets
    if skip_empty:
        n_data = len(data)
        n_zero = n_data - np.count_nonzero(data)
        n_nan = pd.isnull(data).sum()
        n_inf = np.sum([np.isinf(x) for x in data if isinstance(x, float)])
        if n_nan + n_zero + n_inf == n_data:
            logger.debug("skipping plot with empty data.")
            return ""

    # plot bar
    fig = go.Figure([go.Bar(x=labels, y=data)])

    # set label granularity
    if len(labels) > 0:
        granularity = math.ceil(len(labels) / 50)
        labels = labels[::granularity]

    fig.update_layout(xaxis_tickangle=-90, xaxis={"type": "category"})
    fig.update_xaxes(ticktext=labels)
    fig.update_yaxes(ticks="outside")
    # plot boundaries
    try:
        all_nan = (np.isnan(data)).all()
        max_value = np.nanmax(data) if not all_nan else np.nan
        min_value = np.nanmin(data) if not all_nan else np.nan

        if len(bounds) > 0:
            max_r, max_y, min_y, min_r = bounds
            y_max = max(
                max(max_r) if isinstance(max_r, (list, tuple)) else max_r, max_value
            )
            y_min = min(
                max(min_r) if isinstance(min_r, (list, tuple)) else min_r, min_value
            )
            spread = (y_max - y_min) / 20
            y_max += spread
            y_min -= spread

            if not isinstance(max_r, (list, tuple)):
                fig.add_hline(y=max_r, line_color="red")
                fig.add_hline(y=max_y, line_color="yellow")
                fig.add_hline(y=min_y, line_color="yellow")
                fig.add_hline(y=min_r, line_color="red")
            else:
                fig.add_hline(y=max_r[0], line_color="red")
                fig.add_hline(y=max_y[0], line_color="yellow")
                fig.add_hline(y=min_y[0], line_color="yellow")
                fig.add_hline(y=min_r[0], line_color="red")

            if y_max > y_min:
                fig.update_yaxes(range=[y_min, y_max])

        elif ylim:
            spread = (max_value - min_value) / 20
            y_min = min_value - spread
            y_max = max_value + spread
            if y_max > y_min:
                fig.update_yaxes(range=[y_min, y_max])
    except Exception:
        logger.debug("unable to plot boundaries")

    return fig.to_json()


def render_traffic_lights_table(feature, data, metrics: List[str], labels: List[str]):
    colors = {}
    color_map = ["green", "yellow", "red"]
    for c1, metric in enumerate(metrics):
        colors[metric] = {}
        for c2, label in enumerate(labels):
            colors[metric][label] = [color_map[data[c1][c2]]]

    return templates_env(
        "table.html",
        feature=feature,
        metrics=metrics,
        labels=labels,
        data=colors,
        links=True,
    )


def plot_traffic_lights_overview(feature, data, metrics=None, labels=None):
    return render_traffic_lights_table(feature, data, metrics, labels)


def render_alert_aggregate_table(feature, data, metrics: List[str], labels: List[str]):
    colors = {}
    for c1, metric in enumerate(metrics):
        colors[metric] = {}
        row_max = np.max(data[c1])
        for c2, label in enumerate(labels):
            a = data[c1][c2] / row_max if row_max and row_max != 0 else 0
            if metric.endswith("green"):
                background_rgba = (0, 128, 0, a)
            elif metric.endswith("yellow"):
                background_rgba = (255, 200, 0, a)
            else:
                background_rgba = (255, 0, 0, a)
            background_rgba = (str(v) for v in background_rgba)
            text_color = "white" if a > 0.5 else "black"
            colors[metric][label] = (text_color, background_rgba, data[c1][c2])

    return templates_env(
        "table.html",
        feature=feature,
        metrics=metrics,
        labels=labels,
        data=colors,
        links=False,
    )


def plot_traffic_lights_alerts_b64(feature, data, metrics=None, labels=None):
    assert data.shape[0] == 3

    # Reorder metrics if needed
    pos_green = metrics.index("n_green")
    pos_yellow = metrics.index("n_yellow")
    pos_red = metrics.index("n_red")

    if [pos_green, pos_yellow, pos_red] != [0, 1, 2]:
        data[[0, 1, 2]] = data[[pos_green, pos_yellow, pos_red]]

    metrics = ["# green", "# yellow", "# red"]

    return render_alert_aggregate_table(feature, data.astype(int), metrics, labels)


def plot_traffic_lights_b64(data, labels=None, skip_empty=True):
    """Plotting histogram data.

    :param np.array data: bin values of a histogram
    :param labels: common bin labels for all histograms (optional)
    :param bool skip_empty: if true, skip empty plots with only nans or only zeroes (optional)

    :return: base64 encoded plot image
    :rtype:   string
    """
    # basic checks first
    n = data.size  # number of bins
    if labels is not None and len(labels) != n:
        raise ValueError("shape mismatch: x-axis labels do not match the data shape")

    # skip plot generation for empty datasets
    if skip_empty:
        n_data = len(data)
        n_zero = n_data - np.count_nonzero(data)
        n_nan = pd.isnull(data).sum()
        n_inf = np.sum([np.isinf(x) for x in data if isinstance(x, float)])
        if n_nan + n_zero + n_inf == n_data:
            logger.debug("skipping plot with empty data.")
            return ""

    color = np.array(["yellow"] * n)
    color[data == 0] = "green"
    color[data == 2] = "red"

    ones = np.ones(n)

    fig = go.Figure([go.Bar(x=labels, y=ones, marker={"color": color.tolist()})])

    # set label granularity
    if len(labels) > 0:
        granularity = math.ceil(len(labels) / 50)
        labels = labels[::granularity]

    # hide yaxis
    fig.update_yaxes(visible=False)

    fig.update_layout(xaxis_tickangle=-90)
    fig.update_xaxes(ticktext=labels)
    return fig.to_json()


def plot_overlay_1d_histogram_b64(
    hists,
    x_label,
    hist_names=[],
    y_label=None,
    is_num=True,
    is_ts=False,
    top=20,
    width_in=None,
    xlim=None,
):
    """Create and plot (overlapping) histogram(s) of column values.

    Copyright Eskapade:
    Kindly taken from Eskapade package and then modified. Reference link:
    https://github.com/KaveIO/Eskapade/blob/master/python/eskapade/visualization/vis_utils.py#L397
    License: https://github.com/KaveIO/Eskapade-Core/blob/master/LICENSE
    Modifications copyright ING WBAA.

    :param list hists: list of input numpy histogram = values, bin_edges
    :param str x_label: Label for histogram x-axis
    :param list hist_names: list of histogram names. default is [].
    :param str y_label: Label for histogram y-axis. default is None.
    :param bool is_num: True if observable to plot is numeric. default is True.
    :param bool is_ts: True if observable to plot is a timestamp. default is False.
    :param int top: only print the top 20 characters of x-labels and y-labels. default is 20.
    :param float width_in: the width of the bars of the histogram in percentage (0-1). default is None.
    :param tuple xlim: set the x limits of the current axes. default is None.
    :return: base64 encoded plot image
    :rtype: str
    """
    # basic checks
    if len(hist_names) == 0:
        hist_names = [f"hist{i}" for i in range(len(hists))]
    if hist_names:
        if len(hists) != len(hist_names):
            raise ValueError("length of hist and hist_names are different")

    fig = go.Figure()

    alpha = 1.0 / len(hists)
    for i, hist in enumerate(hists):
        try:
            hist_values = hist[0]
            hist_bins = hist[1]
        except BaseException as e:
            raise ValueError(
                "Cannot extract binning and values from input histogram"
            ) from e

        assert hist_values is not None and len(
            hist_values
        ), "Histogram bin values have not been set."
        assert hist_bins is not None and len(
            hist_bins
        ), "Histogram binning has not been set."

        # basic attribute check: time stamps treated as numeric.
        if is_ts:
            is_num = True

        # plot numeric and time stamps
        if is_num:
            bin_edges = hist_bins
            bin_values = hist_values
            assert (
                len(bin_edges) == len(bin_values) + 1
            ), "bin edges (+ upper edge) and bin values have inconsistent lengths: {:d} vs {:d}. {}".format(
                len(bin_edges), len(bin_values), x_label
            )

            if is_ts:
                # difference in seconds
                be_tsv = [pd.Timestamp(ts).value for ts in bin_edges]
                width = np.diff(be_tsv)
                # pd.Timestamp(ts).value is in ns
                # maplotlib dates have base of 1 day
                width = width / NUM_NS_DAY
            elif width_in:
                width = width_in
            else:
                width = np.diff(bin_edges)

            # plot histogram
            fig.add_trace(
                go.Bar(
                    x=bin_edges[1:],
                    y=bin_values,
                    showlegend=True,
                    opacity=alpha,
                    name=hist_names[i],
                )
            )

            # set x-axis properties
            if xlim:
                fig.update_xaxes(range=xlim)
            else:
                fig.update_xaxes(range=[min(bin_edges), max(bin_edges)])

        # plot categories
        else:
            labels = hist_bins
            values = hist_values
            assert len(labels) == len(
                values
            ), "labels and values have different array lengths: {:d} vs {:d}. {}".format(
                len(labels), len(values), x_label
            )

            # set x-axis properties
            def xtick(lab):
                """Get x-tick."""
                lab = str(lab)
                if len(lab) > top:
                    lab = lab[:17] + "..."
                return lab

            # plot histogram
            fig.add_trace(
                go.Bar(
                    x=[xtick(lab) for lab in labels],
                    y=values,
                    showlegend=True,
                    opacity=alpha,
                    name=hist_names[i],
                )
            )

    # set common histogram properties
    fig.update_layout(barmode="overlay")
    fig.update_yaxes(title=str(y_label) if y_label is not None else "Bin count")
    fig.update_xaxes(title=x_label)
    fig.update_layout(
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 10},
        }
    )

    return fig.to_json()


def plot_heatmap_b64(
    hist_values,
    hist_bins,
    date,
    x_label,
    hist_name,
    y_label=None,
    is_num=False,
    is_ts=False,
    cmap="ylorrd",
    top=20,
    xlim=None,
):
    """Create and plot heatmap of column values.

    Copyright Eskapade:
    Kindly taken from Eskapade package and then modified. Reference link:
    https://github.com/KaveIO/Eskapade/blob/master/python/eskapade/visualization/vis_utils.py#L397
    License: https://github.com/KaveIO/Eskapade-Core/blob/master/LICENSE
    Modifications copyright ING WBAA.

    :param list hist_values: values of heatmap in a 2d numpy array =
    :param list hist_bins: bin labels/edges on y-axis
    :param list date: dates for x/time axis of heatmap
    :param str x_label: Label for heatmap x-axis
    :param list hist_names: list of histogram names. default is [].
    :param str y_label: Label for histogram y-axis. default is None.
    :param bool is_num: True if observable to plot is numeric. default is True.
    :param bool is_ts: True if observable to plot is a timestamp. default is False.
    :param int top: only print the top 20 characters of x-labels and y-labels. default is 20.
    :param float cmap: the colormap for heeatmap. default is ylorrd.
    :param tuple xlim: set the x limits of the current axes. default is None.
    :return: base64 encoded plot image
    :rtype: str
    """
    if hist_name:
        if len(hist_name) == 0:
            raise ValueError("length of heatmap names is zero")

    assert hist_values is not None and len(
        hist_values
    ), "Heatmap bin values have not been set."
    assert hist_bins is not None and len(hist_bins), "Heatmap binning has not been set."

    # basic attribute check: time stamps treated as numeric.
    if is_ts:
        is_num = True

    # plot numeric and time stamps
    if is_num:
        bin_edges = hist_bins
        bin_values = hist_values
        assert (
            len(bin_edges) == len(bin_values) + 1
        ), "bin edges (+ upper edge) and bin values have inconsistent lengths: {:d} vs {:d}. {}".format(
            len(bin_edges), len(bin_values), x_label
        )
        return ""

    # plot categories
    else:
        labels = hist_bins
        values = hist_values
        assert len(labels) == len(
            values
        ), "labels and values have different array lengths: {:d} vs {:d}. {}".format(
            len(labels), len(values), x_label
        )

        # set x-axis properties
        def xtick(lab):
            """Get x-tick."""
            lab = str(lab)
            if len(lab) > top:
                lab = lab[:17] + "..."
            return lab

        # plot histogram
        fig = px.imshow(
            values,
            labels={"x": "Time Bins", "y": x_label},
            x=date,
            y=[xtick(lab) for lab in labels],
            color_continuous_scale=cmap,
            text_auto=".2f",
            title="heatmap",
        )

        fig.update_xaxes(tickvals=date, ticktext=date, tickangle=-90)
        fig.update_yaxes(ticks="outside")

    return {"name": hist_name, "plot": fig.to_json()}


def _prune(values, last_n=0, skip_first_n=0, skip_last_n=0):
    """inline function to select first or last items of input list

    :param values: input list to select from
    :param int last_n: select last 'n' items of values. default is 0.
    :param int skip_first_n: skip first n items of values. default is 0. last_n takes precedence.
    :param int skip_last_n: in plot skip last 'n' periods. last_n takes precedence (optional)
    :return: list of selected values
    """
    if last_n > 0:
        return values[-last_n:]
    if skip_first_n > 0:
        values = values[skip_first_n:]
    if skip_last_n > 0:
        values = values[:-skip_last_n]
    return values
