from typing import Callable, Iterable

from .benchmark import Series
from .charts import (
    PANEL_FIGURE_SIZE,
    Axes,
    draw_error_series,
    plt,
    save_figure,
)


def render_operation_panels(
    operations: list[str],
    names: list[str],
    collect: Callable[[str, str], Series],
    *,
    title: str,
    x_label: str,
    y_label: str,
    color_for: Callable[[str], str],
    configure_axis: Callable[[Axes], None],
    output_path: str,
    label_for: Callable[[str], str] | None = None,
    legend_kwargs: dict | None = None,
    on_panel: Callable[[Axes, str, list[tuple[str, Series]]], None] | None = None,
) -> None:

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, operation in zip(axes, operations):

        drawn: list[tuple[str, Series]] = []

        for name in names:
            series = collect(operation, name)
            label = label_for(name) if label_for is not None else name
            draw_error_series(axis, series, label, color_for(name))
            drawn.append((name, series))

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)

        axis.set_ylim(bottom=0)

        configure_axis(axis)
        axis.legend(
            **(legend_kwargs if legend_kwargs is not None else {"fontsize": 10})
        )

        if on_panel is not None:
            on_panel(axis, operation, drawn)

    figure.tight_layout()
    save_figure(figure, output_path)


def series_maximum(series_list: Iterable[Series]) -> float:

    return max(
        (
            mean_value + ci_half
            for series in series_list
            for mean_value, ci_half in zip(series.means, series.ci_halfs)
        ),
        default=0.0,
    )
