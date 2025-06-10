__version__ = '0.1.0'

from easybuild.tools.entrypoints import register_entrypoint_hooks
from easybuild.tools.hooks import CONFIGURE_STEP, START


@register_entrypoint_hooks(START)
def hello_world():
    for i in range(5):
        print("Hello, World! ----------------------------------------")

@register_entrypoint_hooks(CONFIGURE_STEP, pre_step=True)
def test_pre_configure(*args, **kwargs):
    print("test_pre_configure called with args:", args, "and kwargs:", kwargs)

@register_entrypoint_hooks(CONFIGURE_STEP, post_step=True)
def test_post_configure(*args, **kwargs):
    print("test_post_configure called with args:", args, "and kwargs:", kwargs)

