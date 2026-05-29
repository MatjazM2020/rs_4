#!/bin/bash
GEM5_WORKSPACE=/d/hpc/projects/FRI/GEM5/gem5_workspace
GEM5_ROOT=$GEM5_WORKSPACE/gem5
GEM5_PATH=$GEM5_ROOT/build/VEGA_X86
APPTAINER_IMG=$GEM5_WORKSPACE/gcn-gpu_v24-0.sif

for CU in 2 4 8; do
    srun --ntasks=1 --time=02:00:00 --output=log_cu${CU}.txt --reservation=fri \
        apptainer exec $APPTAINER_IMG \
        $GEM5_PATH/gem5.opt --outdir=results/cu_${CU} \
        $GEM5_ROOT/configs/example/apu_se.py \
        --cpu-type=X86TimingSimpleCPU \
        --num-cpus=1 \
        --mem-size=8GB \
        --mem-type=HBM_1000_4H_1x64 \
        --num-compute-units=$CU \
        -n 3 \
        --benchmark-root=/d/hpc/home/jm1540/RS/rs_4/mat_transpose/bin/ \
        --cmd=mat_transpose.bin &
done

wait
echo "All done"