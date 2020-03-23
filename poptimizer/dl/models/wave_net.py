"""Модель на основе WaveNet."""
from typing import Dict, Union, List

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader


class SubBlock(nn.Module):
    """Блок с гейтом и остаточным соединением."""

    def __init__(
        self, kernels: int, gate_channels: int, residual_channels: int
    ) -> None:
        """
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param gate_channels:
            Количество каналов в signal и gate сверточных слоях.
        :param residual_channels:
            Количество каналов на входе и по обходному пути.
        """
        super().__init__()
        self.signal_gate_pad = nn.ConstantPad1d(padding=(kernels - 1, 0), value=0.0)
        self.signal_conv = nn.Conv1d(
            in_channels=residual_channels,
            out_channels=gate_channels,
            kernel_size=kernels,
            stride=1,
        )
        self.gate_conv = nn.Conv1d(
            in_channels=residual_channels,
            out_channels=gate_channels,
            kernel_size=kernels,
            stride=1,
        )
        self.output_conv = nn.Conv1d(
            in_channels=gate_channels, out_channels=residual_channels, kernel_size=1
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
           |-------------------------|
           | |-signal-relu-|         |
        ->-|-|             *-output->+->
             |-gate--sigma-|
        """
        y = self.signal_gate_pad(x)

        y_signal = self.signal_conv(y)
        y_signal = torch.relu(y_signal)

        y_gate = self.gate_conv(y)
        y_gate = torch.sigmoid(y_gate)

        y = y_signal * y_gate
        y = self.output_conv(y)

        return y + x


class Block(nn.Module):
    """Блок, состоящий из нескольких маленьких блоков и последующим уменьшением размерности.

     Имеет два выхода:
     - Основной с уменьшенной в два раза размерностью;
     - Скип для суммирования последнего значения слоя с остальными скипами и расчета общего выходного
     значения.
     """

    def __init__(
        self,
        sub_blocks: int,
        kernels: int,
        gate_channels: int,
        residual_channels: int,
        skip_channels: int,
    ) -> None:
        """
        :param sub_blocks:
            Количество маленьких блоков в блоке.
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param gate_channels:
            Количество каналов в signal и gate сверточных слоях маленьких блоков.
        :param residual_channels:
            Количество каналов на входе и по обходному пути маленьких блоков.
        :param skip_channels:
            Количество каналов у скипа.
        """
        super().__init__()
        self.sub_blocks = nn.ModuleList()
        for i in range(sub_blocks):
            self.sub_blocks.append(
                SubBlock(
                    kernels=kernels,
                    gate_channels=gate_channels,
                    residual_channels=residual_channels,
                )
            )
        self.skip_convs = nn.Conv1d(
            in_channels=residual_channels, out_channels=skip_channels, kernel_size=1
        )
        self.dilated_pad = nn.ConstantPad1d(padding=(1, 0), value=0.0)
        self.dilated_convs = nn.Conv1d(
            in_channels=residual_channels,
            out_channels=residual_channels,
            kernel_size=2,
            stride=2,
        )

    def forward(self, x: torch.Tensor) -> (torch.Tensor, torch.Tensor):
        """
                        |-dilated->
        ->n x SubBlock -|
                        |-skip---->
        """
        y = x
        for sub_block in self.sub_blocks:
            y = sub_block(y)

        skip = self.skip_convs(y[:, :, -1:])

        y = self.dilated_pad(y)
        y = self.dilated_convs(y)

        return y, skip


class WaveNet(nn.Module):
    """За основу взята WaveNet https://arxiv.org/abs/1609.03499

    Сверточная сеть с большим полем восприятия - удваивается при увеличении глубины на один уровень,
    что позволяет анализировать длинные последовательности котировок.
    """

    def __init__(
        self,
        data_loader: DataLoader,
        start_bn: bool,
        sub_blocks: int,
        kernels: int,
        gate_channels: int,
        residual_channels: int,
        skip_channels: int,
        end_channels: int,
    ) -> None:
        """
        :param data_loader:
            Загрузчик данных - нужен для определения параметров входных данных и расчета необходимой
            глубины сети.
        :param start_bn:
            Нужно ли производить BN для входящих численных значений.
        :param sub_blocks:
            Количество маленьких блоков в блоке.
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param gate_channels:
            Количество каналов в signal и gate сверточных слоях маленьких блоков.
        :param residual_channels:
            Количество каналов на входе и по обходному пути маленьких блоков.
        :param skip_channels:
            Количество каналов у скипа.
        :param end_channels:
            Количество каналов, до которого сжимаются скипы перед расчетом финального значений.
        """
        super().__init__()

        batch = next(iter(data_loader))
        input_sequences = len(batch["Sequence"])
        history_days = batch["Sequence"][0].shape[1]

        if start_bn:
            self.bn = nn.BatchNorm1d(input_sequences)
        else:
            self.bn = nn.Identity()

        self.start_conv = nn.Conv1d(
            in_channels=input_sequences, out_channels=residual_channels, kernel_size=1
        )

        self.blocks = nn.ModuleList()
        blocks = int(np.log2(history_days - 1)) + 1
        for block in range(blocks):
            self.blocks.append(
                Block(
                    sub_blocks=sub_blocks,
                    kernels=kernels,
                    gate_channels=gate_channels,
                    residual_channels=residual_channels,
                    skip_channels=skip_channels,
                )
            )

        self.skip_channels = skip_channels
        self.final_skip_conv = nn.Conv1d(
            in_channels=residual_channels, out_channels=skip_channels, kernel_size=1
        )

        self.end_conv = nn.Conv1d(
            in_channels=skip_channels, out_channels=end_channels, kernel_size=1
        )
        self.output_conv = nn.Conv1d(
            in_channels=end_channels, out_channels=1, kernel_size=1
        )

    def forward(
        self, batch: Dict[str, Union[torch.Tensor, List[torch.Tensor]]]
    ) -> torch.Tensor:
        """
        ->nb-start-Block-|-Block-|-...-Block-|-final_skip-|
                         |-skips-+-...-skips-+-skips------+-relu-end-relu-output->
        """
        y = torch.stack(batch["Sequence"], dim=1)
        y = self.bn(y)
        y = self.start_conv(y)

        skips = torch.zeros((y.shape[0], self.skip_channels, 1))

        for block in self.blocks:
            y, skip = block(y)
            skips = skips + skip

        skip = self.final_skip_conv(y)
        skips = skip + skips

        y = torch.relu(skips)
        y = self.end_conv(y)
        y = torch.relu(y)
        y = self.output_conv(y)

        return y.squeeze(dim=-1)
