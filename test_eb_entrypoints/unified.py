
import re

import easybuild.tools.systemtools as systemtools
from easybuild.toolchains.fft.fftw import Fftw
from easybuild.toolchains.gcccore import GCCcore
from easybuild.toolchains.linalg.flexiblas import FlexiBLAS
from easybuild.toolchains.linalg.openblas import OpenBLAS
from easybuild.toolchains.linalg.scalapack import ScaLAPACK
from easybuild.toolchains.mpi.openmpi import OpenMPI
from easybuild.tools import LooseVersion
from easybuild.tools.entrypoints import register_toolchain_entrypoint
from easybuild.tools.toolchain.compiler import DEFAULT_OPT_LEVEL, Compiler
from easybuild.tools.toolchain.toolchain import SYSTEM_TOOLCHAIN_NAME

TC_CONSTANT_LLVM = "LLVM"


class LLVM(Compiler):
    """Compiler toolchain with Clang and GFortran compilers."""
    # NAME = 'LLVMcore'
    # COMPILER_MODULE_NAME = [NAME]
    COMPILER_FAMILY = TC_CONSTANT_LLVM
    SUBTOOLCHAIN = SYSTEM_TOOLCHAIN_NAME

    # List of flags that are supported by Clang but not yet by Flang and should be filtered out
    # The element of the list are tuples with the following structure:
    # (min_version, max_version, [list of flags])
    # Where min_version and max_version are strings representing a left-inclusive and right-exclusive version range,
    # [min_version, max_version) respectively.
    # This is used to specify general `clang`-accepted flags and remove them from `flang` compiler flags if
    # not supported for a particular version of LLVM
    FLANG_UNSUPPORTED_VARS = [
        ('19', '21', [
            '-fslp-vectorize',
            '-fvectorize',
            '-fno-vectorize',
            '-fno-unsafe-math-optimizations',
        ])
    ]

    FORTRAN_FLAGS = ['FCFLAGS', 'FFLAGS', 'F90FLAGS']

    COMPILER_UNIQUE_OPTS = {
        'loop-vectorize': (False, "Loop vectorization"),
        'basic-block-vectorize': (False, "Basic block vectorization"),

        # https://github.com/madler/zlib/issues/856
        'lld_undefined_version': (True, "-Wl,--undefined-version - Allow unused version in version script"),
        'no_unused_args': (
            True,
            (
                "-Wno-unused-command-line-argument - Avoid some failures in CMake correctly recognizing "
                "feature due to linker warnings"
            )
        ),
    }

    COMPILER_UNIQUE_OPTION_MAP = {
        'unroll': '-funroll-loops',
        'loop-vectorize': ['-fvectorize'],
        'basic-block-vectorize': ['-fslp-vectorize'],
        'optarch': '',
        # 'optarch': '-march=native',
        # Clang's options do not map well onto these precision modes.  The flags enable and disable certain classes of
        # optimizations.
        #
        # -fassociative-math: allow re-association of operands in series of floating-point operations, violates the
        # ISO C and C++ language standard by possibly changing computation result.
        # -freciprocal-math: allow optimizations to use the reciprocal of an argument rather than perform division.
        # -fsigned-zeros: do not allow optimizations to treat the sign of a zero argument or result as insignificant.
        # -fhonor-infinities: disallow optimizations to assume that arguments and results are not +/- Infs.
        # -fhonor-nans: disallow optimizations to assume that arguments and results are not +/- NaNs.
        # -ffinite-math-only: allow optimizations for floating-point arithmetic that assume that arguments and results
        # are not NaNs or +-Infs (equivalent to -fno-honor-nans -fno-honor-infinities)
        # -funsafe-math-optimizations: allow unsafe math optimizations (implies -fassociative-math, -fno-signed-zeros,
        # -freciprocal-math).
        # -ffast-math: an umbrella flag that enables all optimizations listed above, provides preprocessor macro
        # __FAST_MATH__.
        #
        # Using -fno-fast-math is equivalent to disabling all individual optimizations, see
        # http://llvm.org/viewvc/llvm-project/cfe/trunk/lib/Driver/Tools.cpp?view=markup (lines 2100 and following)
        #
        # 'strict', 'precise' and 'defaultprec' are all ISO C++ and IEEE complaint, but we explicitly specify details
        # flags for strict and precise for robustness against future changes.
        'strict': ['-fno-fast-math'],
        'precise': ['-fno-unsafe-math-optimizations'],
        'defaultprec': [],
        'loose': ['-ffast-math', '-fno-unsafe-math-optimizations'],
        'veryloose': ['-ffast-math'],
        'vectorize': {False: '-fno-vectorize', True: '-fvectorize'},
        DEFAULT_OPT_LEVEL: ['-O2'],

        'lld_undefined_version': ['-Wl,--undefined-version'],
        'no_unused_args': ['-Wno-unused-command-line-argument'],
    }

    COMPILER_OPTIONS = [
        'lld_undefined_version',
    ]

    # Options only available for Clang compiler
    COMPILER_C_OPTIONS = [
        'no_unused_args',
    ]

    # Options only available for Flang compiler
    COMPILER_F_OPTIONS = []

    # used when 'optarch' toolchain option is enabled (and --optarch is not specified)
    COMPILER_OPTIMAL_ARCHITECTURE_OPTION = {
        (systemtools.POWER, systemtools.POWER): '-mcpu=native',  # no support for march=native on POWER
        (systemtools.POWER, systemtools.POWER_LE): '-mcpu=native',  # no support for march=native on POWER
        (systemtools.X86_64, systemtools.AMD): '-march=native',
        (systemtools.X86_64, systemtools.INTEL): '-march=native',
    }
    # used with --optarch=GENERIC
    COMPILER_GENERIC_OPTION = {
        (systemtools.RISCV64, systemtools.RISCV): '-march=rv64gc -mabi=lp64d',  # default for -mabi is system-dependent
        (systemtools.X86_64, systemtools.AMD): '-march=x86-64 -mtune=generic',
        (systemtools.X86_64, systemtools.INTEL): '-march=x86-64 -mtune=generic',
    }

    COMPILER_CC = 'clang'
    COMPILER_CXX = 'clang++'
    COMPILER_C_UNIQUE_OPTIONS = []

    COMPILER_F77 = 'flang'
    COMPILER_F90 = 'flang'
    COMPILER_FC = 'flang'
    COMPILER_F_UNIQUE_OPTIONS = []

    LIB_MULTITHREAD = ['pthread']
    LIB_MATH = ['m']

    def _set_compiler_flags(self):
        super()._set_compiler_flags()

        unsupported_fortran_flags = None
        for v_min, v_max, flags in self.FLANG_UNSUPPORTED_VARS:
            if LooseVersion(self.version) >= LooseVersion(v_min) and LooseVersion(self.version) < LooseVersion(v_max):
                unsupported_fortran_flags = flags
                break
        else:
            self.log.debug("No unsupported flags found for LLVM version %s", self.version)

        if unsupported_fortran_flags is not None:
            self.log.debug(
                f"Ensuring usupported Fortran flags `{unsupported_fortran_flags}` are removed from variables"
            )
            for key, lst in self.variables.items():
                if key not in self.FORTRAN_FLAGS:
                    continue
                for item in lst:
                    item.try_remove(unsupported_fortran_flags)


