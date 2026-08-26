#define CORE_MAP_EXPORTS
#include "core_map.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BLAZE_LM 33
#define COCO_LM 17
#define STRIDE 4
#define VIS_BBOX 0.1f
#define VIS_PERSON 0.25f

static const int kBlazeToCoco[COCO_LM] = {
    0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28};

static const char *kCocoNames[COCO_LM] = {
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
};

typedef struct Buf {
    char *data;
    size_t len;
    size_t cap;
} Buf;

static int buf_grow(Buf *b, size_t need) {
    if (b->len + need + 1 <= b->cap) {
        return 1;
    }
    size_t cap = b->cap ? b->cap : 256;
    while (b->len + need + 1 > cap) {
        cap *= 2;
    }
    char *p = (char *)realloc(b->data, cap);
    if (!p) {
        return 0;
    }
    b->data = p;
    b->cap = cap;
    return 1;
}

static int buf_puts(Buf *b, const char *s) {
    size_t n = strlen(s);
    if (!buf_grow(b, n)) {
        return 0;
    }
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = 0;
    return 1;
}

static int buf_puti(Buf *b, int v) {
    char tmp[32];
    int n = snprintf(tmp, sizeof(tmp), "%d", v);
    if (n < 0) {
        return 0;
    }
    return buf_puts(b, tmp);
}

static int buf_putf(Buf *b, double v) {
    char tmp[64];
    int n = snprintf(tmp, sizeof(tmp), "%.7g", v);
    if (n < 0) {
        return 0;
    }
    return buf_puts(b, tmp);
}

static float clampf(float v, float lo, float hi) {
    if (v < lo) {
        return lo;
    }
    if (v > hi) {
        return hi;
    }
    return v;
}

static char *json_error(int width, int height, float latency_ms, const char *device,
                        const char *code, const char *message) {
    Buf b = {0};
    int w = width >= 1 ? width : 1;
    int h = height >= 1 ? height : 1;
    const char *dev = device && device[0] ? device : "cpu";
    if (!buf_puts(&b,
                  "{\"schema_version\":\"0.1.0\",\"frame\":{"
                  "\"source_kind\":\"image\",\"timestamp_ms\":0,"
                  "\"width\":")) {
        free(b.data);
        return NULL;
    }
    if (!buf_puti(&b, w) || !buf_puts(&b, ",\"height\":") || !buf_puti(&b, h) ||
        !buf_puts(&b, ",\"camera_intrinsics\":null},\"detections\":[],\"poses\":[],"
                      "\"tracks\":[],\"classifications\":[],\"segments\":[],"
                      "\"model_meta\":{\"backend_id\":\"mediapipe_pose\","
                      "\"model_name\":\"pose_landmarker_full.task\",\"latency_ms\":") ||
        !buf_putf(&b, (double)latency_ms) || !buf_puts(&b, ",\"device\":\"") ||
        !buf_puts(&b, dev) ||
        !buf_puts(&b, "\"},\"error\":{\"code\":\"") || !buf_puts(&b, code) ||
        !buf_puts(&b, "\",\"message\":\"") || !buf_puts(&b, message) ||
        !buf_puts(&b, "\"}}")) {
        free(b.data);
        return NULL;
    }
    return b.data;
}

