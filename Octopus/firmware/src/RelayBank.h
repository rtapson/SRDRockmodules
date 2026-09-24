#pragma once
#include <Arduino.h>

// Drives the 8 relay outputs through the ULN2803A driver.
// Pin map here must match Octopus/README.md's "Pin map (Teensy 4.1)" table.
class RelayBank {
public:
    static constexpr uint8_t kChannelCount = 8;

    void begin();

    // Sets all 8 relays at once from an 8-bit pattern (bit i = relay i+1).
    void setPattern(uint8_t pattern);

    // Sets a single relay (index 0-7 = relay 1-8) without touching the others.
    void setChannel(uint8_t index, bool on);

    uint8_t pattern() const { return pattern_; }

private:
    static const uint8_t pins_[kChannelCount];
    uint8_t pattern_ = 0;
};
