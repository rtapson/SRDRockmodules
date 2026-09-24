#include "SerialConfig.h"

SerialConfig::SerialConfig(PresetStore& presets) : presets_(presets) {}

void SerialConfig::begin() {
    lineBuffer_.reserve(32);
}

void SerialConfig::update() {
    while (Serial.available()) {
        char c = static_cast<char>(Serial.read());
        if (c == '\n' || c == '\r') {
            if (lineBuffer_.length() > 0) {
                handleLine(lineBuffer_);
                lineBuffer_ = "";
            }
        } else {
            lineBuffer_ += c;
        }
    }
}

void SerialConfig::handleLine(const String& line) {
    String cmd = line;
    cmd.trim();
    cmd.toUpperCase();

    if (cmd == "HELP") {
        printHelp();
        return;
    }
    if (cmd == "DUMP") {
        printDump();
        return;
    }
    if (cmd.startsWith("CH=")) {
        int value = cmd.substring(3).toInt();
        if (value < 0 || value > 16) {
            Serial.println(F("ERR: channel must be 0 (omni) - 16"));
            return;
        }
        presets_.setMidiChannel(static_cast<uint8_t>(value));
        Serial.print(F("OK channel="));
        Serial.println(value);
        return;
    }
    if (cmd.startsWith("P")) {
        int eq = cmd.indexOf('=');
        if (eq < 1) {
            Serial.println(F("ERR: expected P<n>=<8 bits of 0/1>"));
            return;
        }
        int index = cmd.substring(1, eq).toInt();
        String bits = cmd.substring(eq + 1);
        if (index < 0 || index >= static_cast<int>(PresetStore::kPresetCount) || bits.length() != 8) {
            Serial.println(F("ERR: preset must be 0-127, pattern must be 8 chars of 0/1"));
            return;
        }
        uint8_t pattern = 0;
        for (uint8_t i = 0; i < 8; i++) {
            char c = bits[i];
            if (c != '0' && c != '1') {
                Serial.println(F("ERR: pattern must contain only 0/1"));
                return;
            }
            if (c == '1') pattern |= static_cast<uint8_t>(1 << i);
        }
        presets_.setPreset(static_cast<uint8_t>(index), pattern);
        Serial.print(F("OK preset "));
        Serial.print(index);
        Serial.print(F(" = "));
        Serial.println(bits);
        return;
    }

    Serial.println(F("ERR: unknown command, try HELP"));
}

void SerialConfig::printHelp() {
    Serial.println(F("Octopus config console:"));
    Serial.println(F("  P<n>=<8 bits>   set preset n (0-127) pattern, char i = relay i+1, e.g. P12=00110101"));
    Serial.println(F("  CH=<n>          set MIDI channel, 0 = omni, 1-16 = fixed channel"));
    Serial.println(F("  DUMP            list all non-empty presets and current channel"));
    Serial.println(F("  HELP            show this message"));
}

void SerialConfig::printDump() {
    Serial.print(F("channel="));
    Serial.println(presets_.midiChannel());
    for (uint16_t i = 0; i < PresetStore::kPresetCount; i++) {
        uint8_t pattern = presets_.preset(static_cast<uint8_t>(i));
        if (pattern == 0) continue;
        Serial.print(F("preset "));
        Serial.print(i);
        Serial.print(F(" = "));
        for (uint8_t bit = 0; bit < 8; bit++) {
            Serial.print((pattern & (1 << bit)) ? '1' : '0');
        }
        Serial.println();
    }
}
