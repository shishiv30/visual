#ifndef CORE_MAP_H
#define CORE_MAP_H

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WIN32
#ifdef CORE_MAP_EXPORTS
#define CORE_MAP_API __declspec(dllexport)
#else
#define CORE_MAP_API __declspec(dllimport)
#endif
#else
#define CORE_MAP_API __attribute__((visibility("default")))
#endif

/* xyz_vis: num_people * 33 * 4 floats (x, y, z, visibility) in pixel space.
   Returns heap JSON (CoreInferenceResult v0). Caller must core_map_free().
   On invalid args still returns a JSON document with error INVALID_INPUT. */
CORE_MAP_API char *core_map_from_blaze33(
    const float *xyz_vis,
    int num_people,
    int width,
    int height,
    float latency_ms,
    const char *device);

CORE_MAP_API void core_map_free(char *json);

#ifdef __cplusplus
}
#endif

#endif