@register_toolchain_entrypoint()
class LLVMtc(LLVM):
    """Compiler toolchain with Clang and Flang compilers."""
    NAME = 'LLVMtc'  # Using `...tc` to distinguish toolchain from package
    COMPILER_MODULE_NAME = [NAME]
    SUBTOOLCHAIN = [GCCcore.NAME, SYSTEM_TOOLCHAIN_NAME]


@register_toolchain_entrypoint()
class Lfbf(LLVMtc, FlexiBLAS, Fftw):
    """Compiler toolchain with GCC, FlexiBLAS and FFTW."""
    NAME = 'lfbf'
    SUBTOOLCHAIN = LLVMtc.NAME
    OPTIONAL = True


@register_toolchain_entrypoint()
class Lompi(LLVMtc, OpenMPI):
    """Compiler toolchain with GCC and OpenMPI."""
    NAME = 'lompi'
    SUBTOOLCHAIN = LLVMtc.NAME

    def is_deprecated(self):
        """Return whether or not this toolchain is deprecated."""
        # need to transform a version like '2018b' with something that is safe to compare with '2019'
        # comparing subversions that include letters causes TypeErrors in Python 3
        # 'a' is assumed to be equivalent with '.01' (January), and 'b' with '.07' (June) (good enough for this purpose)
        version = self.version.replace('a', '.01').replace('b', '.07')

        deprecated = False

        # make sure a non-symbolic version (e.g., 'system') is used before making comparisons using LooseVersion
        if re.match('^[0-9]', version):
            # lompi toolchains older than 2023b should not exist  (need GCC >= 13)
            if LooseVersion(version) < LooseVersion('2023'):
                deprecated = True

        return deprecated


