from . import controllers
from . import models


def _post_init_hook(env):
    # A column default is computed once for all existing rows, so give each
    # point of sale its own secret link here.
    for config in env["pos.config"].search([]):
        config._reset_order_status_token()
