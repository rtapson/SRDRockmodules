#pragma once
#include <Arduino.h>

// 128 MIDI-Program-Change presets (16-bit line pattern each) plus the MIDI
// channel setting, persisted in the Teensy's emulated EEPROM (survives power
// cycles and re-flashing, since it lives in a separate flash region).
class PresetStore {
public:
    static constexpr uint16_t kPresetCount = 128;

    void begin();

    uint16_t preset(uint8_t index) const;
    void setPreset(uint8_t index, uint16_t pattern);

    // 0 = omni, 1-16 = fixed MIDI channel.
    uint8_t midiChannel() const { return channel_; }
    void setMidiChannel(uint8_t channel);

private:
    static constexpr uint16_t kMagicAddr = 0;
    static constexpr uint16_t kChannelAddr = 1;
    static constexpr uint16_t kPresetBaseAddr = 2;   // 2 bytes per preset, little-endian
    // Bumped from 0xA5 (8-line, 1 byte/preset) so older EEPROM contents are reset
    // instead of being misread as 16-bit patterns.
    static constexpr uint8_t kMagic = 0xA6;

    void loadDefaults();
    void writePreset(uint8_t index, uint16_t pattern, bool updateOnly);

    uint16_t presets_[kPresetCount] = {};
    uint8_t channel_ = 0;
};
