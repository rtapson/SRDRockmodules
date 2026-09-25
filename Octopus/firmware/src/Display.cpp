#include "Display.h"
#include <Wire.h>
#include <U8x8lib.h>

namespace {
U8X8_SSD1306_128X64_NONAME_HW_I2C oled(U8X8_PIN_NONE);

constexpr uint8_t kCols = 16;            // 8x8 tiles across
constexpr uint8_t kNumberRow = 2;        // the 3x6-tile digits fill rows 2-7
constexpr uint8_t kDigitTiles = 3;
}  // namespace

void Display::begin() {
    Wire.beginTransmission(kAddr);
    present_ = Wire.endTransmission() == 0;
    if (!present_) {
        Serial.println(F("display not found on I2C; running without it"));
        return;
    }
    oled.setBusClock(400000);
    oled.begin();                        // also clears the screen
    oled.setPowerSave(0);
    drawn_ = false;
}

void Display::show(Mode mode, uint8_t preset, bool edited) {
    if (!present_) return;
    if (!drawn_ || mode != mode_ || edited != edited_) drawLabel(mode, edited);
    if (!drawn_ || preset != preset_) drawNumber(preset);
    mode_ = mode;
    preset_ = preset;
    edited_ = edited;
    drawn_ = true;
}

void Display::drawLabel(Mode mode, bool edited) {
    char line[kCols + 1];
    const char* label = mode == Mode::Selecting ? "SELECT?" : mode == Mode::Saved ? "SAVED" : "PRESET";
    snprintf(line, sizeof line, "%-8s%8s", label, edited && mode != Mode::Saved ? "EDITED" : "");
    oled.setFont(u8x8_font_chroma48medium8_r);
    oled.setInverseFont(mode == Mode::Selecting);
    oled.drawString(0, 0, line);
    oled.setInverseFont(0);
}

void Display::drawNumber(uint8_t preset) {
    // Always three characters, right-aligned and space-padded, so the old digits get
    // overwritten without clearing (and re-sending) the whole number area first.
    char digits[4];
    snprintf(digits, sizeof digits, "%3u", static_cast<unsigned>(preset) + 1);
    oled.setFont(u8x8_font_inb33_3x6_r);
    oled.drawString((kCols - 3 * kDigitTiles) / 2, kNumberRow, digits);
}
