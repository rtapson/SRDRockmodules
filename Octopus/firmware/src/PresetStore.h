#pragma once
#include <Arduino.h>

// 128 MIDI-Program-Change presets (1 byte relay pattern each) plus the MIDI
// channel setting, persisted in the Teensy's emulated EEPROM (survives power
// cycles and re-flashing, since it lives in a separate flash region).
class PresetStore {
public:
    static constexpr uint16_t kPresetCount = 128;

    void begin();

    uint8_t preset(uint8_t index) const;
    void setPreset(uint8_t index, uint8_t pattern);

    // 0 = omni, 1-16 = fixed MIDI channel.
    uint8_t midiChannel() const { return channel_; }
    void setMidiChannel(uint8_t channel);

private:
    static constexpr uint16_t kMagicAddr = 0;
    static constexpr uint16_t kChannelAddr = 1;
    static constexpr uint16_t kPresetBaseAddr = 2;
    static constexpr uint8_t kMagic = 0xA5;

    void loadDefaults();

    uint8_t presets_[kPresetCount] = {};
    uint8_t channel_ = 0;
};
