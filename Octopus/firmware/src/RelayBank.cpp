#include "RelayBank.h"

const uint8_t RelayBank::pins_[RelayBank::kChannelCount] = {2, 3, 4, 5, 6, 7, 8, 9};

void RelayBank::begin() {
    for (uint8_t i = 0; i < kChannelCount; i++) {
        pinMode(pins_[i], OUTPUT);
        digitalWrite(pins_[i], LOW);
    }
    pattern_ = 0;
}

void RelayBank::setPattern(uint8_t pattern) {
    pattern_ = pattern;
    for (uint8_t i = 0; i < kChannelCount; i++) {
        digitalWrite(pins_[i], (pattern & (1 << i)) ? HIGH : LOW);
    }
}

void RelayBank::setChannel(uint8_t index, bool on) {
    if (index >= kChannelCount) return;
    if (on) {
        pattern_ |= static_cast<uint8_t>(1 << index);
    } else {
        pattern_ &= static_cast<uint8_t>(~(1 << index));
    }
    digitalWrite(pins_[index], on ? HIGH : LOW);
}
