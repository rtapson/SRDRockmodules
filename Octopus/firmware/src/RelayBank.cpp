#include "RelayBank.h"

// Lines 1-8 (jack tips) via ULN2803A U3, lines 9-16 (jack rings) via U5.
const uint8_t RelayBank::pins_[RelayBank::kChannelCount] = {
    2, 3, 4, 5, 6, 7, 8, 9,
    24, 25, 26, 27, 28, 29, 30, 31,
};

void RelayBank::begin() {
    for (uint8_t i = 0; i < kChannelCount; i++) {
        pinMode(pins_[i], OUTPUT);
        digitalWrite(pins_[i], LOW);
    }
    pattern_ = 0;
}

void RelayBank::setPattern(uint16_t pattern) {
    pattern_ = pattern;
    for (uint8_t i = 0; i < kChannelCount; i++) {
        digitalWrite(pins_[i], (pattern & (1u << i)) ? HIGH : LOW);
    }
}

void RelayBank::setChannel(uint8_t index, bool on) {
    if (index >= kChannelCount) return;
    if (on) {
        pattern_ |= static_cast<uint16_t>(1u << index);
    } else {
        pattern_ &= static_cast<uint16_t>(~(1u << index));
    }
    digitalWrite(pins_[index], on ? HIGH : LOW);
}
