from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from .base import I2CDevice

# Key registers
REG_CONFIG          = 0x00
REG_INT_STATUS      = 0x01
REG_INT_MASK        = 0x03
REG_CONV_RATE       = 0x07
REG_CH_DISABLE      = 0x08
REG_ONE_SHOT        = 0x09
REG_DEEP_SHUTDOWN   = 0x0A
REG_READING_BASE    = 0x20  # 0x20..0x27 inclusive (IN0..IN7 / temp as assigned)

# Helpers
INTERNAL_VREF_V = 2.56     # default internal Vref (0.625mV/LSB)
ADC_LSB_V       = INTERNAL_VREF_V / 4096.0

@dataclass
class ADC128ChannelReading:
    raw: int
    volts: float

class ADC128D818(I2CDevice):
    """
    TI ADC128D818 – 8ch, 12-bit ΔΣ ADC w/ temp sensor and internal 2.56V Vref.
    """
    def _start(self, enable: bool) -> None:
        # Bit0 START, Bit1 INT_Enable, Bit3 INT_Clear, Bit7 INITIALIZATION
        cfg = self.read_u8(REG_CONFIG)
        if enable:
            cfg |= 0b00000001
        else:
            cfg &= ~0b00000001
        self.write_u8(REG_CONFIG, cfg)

    def configure(self,
                  start: bool = True,
                  continuous: bool = True,
                  disable_mask: int = 0x00) -> None:
        """
        - start: set START bit
        - continuous: if False, set low-power conversion (convert all enabled, then shutdown)
        - disable_mask: bit i disables channel i when set. Must be done in shutdown.
        """
        # Enter shutdown to tweak conversion rate & channel disable
        self._start(False)
        # Conversion Rate: bit0=1 continuous, 0 low-power; only valid in shutdown
        self.write_u8(REG_CONV_RATE, 0x01 if continuous else 0x00)
        # Disable channels (1=disable). Only valid in shutdown.
        self.write_u8(REG_CH_DISABLE, disable_mask & 0xFF)
        # Start sampling if requested
        if start:
            self._start(True)

    def trigger_one_shot(self) -> None:
        """
        When in shutdown (or deep shutdown), writing any value to ONE_SHOT triggers a single conversion.
        """
        self.write_u8(REG_ONE_SHOT, 0x01)

    def deep_shutdown(self, enable: bool) -> None:
        # Enter deep shutdown after clearing START; exit by writing 0
        if enable:
            self._start(False)
            self.write_u8(REG_DEEP_SHUTDOWN, 0x01)
        else:
            self.write_u8(REG_DEEP_SHUTDOWN, 0x00)

    def read_channel_raw(self, index: int) -> int:
        if not (0 <= index <= 7):
            raise ValueError("channel index 0..7")
        return self.read_u16_be(REG_READING_BASE + index)

    def read_channels(self, active_mask: int = 0xFF) -> Dict[str, Any]:
        readings: Dict[str, Any] = {}
        for ch in range(8):
            if (active_mask >> ch) & 0x1:
                raw = self.read_channel_raw(ch)
                # 12-bit value is left-justified in a 16-bit reg in many TI monitors;
                # Datasheet states 16-bit reg to accommodate 12-bit reading (or 9-bit temp).
                # We assume upper 12 bits; if using full 16, adjust here easily.
                value_12b = (raw >> 4) & 0x0FFF
                volts = value_12b * ADC_LSB_V
                readings[f"in{ch}_v"] = volts
                readings[f"in{ch}_raw"] = raw
        return readings
