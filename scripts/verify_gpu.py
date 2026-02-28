import sys

import torch


def main():
    print(f"torch_version={torch.__version__}")
    print(f"cuda_built={torch.backends.cuda.is_built()}")
    print(f"cuda_version={torch.version.cuda}")
    print(f"cuda_available={torch.cuda.is_available()}")
    print(f"device_count={torch.cuda.device_count()}")

    if not torch.backends.cuda.is_built():
        print("ERROR: PyTorch is not built with CUDA support.", file=sys.stderr)
        return 1

    if not torch.cuda.is_available():
        print("ERROR: CUDA runtime is not available in the container.", file=sys.stderr)
        return 2

    if torch.cuda.device_count() <= 0:
        print("ERROR: No visible CUDA devices.", file=sys.stderr)
        return 3

    print(f"gpu_name={torch.cuda.get_device_name(0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
