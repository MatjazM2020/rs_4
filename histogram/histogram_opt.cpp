#include <hip/hip_runtime.h>
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include <stdio.h>
#include <stdlib.h>

#define NUM_BINS 256
#define BLOCK_SIZE 1024

#define HIP_CHECK(cmd)                                                    \
    do {                                                                  \
        hipError_t _e = (cmd);                                            \
        if (_e != hipSuccess) {                                           \
            fprintf(stderr, "HIP error at %s:%d  \"%s\"\n",              \
                    __FILE__, __LINE__, hipGetErrorString(_e));           \
            exit(EXIT_FAILURE);                                           \
        }                                                                 \
    } while (0)

static unsigned char *load_image(int argc, char **argv,
                                 int *width, int *height, int *channels)
{
    const char *paths[] = {
        argc > 1 ? argv[1] : NULL,
        "./histogram/lena_gray.bmp",
        "../histogram/lena_gray.bmp",
        "./lena_gray.bmp",
    };

    for (unsigned i = 0; i < sizeof(paths) / sizeof(paths[0]); i++) {
        if (!paths[i]) continue;
        unsigned char *img = stbi_load(paths[i], width, height, channels, 1);
        if (img) {
            printf("Loaded image %s (%dx%d)\n", paths[i], *width, *height);
            return img;
        }
    }

    fprintf(stderr, "Failed to load lena_gray.bmp\n");
    return NULL;
}


__global__ void histogram_optimized(const unsigned char *image, int *hist, int size) {
    __shared__ int local_hist[NUM_BINS];
    
    // Initialize shared memory
    int t = threadIdx.x;
    if (t < NUM_BINS) local_hist[t] = 0;
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        atomicAdd(&local_hist[image[idx]], 1);
    }
    __syncthreads();

    // Merge local histograms into global memory
    if (t < NUM_BINS) {
        atomicAdd(&hist[t], local_hist[t]);
    }
}

int main(int argc, char **argv) {

    int width, height, channels;
    unsigned char *h_img = load_image(argc, argv, &width, &height, &channels);
    
    if (!h_img) {
        return 1;
    }

    int img_size = width * height;

    // Allocate device memory
    unsigned char *d_img;
    int *d_hist;
    HIP_CHECK(hipMalloc(&d_img, img_size));
    HIP_CHECK(hipMalloc(&d_hist, NUM_BINS * sizeof(int)));

    // Initialize histogram to zero
    HIP_CHECK(hipMemset(d_hist, 0, NUM_BINS * sizeof(int)));

    // Copy image to device
    HIP_CHECK(hipMemcpy(d_img, h_img, img_size, hipMemcpyHostToDevice));

    // Kernel launch parameters
    int threads = BLOCK_SIZE;
    int blocks = (img_size + threads - 1) / threads;


    // --- OPTIMIZED HISTOGRAM ---
    HIP_CHECK(hipMemset(d_hist, 0, NUM_BINS * sizeof(int)));
    hipLaunchKernelGGL(histogram_optimized, dim3(blocks), dim3(threads), 0, 0, d_img, d_hist, img_size);
    HIP_CHECK(hipDeviceSynchronize());

    int h_hist_opt[NUM_BINS];
    HIP_CHECK(hipMemcpy(h_hist_opt, d_hist, NUM_BINS * sizeof(int), hipMemcpyDeviceToHost));

    printf("Optimized histogram computed.\n");

    // Compare or print histograms
    for (int i = 0; i < NUM_BINS; ++i) {
        printf("Bin %3d: optimized = %6d\n", i, h_hist_opt[i]);
    }

    // Cleanup
    stbi_image_free(h_img);
    HIP_CHECK(hipFree(d_img));
    HIP_CHECK(hipFree(d_hist));

    return 0;
}
