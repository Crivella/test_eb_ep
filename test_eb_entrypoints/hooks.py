from easybuild.tools.entrypoints import EntrypointHook
from easybuild.tools.hooks import CONFIGURE_STEP, START


@EntrypointHook(START)
def hello_world():
    for i in range(5):
        print("Hello, World! ----------------------------------------")

@EntrypointHook(CONFIGURE_STEP, pre_step=True)
def test_pre_configure(*args, **kwargs):
    print("test_pre_configure called with args:", args, "and kwargs:", kwargs)

@EntrypointHook(CONFIGURE_STEP, post_step=True)
def test_post_configure(*args, **kwargs):
    print("test_post_configure called with args:", args, "and kwargs:", kwargs)

