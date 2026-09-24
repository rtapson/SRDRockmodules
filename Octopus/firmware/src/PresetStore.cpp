#include "PresetStore.h"
#include <EEPROM.h>

void PresetStore::begin() {
    if (EEPROM.read(kMagicAddr) != kMagic) {
        loadDefaults();
        return;
    }
    channel_ = EEPROM.read(kChannelAddr);
    for (uint16_t i = 0; i < kPresetCount; i++) {
        presets_[i] = EEPROM.read(kPresetBaseAddr + i);
    }
}

void PresetStore::loadDefaults() {
    channel_ = 0;
    for (uint16_t i = 0; i < kPresetCount; i++) {
        presets_[i] = 0;
        EEPROM.write(kPresetBaseAddr + i, 0);
    }
    EEPROM.write(kChannelAddr, channel_);
    EEPROM.write(kMagicAddr, kMagic);
}

uint8_t PresetStore::preset(uint8_t index) const {
    if (index >= kPresetCount) return 0;
    return presets_[index];
}

void PresetStore::setPreset(uint8_t index, uint8_t pattern) {
    if (index >= kPresetCount) return;
    presets_[index] = pattern;
    EEPROM.update(kPresetBaseAddr + index, pattern);
}

void PresetStore::setMidiChannel(uint8_t channel) {
    channel_ = channel;
    EEPROM.update(kChannelAddr, channel);
}
