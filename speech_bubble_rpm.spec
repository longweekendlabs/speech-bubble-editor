# -*- mode: python ; coding: utf-8 -*-
"""Compatibility entry point for build_rpm.sh; all packages share one spec."""
import os

_shared_spec = os.path.join(os.path.dirname(os.path.abspath(SPEC)),
                            'speech_bubble.spec')
with open(_shared_spec, encoding='utf-8') as _source:
    exec(compile(_source.read(), _shared_spec, 'exec'))
