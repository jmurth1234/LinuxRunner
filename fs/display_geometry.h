#ifndef LR_DISPLAY_GEOMETRY_H
#define LR_DISPLAY_GEOMETRY_H
#include <stdbool.h>
#include <stdint.h>
#define LR_DISPLAY_MAX_AXIS 4096U
#define LR_DISPLAY_MAX_PIXELS 8388608U
// Bound frame memory in both screen orientations.
static inline bool lr_display_dimensions(uint32_t width, uint32_t height) {
    return width && height && width <= LR_DISPLAY_MAX_AXIS && height <= LR_DISPLAY_MAX_AXIS &&
        (uint64_t)width * height <= LR_DISPLAY_MAX_PIXELS;
}
#endif