char *core_map_from_blaze33(const float *xyz_vis, int num_people, int width, int height,
                            float latency_ms, const char *device) {
    const char *dev = device && device[0] ? device : "cpu";
    if (width < 1 || height < 1 || num_people < 0 || (num_people > 0 && xyz_vis == NULL)) {
        return json_error(width, height, latency_ms, dev, "INVALID_INPUT",
                          "expected width,height >= 1 and a blaze33 buffer");
    }
    if (num_people == 0) {
        return json_error(width, height, latency_ms, dev, "NO_PERSON", "no detections");
    }

    typedef struct Person {
        float bbox[4];
        float conf;
        float kpx[COCO_LM];
        float kpy[COCO_LM];
        float kpz[COCO_LM];
        float kpc[COCO_LM];
        int keep;
    } Person;

    Person *people = (Person *)calloc((size_t)num_people, sizeof(Person));
    if (!people) {
        return json_error(width, height, latency_ms, dev, "INVALID_INPUT", "out of memory");
    }

    int kept = 0;
    int any_low = 0;
    for (int p = 0; p < num_people; p++) {
        const float *base = xyz_vis + (size_t)p * BLAZE_LM * STRIDE;
        float vis_sum = 0.f;
        float xmin = (float)width;
        float ymin = (float)height;
        float xmax = 0.f;
        float ymax = 0.f;
        int boxed = 0;
        for (int c = 0; c < COCO_LM; c++) {
            int bi = kBlazeToCoco[c];
            float x = base[bi * STRIDE + 0];
            float y = base[bi * STRIDE + 1];
            float z = base[bi * STRIDE + 2];
            float v = clampf(base[bi * STRIDE + 3], 0.f, 1.f);
            people[p].kpx[c] = x;
            people[p].kpy[c] = y;
            people[p].kpz[c] = z;
            people[p].kpc[c] = v;
            vis_sum += v;
            if (v >= VIS_BBOX) {
                if (x < xmin) xmin = x;
                if (y < ymin) ymin = y;
                if (x > xmax) xmax = x;
                if (y > ymax) ymax = y;
                boxed = 1;
            }
        }
        float mean_v = vis_sum / (float)COCO_LM;
        people[p].conf = mean_v;
        if (mean_v < VIS_PERSON || !boxed) {
            people[p].keep = 0;
            any_low = 1;
            continue;
        }
        people[p].keep = 1;
        people[p].bbox[0] = clampf(xmin, 0.f, (float)width);
        people[p].bbox[1] = clampf(ymin, 0.f, (float)height);
        people[p].bbox[2] = clampf(xmax, 0.f, (float)width);
        people[p].bbox[3] = clampf(ymax, 0.f, (float)height);
        kept++;
    }

    if (kept == 0) {
        free(people);
        return json_error(width, height, latency_ms, dev,
                          any_low ? "LOW_CONFIDENCE" : "NO_PERSON",
                          any_low ? "all detections below vis threshold 0.25"
                                  : "no detections");
    }

    Buf b = {0};
    if (!buf_puts(&b,
                  "{\"schema_version\":\"0.1.0\",\"frame\":{"
                  "\"source_kind\":\"image\",\"timestamp_ms\":0,\"width\":") ||
        !buf_puti(&b, width) || !buf_puts(&b, ",\"height\":") ||
        !buf_puti(&b, height) ||
        !buf_puts(&b, ",\"camera_intrinsics\":null},\"detections\":[")) {
        free(people);
        free(b.data);
        return NULL;
    }

    int first = 1;
    int det_index = 0;
    for (int p = 0; p < num_people; p++) {
        if (!people[p].keep) {
            continue;
        }
        if (!first && !buf_puts(&b, ",")) {
            free(people);
            free(b.data);
            return NULL;
        }
        first = 0;
        if (!buf_puts(&b, "{\"class_name\":\"person\",\"confidence\":") ||
            !buf_putf(&b, (double)people[p].conf) || !buf_puts(&b, ",\"bbox_xyxy\":[") ||
            !buf_putf(&b, (double)people[p].bbox[0]) || !buf_puts(&b, ",") ||
            !buf_putf(&b, (double)people[p].bbox[1]) || !buf_puts(&b, ",") ||
            !buf_putf(&b, (double)people[p].bbox[2]) || !buf_puts(&b, ",") ||
            !buf_putf(&b, (double)people[p].bbox[3]) ||
            !buf_puts(&b, "],\"track_id\":null}")) {
            free(people);
            free(b.data);
            return NULL;
        }
        det_index++;
    }

    if (!buf_puts(&b, "],\"poses\":[")) {
        free(people);
        free(b.data);
        return NULL;
    }
    first = 1;
    det_index = 0;
    for (int p = 0; p < num_people; p++) {
        if (!people[p].keep) {
            continue;
        }
        if (!first && !buf_puts(&b, ",")) {
            free(people);
            free(b.data);
            return NULL;
        }
        first = 0;
        if (!buf_puts(&b, "{\"skeleton\":\"coco_17\",\"keypoints\":[")) {
            free(people);
            free(b.data);
            return NULL;
        }
        for (int c = 0; c < COCO_LM; c++) {
            if (c && !buf_puts(&b, ",")) {
                free(people);
                free(b.data);
                return NULL;
            }
            if (!buf_puts(&b, "{\"name\":\"") || !buf_puts(&b, kCocoNames[c]) ||
                !buf_puts(&b, "\",\"x\":") || !buf_putf(&b, (double)people[p].kpx[c]) ||
                !buf_puts(&b, ",\"y\":") || !buf_putf(&b, (double)people[p].kpy[c]) ||
                !buf_puts(&b, ",\"z\":") || !buf_putf(&b, (double)people[p].kpz[c]) ||
                !buf_puts(&b, ",\"confidence\":") ||
                !buf_putf(&b, (double)people[p].kpc[c]) || !buf_puts(&b, "}")) {
                free(people);
                free(b.data);
                return NULL;
            }
        }
        if (!buf_puts(&b, "],\"score\":") || !buf_putf(&b, (double)people[p].conf) ||
            !buf_puts(&b, ",\"detection_index\":") || !buf_puti(&b, det_index) ||
            !buf_puts(&b, "}")) {
            free(people);
            free(b.data);
            return NULL;
        }
        det_index++;
    }

    if (!buf_puts(&b, "],\"tracks\":[],\"classifications\":[],\"segments\":[],"
                      "\"model_meta\":{\"backend_id\":\"mediapipe_pose\","
                      "\"model_name\":\"pose_landmarker_full.task\",\"latency_ms\":") ||
        !buf_putf(&b, (double)latency_ms) || !buf_puts(&b, ",\"device\":\"") ||
        !buf_puts(&b, dev) || !buf_puts(&b, "\"},\"error\":null}")) {
        free(people);
        free(b.data);
        return NULL;
    }
    free(people);
    return b.data;
}

void core_map_free(char *json) { free(json); }
