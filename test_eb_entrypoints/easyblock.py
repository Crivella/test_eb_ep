from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.entrypoints import EntrypointEasyblock


@EntrypointEasyblock()
class TestEasyBlock(EasyBlock):
    """A test easyblock that does nothing but print a message."""

    def configure_step(self):
        """Override the configure step to print a message."""
        # super().configure_step()
        print("TestEasyBlock: configure_step called.")

    def build_step(self):
        """Override the build step to print a message."""
        # super().build_step()
        print("TestEasyBlock: build_step called.")

    def install_step(self):
        """Override the install step to print a message."""
        # super().install_step()
        print("TestEasyBlock: install_step called.")

    def sanity_check_step(self):
        """Override the sanity check step to print a message."""
        # super().sanity_check_step()
        print("TestEasyBlock: sanity_check_step called.")
