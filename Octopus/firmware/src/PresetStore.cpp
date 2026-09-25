#include "PresetStore.h"
#include <EEPROM.h>

void PresetStore::begin() {
    if (EEPROM.read(kMagicAddr) != kMagic) {
        loadDefaults();
        return;
    }
    channel_ = EEPROM.read(kChannelAddr);
    for (uint16_t i = 0; i < kPresetCount; i++) {
        uint16_t addr = kPresetBaseAddr + i * 2;
        presets_[i] = static_cast<uint16_t>(EEPROM.read(addr) | (EEPROM.read(addr + 1) << 8));
    }
}

void PresetStore::loadDefaults() {
    channel_ = 0;
    for (uint16_t i = 0; i < kPresetCount; i++) {
        presets_[i] = 0;
        writePreset(static_cast<uint8_t>(i), 0, false);
    }
    EEPROM.write(kChannelAddr, channel_);
    EEPROM.write(kMagicAddr, kMagic);
}

void PresetStore::writePreset(uint8_t index, uint16_t pattern, bool updateOnly) {
    uint16_t addr = kPresetBaseAddr + index * 2;
    uint8_t lo = pattern & 0xFF;
    uint8_t hi = pattern >> 8;
    if (updateOnly) {
        EEPROM.update(addr, lo);
        EEPROM.update(addr + 1, hi);
    } else {
        EEPROM.write(addr, lo);
        EEPROM.write(addr + 1, hi);
    }
}

uint16_t PresetStore::preset(uint8_t index) const {
    if (index >= kPresetCount) return 0;
    return presets_[index];
}

void PresetStore::setPreset(uint8_t index, uint16_t pattern) {
    if (index >= kPresetCount) return;
    presets_[index] = pattern;
    writePreset(index, pattern, true);
}

void PresetStore::setMidiChannel(uint8_t channel) {
    channel_ = channel;
    EEPROM.update(kChannelAddr, channel);
}
