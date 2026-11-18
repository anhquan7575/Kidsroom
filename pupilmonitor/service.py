"""Deprecated: use kidsroom.service instead."""
import warnings
from kidsroom.service import *

warnings.warn("pupilmonitor.service is deprecated, use kidsroom.service instead", DeprecationWarning, stacklevel=2)
