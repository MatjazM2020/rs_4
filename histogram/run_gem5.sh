#!/bin/bash

if [[ -n "${SLURM_SUBMIT_DIR:-}" && -d "$SLURM_SUBMIT_DIR/histogram" ]]; then
    SCRIPT_DIR=$SLURM_SUBMIT_DIR/histogram
elif [[ -n "${SLURM_SUBMIT_DIR:-}" && -f "$SLURM_SUBMIT_DIR/histogram_naive.cpp" ]]; then
    SCRIPT_DIR=$SLURM_SUBMIT_DIR
else
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
fi
cd "$SCRIPT_DIR"

GEM5_WORKSPACE=/d/hpc/projects/FRI/GEM5/gem5_workspace
GEM5_ROOT=$GEM5_WORKSPACE/gem5
GEM5_PATH=$GEM5_ROOT/build/VEGA_X86
APPTAINER_IMG=$GEM5_WORKSPACE/gcn-gpu_v24-0.sif

BIN_ROOT=$SCRIPT_DIR/bin

if [[ ! -f "$BIN_ROOT/histogram_naive.bin" || ! -f "$BIN_ROOT/histogram_opt.bin" ]]; then
    echo "Missing histogram binaries. Run ./make_apptainer.sh before this script." >&2
    exit 1
fi

mkdir -p results/naive results/optimized

for CU in 2 4 8; do
    srun --ntasks=1 --time=02:00:00 --output=log_naive_cu${CU}.txt --reservation=fri \
        apptainer exec $APPTAINER_IMG \
        $GEM5_PATH/gem5.opt --outdir=results/naive/cu_${CU} \
        $GEM5_ROOT/configs/example/apu_se.py \
        --cpu-type=X86TimingSimpleCPU \
        --num-cpus=1 \
        --mem-size=8GB \
        --mem-type=HBM_1000_4H_1x64 \
        --num-compute-units=$CU \
        -n 3 \
        --benchmark-root=$BIN_ROOT/ \
        --cmd=histogram_naive.bin &

    srun --ntasks=1 --time=02:00:00 --output=log_optimized_cu${CU}.txt --reservation=fri \
        apptainer exec $APPTAINER_IMG \
        $GEM5_PATH/gem5.opt --outdir=results/optimized/cu_${CU} \
        $GEM5_ROOT/configs/example/apu_se.py \
        --cpu-type=X86TimingSimpleCPU \
        --num-cpus=1 \
        --mem-size=8GB \
        --mem-type=HBM_1000_4H_1x64 \
        --num-compute-units=$CU \
        -n 3 \
        --benchmark-root=$BIN_ROOT/ \
        --cmd=histogram_opt.bin &
done

wait
echo "All histogram GEM5 runs done"