@register_toolchain_entrypoint()
class Lolf(LLVMtc, OpenBLAS, Fftw):
    """Compiler toolchain with LLVM, OpenBLAS, and FFTW."""
    NAME = 'lolf'
    SUBTOOLCHAIN = LLVMtc.NAME
    OPTIONAL = True


@register_toolchain_entrypoint()
class LFoss(Lompi, FlexiBLAS, ScaLAPACK, Fftw):
    """Compiler toolchain with GCC, OpenMPI, FlexiBLAS, ScaLAPACK and FFTW."""
    NAME = 'lfoss'
    SUBTOOLCHAIN = [
        Lompi.NAME,
        Lolf.NAME,
        Lfbf.NAME
    ]

    def __init__(self, *args, **kwargs):
        """Toolchain constructor."""
        super(LFoss, self).__init__(*args, **kwargs)

        # need to transform a version like '2018b' with something that is safe to compare with '2019'
        # comparing subversions that include letters causes TypeErrors in Python 3
        # 'a' is assumed to be equivalent with '.01' (January), and 'b' with '.07' (June) (good enough for this purpose)
        version = self.version.replace('a', '.01').replace('b', '.07')

        self.looseversion = LooseVersion(version)

        constants = ('BLAS_MODULE_NAME', 'BLAS_LIB', 'BLAS_LIB_MT', 'BLAS_FAMILY',
                     'LAPACK_MODULE_NAME', 'LAPACK_IS_BLAS', 'LAPACK_FAMILY')

        for constant in constants:
            setattr(self, constant, getattr(FlexiBLAS, constant))

    def banned_linked_shared_libs(self):
        """
        List of shared libraries (names, file names, paths) which are
        not allowed to be linked in any installed binary/library.
        """
        res = []
        res.extend(Lompi.banned_linked_shared_libs(self))
        res.extend(FlexiBLAS.banned_linked_shared_libs(self))
        res.extend(ScaLAPACK.banned_linked_shared_libs(self))
        res.extend(Fftw.banned_linked_shared_libs(self))

        return res

    def is_deprecated(self):
        """Return whether or not this toolchain is deprecated."""

        # lfoss toolchains older than 2023b should not exist (need GCC >= 13)
        if self.looseversion < LooseVersion('2023'):
            deprecated = True
        else:
            deprecated = False

        return deprecated

# @register_toolchain_entrypoint()
# def this_is_not_a_toolchain():
#     """
#     This is not a toolchain, but a function to ensure that this module is
#     loaded as a Python package and can be used to register entrypoints.
#     """
#     pass

