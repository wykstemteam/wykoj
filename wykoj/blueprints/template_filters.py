from datetime import datetime, timedelta
from typing import Union

from quart import Blueprint

from wykoj.constants import VERDICT_TRANS

template_filters = Blueprint("template_filters", __name__)


@template_filters.app_template_filter("threedp")
def corr_to_at_most_3dp(f: Union[str, int, float]) -> str:
    return f if isinstance(f, str) else format(f, ".3f").rstrip("0").rstrip(".")


@template_filters.app_template_filter("f3dp")
def corr_to_3dp(f: Union[int, float]) -> str:  # Forced 3dp precision
    return format(f, ".3f")


@template_filters.app_template_filter("duration")
def duration(minutes: int) -> str:
    if minutes // 1440:
        if minutes % 1440 // 60:
            return f"{minutes // 1440} d {minutes % 1440 // 60} h"
        return f"{minutes // 1440} d"
    if minutes // 60:
        if minutes % 60:
            return "{} h {} m".format(*divmod(minutes, 60))
        return f"{minutes // 60} h"
    return f"{minutes} m"


@template_filters.app_template_filter("datetime")
def display_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@template_filters.app_template_filter("timedelta")
def simplify_timedelta(td: timedelta) -> str:
    return f"{int(td.total_seconds()) // 3600}:{td.seconds % 3600 // 60:02d}"


@template_filters.app_template_filter("submission_verdict")  # TODO: Change name to verdict
def get_submission_verdict(k: int) -> str:
    return VERDICT_TRANS[k]
