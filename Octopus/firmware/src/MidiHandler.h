#pragma once
#include <Arduino.h>
#include "RelayBank.h"
#include "PresetStore.h"

// Serial-MIDI (5-pin DIN, via Serial1) input handling.
// Program Change recalls a stored preset (sets all 16 lines at once).
// Control Change (kBaseCC..kBaseCC+15) switches a single line live.
class MidiHandler {
public:
    // CC 102-117 -> lines 1-16. 102-119 are "undefined" in the MIDI spec; a 20-35 range
    // would include CC 32 (Bank Select LSB), which controllers send with program changes.
    static constexpr uint8_t kBaseCC = 102;

    MidiHandler(RelayBank& relays, PresetStore& presets);

    void begin();
    void update();

    // Public so the free-function MIDI library callbacks can reach them.
    void handleProgramChange(uint8_t channel, uint8_t number);
    void handleControlChange(uint8_t channel, uint8_t number, uint8_t value);

    // Recall preset 0-127 (all 16 lines at once): Program Change and the front-panel
    // encoder both come through here.
    void recall(uint8_t preset);

    // Last preset recalled (0 until the first one); the button panel's long-press saves
    // into this slot, and the display shows it (as 1-128).
    uint8_t currentPreset() const { return current_; }

private:
    RelayBank& relays_;
    PresetStore& presets_;
    uint8_t current_ = 0;
};
