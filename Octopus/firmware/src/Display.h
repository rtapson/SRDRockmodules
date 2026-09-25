#pragma once
#include <Arduino.h>

// 0.96" 128x64 SSD1306 OLED (Winstar WEA012864D-03) on the button board, I2C 0x3C, on the
// same bus as the panel's LED drivers. Uses U8g2's buffer-less U8x8 mode and redraws only
// what changed, so the I2C bus (and the loop) is busy for as little time as possible.
//
//   row 0     label: PRESET / SELECT? / SAVED            and "EDITED" when the lines no
//                                                         longer match the stored preset
//   rows 2-7  the preset number, 1-128, in big digits
class Display {
public:
    enum class Mode : uint8_t { Current, Selecting, Saved };

    // Probes the display; if it doesn't answer, show() does nothing.
    void begin();
    bool present() const { return present_; }

    // preset is 0-127 (shown as 1-128)
    void show(Mode mode, uint8_t preset, bool edited);

private:
    static constexpr uint8_t kAddr = 0x3C;
    bool present_ = false;
    bool drawn_ = false;
    Mode mode_ = Mode::Current;
    uint8_t preset_ = 0;
    bool edited_ = false;

    void drawLabel(Mode mode, bool edited);
    void drawNumber(uint8_t preset);
};
