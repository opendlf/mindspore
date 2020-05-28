# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# httpwww.apache.orglicensesLICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Init DeepLabv3."""
from .deeplabv3 import ASPP, DeepLabV3, deeplabv3_resnet50
from . import backbone
from .backbone import *

__all__ = [
    "ASPP", "DeepLabV3", "deeplabv3_resnet50", "Decoder"
]

__all__.extend(backbone.__all__)
