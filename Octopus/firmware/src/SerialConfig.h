#pragma once
#include <Arduino.h>
#include "PresetStore.h"

// Tiny USB-serial text protocol for editing presets/MIDI channel without
// re-flashing. See firmware/README.md for the command reference.
class SerialConfig {
public:
    explicit SerialConfig(PresetStore& presets);

    void begin();
    void update();

private:
    PresetStore& presets_;
    String lineBuffer_;

    void handleLine(const String& line);
    void printHelp();
    void printDump();
    void printPattern(uint16_t pattern);
};
