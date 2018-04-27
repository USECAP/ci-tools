"""Module for the fuzzing engine"""
from .libfuzzer import run_fuzzer, parse_libfuzzer
__all__ = 'libfuzzer, run'
