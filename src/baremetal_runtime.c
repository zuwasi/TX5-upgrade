#include <stddef.h>
#include <stdint.h>

void *memcpy(void *destination, const void *source, size_t count)
{
    uint8_t *out = destination;
    const uint8_t *in = source;

    for (size_t index = 0U; index < count; ++index) {
        out[index] = in[index];
    }
    return destination;
}

void *memset(void *destination, int value, size_t count)
{
    uint8_t *out = destination;

    for (size_t index = 0U; index < count; ++index) {
        out[index] = (uint8_t)value;
    }
    return destination;
}

void *memmove(void *destination, const void *source, size_t count)
{
    uint8_t *out = destination;
    const uint8_t *in = source;

    if ((uintptr_t)out < (uintptr_t)in) {
        for (size_t index = 0U; index < count; ++index) {
            out[index] = in[index];
        }
    } else if ((uintptr_t)out > (uintptr_t)in) {
        for (size_t index = count; index != 0U; --index) {
            out[index - 1U] = in[index - 1U];
        }
    }
    return destination;
}

int memcmp(const void *left, const void *right, size_t count)
{
    const uint8_t *a = left;
    const uint8_t *b = right;

    for (size_t index = 0U; index < count; ++index) {
        if (a[index] != b[index]) {
            return (a[index] < b[index]) ? -1 : 1;
        }
    }
    return 0;
}

size_t strlen(const char *text)
{
    size_t length = 0U;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

int strcmp(const char *left, const char *right)
{
    while (*left != '\0' && *left == *right) {
        ++left;
        ++right;
    }
    return (unsigned char)*left - (unsigned char)*right;
}

int strncmp(const char *left, const char *right, size_t count)
{
    for (size_t index = 0U; index < count; ++index) {
        const unsigned char a = (unsigned char)left[index];
        const unsigned char b = (unsigned char)right[index];
        if (a != b || a == '\0') {
            return (int)a - (int)b;
        }
    }
    return 0;
}

char *strcpy(char *destination, const char *source)
{
    char *result = destination;
    while ((*destination++ = *source++) != '\0') {
    }
    return result;
}

char *strncpy(char *destination, const char *source, size_t count)
{
    size_t index = 0U;
    for (; index < count && source[index] != '\0'; ++index) {
        destination[index] = source[index];
    }
    for (; index < count; ++index) {
        destination[index] = '\0';
    }
    return destination;
}
