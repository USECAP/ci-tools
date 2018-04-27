"""Setup ci-tools

"""
import os
import platform
import re
import subprocess
import sys
import multiprocessing

from distutils.version import LooseVersion
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    """setuptools extension allowing to build with cmake"""
    def __init__(self, name, sourcedir='', targetdir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)
        self.targetdir = os.path.abspath(targetdir)


class CMakeBuild(build_ext):
    """Building with cmake"""
    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: " +
                ", ".join(e.name for e in self.extensions))

        if platform.system() == "Windows":
            cmake_version = LooseVersion(re.search(r'version\s*([\d.]+)',
                                                   out.decode()).group(1))
            if cmake_version < '3.1.0':
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(
            os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DCMAKE_INSTALL_PREFIX=' + ext.targetdir]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(
                cfg.upper(),
                extdir)]
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j{}'.format(multiprocessing.cpu_count())]

        env = os.environ.copy()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(
            env.get('CXXFLAGS', ''),
            self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args,
                              cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args,
                              cwd=self.build_temp)
        subprocess.check_call(['make', 'install'],
                              cwd=self.build_temp)
        print()  # Add an empty line for cleaner output


setup(
    name='ci_tools',
    version='0.0.1',
    description='Code Intelligence Tools',
    include_package_data=True,
    install_requires=[
        'wllvm', 'pyyaml', 'jsonschema', 'typing', 'scan-build',
        'jsonrpcserver', 'jsonrpcclient', 'websockets'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['mock', 'pytest', 'pytest-cov'],
    package_data={'': ['config/specs/*.json']},
    packages=find_packages(exclude=['lib', 'scripts']) + [''],
    ext_modules=[CMakeExtension('checkers',
                                sourcedir='lib/src/checkers',
                                targetdir='.')],
    entry_points={
        'console_scripts': [
            'ci-vulnscan = analysis:analyze_main',
            'ci-build = compile:build_main',
            'ci-cc = compile:compile_main',
            'ci-server = service.server:main',
            'ci-fuzz = fuzzing.libfuzzer:run_fuzzer'
        ]
    },
    cmdclass=dict(build_ext=CMakeBuild),
    zip_safe=False
)
