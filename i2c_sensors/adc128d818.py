from __future__ import annotations
from typing import Dict, Any, List, Tuple
from .base import I2CDevice
import time

# Key registers
REG_CONFIG          = 0x00
REG_INT_STATUS      = 0x01
REG_INT_MASK        = 0x03
REG_CONV_RATE       = 0x07
REG_CH_DISABLE      = 0x08
REG_ONE_SHOT        = 0x09
REG_DEEP_SHUTDOWN   = 0x0A
REG_ADV_CONFIG      = 0x0B
REG_READING_BASE    = 0x20  # 0x20..0x27 inclusive (IN0..IN7 / temp as assigned)

# Helpers
INTERNAL_VREF_V = 2.56     # default internal Vref (0.625mV/LSB)
ADC_LSB_V       = INTERNAL_VREF_V / 4096.0

class ADC128ChannelReading:
    raw: int
    volts: float

    def __init__(self, raw: int, volts: float):
        self.raw = raw
        self.volts = volts

class ADC128D818Config:
    """
    Configuration object for ADC128D818
    - start: set START bit
    - continuous: if False, set low-power conversion (convert all enabled, then shutdown)
    - disable_mask: bit i disables channel i when set. Must be done in shutdown.
    - extResistorMultipliers: List of 8 floats, one per channel, to scale readings if using
        external Vref divider. E.g. for a 10k/30k divider, multiplier is 4.0 (Vout=Vin*10k/40k).
    """
    start: bool = True
    continuous: bool = True
    disable_mask: int = 0x00
    mode: int = 0x00 # 0-3, see datasheet
    extResistorMultipliers: List[float] = [1.0] * 8 # if using external Vref divider

    def __init__(self,  
                 start: bool = True,
                 continuous: bool = True,
                 disable_mask: int = 0x00,
                 mode: int = 0x00,
                 extResistorMultipliers: List[float] = [1.0] * 8):
        self.start = start
        self.continuous = continuous
        self.disable_mask = disable_mask
        self.mode = (mode & 0x03) << 1
        if len(extResistorMultipliers) != 8:
            raise ValueError("extResistorMultipliers must be length 8")
        self.extResistorMultipliers = extResistorMultipliers

class ADC128D818(I2CDevice):
    # extResistorMultipliers: List[float] = [1.0] * 8 # if using external Vref divider
    config: ADC128D818Config

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
        print(f"_start: cfg : 0x{cfg:08b}")

    def configure(self,
                  config: ADC128D818Config
                  ) -> None:
        """
        - config: configuration object with fields:
            - start: set START bit
            - continuous: if False, set low-power conversion (convert all enabled, then shutdown)
            - disable_mask: bit i disables channel i when set. Must be done in shutdown.
            - extResistorMultipliers: List of 8 floats, one per channel, to scale readings
        """
        # Enter shutdown to tweak conversion rate & channel disable
        self._start(False)
        self.config = config

        cfg = 0b10000000 
        self.write_u8(REG_CONFIG, cfg)
        time.sleep(0.01)  # per datasheet, 10ms after clearing START

        self.deep_shutdown(True)  # exit deep shutdown if set

        # Conversion Rate: bit0=1 continuous, 0 low-power; only valid in shutdown
        self.write_u8(REG_CONV_RATE, 0x01 if config.continuous else 0x00)

        # Disable channels (1=disable). Only valid in shutdown.
        self.write_u8(REG_CH_DISABLE, config.disable_mask & 0xFF)


        self.write_u8(REG_ADV_CONFIG, self.config.mode)  # advanced config - mode 1

        # Start sampling if requested
        if config.start:
            self._start(True)

        cfg = self.read_u8(REG_CONFIG)
        print(f"configure: cfg : 0x{cfg:08b}")
        print(f"configure: conv_rate : 0x{self.read_u8(REG_CONV_RATE):08b}")
        print(f"configure: ch_disable : 0x{self.read_u8(REG_CH_DISABLE):08b}")
        print(f"configure: adv_config : 0x{self.read_u8(REG_ADV_CONFIG):08b}")

    def trigger_one_shot(self) -> None:
        """
        When in shutdown (or deep shutdown), writing any value to ONE_SHOT triggers a single conversion.
        """
        self.deep_shutdown(False)  # exit deep shutdown if set
        self.write_u8(REG_CONFIG, 0x01)  # ensure START=1
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
        # while self.read_u8(REG_INT_STATUS) & 0x1 == 0:
        #     time.sleep(0.01)
        return self.read_u16_be(REG_READING_BASE + index)
    
    def _convert_raw_to_volts(self, raw: int, index: int) -> float:
        # 12-bit value is left-justified in a 16-bit reg in many TI monitors;
        # Datasheet states 16-bit reg to accommodate 12-bit reading (or 9-bit temp).
        # We assume upper 12 bits; if using full 16, adjust here easily.
        value_12b = (raw >> 4) & 0x0FFF
        volts = value_12b * self.config.extResistorMultipliers[index] * ADC_LSB_V
        return volts

    def read_channel(self, index: int) -> Tuple[float, int]:
        if not (0 <= index <= 7):
            raise ValueError("channel index 0..7")
        
        if self.config.continuous is False:
            self.trigger_one_shot()
            time.sleep(1)  # allow time for conversion;

        raw = self.read_channel_raw(index)
        volts = self._convert_raw_to_volts(raw, index)
        print(f"Reading channel {index}: {volts:9.4f} (raw 0x{raw:04X})")
        return volts, raw

    def read_channels(self, active_mask: int = 0xFF) -> Dict[str, Any]:
        readings: Dict[str, Any] = {}

        if self.config.continuous is False:
            self.trigger_one_shot()
            time.sleep(1)  # allow time for conversion;

        for ch in range(8):
            if (active_mask >> ch) & 0x1:
                raw = self.read_channel_raw(ch)
                volts = self._convert_raw_to_volts(raw, ch)
                readings[f"ch_{ch}"] = {"raw":raw, "val": volts}
                print(f"Reading channel {ch}: {volts:9.4f} (raw 0x{raw:04X})")
                # readings[f"in{ch}_v"] = volts
                # readings[f"in{ch}_raw"] = raw
        return readings
