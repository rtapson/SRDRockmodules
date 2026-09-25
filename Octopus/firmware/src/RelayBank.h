#pragma once
#include <Arduino.h>

// Drives the 16 relay lines through the two ULN2803A drivers.
// Lines 1-8 switch jack 1-8 TIP, lines 9-16 switch jack 1-8 RING.
// Pin map here must match Octopus/README.md's "Pin map (Teensy 4.1)" table.
class RelayBank {
public:
    static constexpr uint8_t kChannelCount = 16;

    void begin();

    // Sets all 16 lines at once from a 16-bit pattern (bit i = line i+1).
    void setPattern(uint16_t pattern);

    // Sets a single line (index 0-15 = line 1-16) without touching the others.
    void setChannel(uint8_t index, bool on);

    uint16_t pattern() const { return pattern_; }

private:
    static const uint8_t pins_[kChannelCount];
    uint16_t pattern_ = 0;
};
