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
REG_BUSY_STATUS     = 0x0C
REG_READING_BASE    = 0x20  # 0x20..0x27 inclusive (IN0..IN7 / temp as assigned)
REG_LIMITS_BASE     = 0x2A  # IN0 -> 0x2A high, 0x2B low (then IN1, etc) Depends on mode

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
        self.mode = (mode & 0x03)
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
        self.config = config

        # Reset
        cfg = 0b10000000 
        self.write_u8(REG_CONFIG, cfg)
        time.sleep(0.01)  # per datasheet, 10ms after clearing START

        # wait for ready
        if not self.wait_until_ready(timeout=1.0):
            raise TimeoutError("Timeout waiting for ADC128D818 to become ready after reset")

        # set the advanced config:
        # Bit0=1 internal Vref (0=external), 
        # Bit1..1=MODE 0..3
        self.write_u8(REG_ADV_CONFIG, self.config.mode << 1) 

        # Conversion Rate: bit0=1 continuous, 0 low-power; only valid in shutdown
        self.write_u8(REG_CONV_RATE, 0x01 if self.config.continuous else 0x00)

        # Disable channels (1=disable). Only valid in shutdown.
        self.write_u8(REG_CH_DISABLE, self.config.disable_mask & 0xFF)

        # Disable channels interrupt mask.
        self.write_u8(REG_INT_MASK, 0x00)  # all disabled

        # Set limits for all channels (example values here, adjust as needed)
        for i in range(8):
            self.set_limits_raw(i, 0x0000, 0x0FFF)  # channel 0 limits as example

        cfg = 0b00000000 
        self.write_u8(REG_CONFIG, cfg)
        time.sleep(0.01)  # per datasheet, 10ms after clearing START        

        # Start sampling if requested
        if self.config.start:
            self._start(True)

        print(f"configure: config      : 0x{self.read_u8(REG_CONFIG):08b}")
        print(f"configure: int_status  : 0x{self.read_u8(REG_INT_STATUS):08b}")
        print(f"configure: int_mask    : 0x{self.read_u8(REG_INT_MASK):08b}")
        print(f"configure: conv_rate   : 0x{self.read_u8(REG_CONV_RATE):08b}")
        print(f"configure: ch_disable  : 0x{self.read_u8(REG_CH_DISABLE):08b}")
        print(f"configure: deep_shdwn  : 0x{self.read_u8(REG_DEEP_SHUTDOWN):08b}")
        print(f"configure: adv_config  : 0x{self.read_u8(REG_ADV_CONFIG):08b}")
        print(f"configure: busy_status : 0x{self.read_u8(REG_BUSY_STATUS):08b}")

    def wait_until_ready(self, timeout: float = 1.0) -> bool:
        t0 = time.time()
        while self.read_u8(REG_BUSY_STATUS) & 0x03:
            if (time.time() - t0) > timeout:
                return False
            time.sleep(0.01)
        return True

    def trigger_one_shot(self) -> None:
        """
        When in shutdown (or deep shutdown), writing any value to ONE_SHOT triggers a single conversion.
        """
        self.read_u8(REG_INT_STATUS)  # clear any pending interrupt
        self.write_u8(REG_ONE_SHOT, 0x01)
        if not self.wait_until_ready(timeout=1.0):
            raise TimeoutError("Timeout waiting for ADC128D818 to complete one-shot conversion")

    def deep_shutdown(self, enable: bool) -> None:
        # Enter deep shutdown after clearing START; exit by writing 0
        if enable:
            self._start(False)
            self.write_u8(REG_DEEP_SHUTDOWN, 0x01)
        else:
            self.write_u8(REG_DEEP_SHUTDOWN, 0x00)

    def set_limits_raw(self, index: int, low: int, high: int) -> None:
        if not (0 <= index <= 7):
            raise ValueError("channel index 0..7")
        # Set low/high limit registers (16-bit values)
        reg = REG_LIMITS_BASE + index * 2
        self.write_u16_be(reg, high & 0xFFFF)
        self.write_u16_be(reg + 1, low & 0xFFFF)

    def read_channel_raw(self, index: int) -> int:
        if not (0 <= index <= 7):
            raise ValueError("channel index 0..7")
        self.read_u8(REG_INT_STATUS)
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

        self.wait_until_ready(timeout=1.0)
        raw = self.read_channel_raw(index)
        volts = self._convert_raw_to_volts(raw, index)
        print(f"Reading channel {index}: {volts:9.4f} (raw 0x{raw:04X})")
        return volts, raw

    def read_channels(self, active_mask: int = 0xFF) -> Dict[str, Any]:
        readings: Dict[str, Any] = {}

        if self.config.continuous is False:
            self.trigger_one_shot()

        self.wait_until_ready(timeout=1.0)

        for ch in range(8):
            if (active_mask >> ch) & 0x1:
                raw = self.read_channel_raw(ch)
                volts = self._convert_raw_to_volts(raw, ch)
                readings[f"ch_{ch}"] = {"raw":raw, "val": volts}
                print(f"Reading channel {ch}: {volts:9.4f} (raw 0x{raw:04X})")
                # readings[f"in{ch}_v"] = volts
                # readings[f"in{ch}_raw"] = raw
        return readings
