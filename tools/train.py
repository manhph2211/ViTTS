import argparse
from ast import arg
import torch
import torch.multiprocessing as mp
from src.utils.utils import get_configs_of
from src.engine.trainer import train
import os
torch.backends.cudnn.benchmark = True


def main():
    assert torch.cuda.is_available(), "CPU training is not allowed."
    parser = argparse.ArgumentParser()
    parser.add_argument('--use_amp', action='store_true')
    parser.add_argument("--restore_step", type=int, default=0)
    parser.add_argument(
        "--dataset",
        type=str,
        # required=True,
        default='Article',
        help="name of dataset",
    )
    parser.add_argument("--model_type", type=str, default='base')

    args = parser.parse_args()

    # Read Config
    preprocess_config, model_config, train_config = get_configs_of(os.path.join(args.model_type,args.dataset))
    configs = (preprocess_config, model_config, train_config)

    # Set Device
    torch.manual_seed(train_config["seed"])
    torch.cuda.manual_seed(train_config["seed"])
    num_gpus = torch.cuda.device_count()
    batch_size = int(train_config["optimizer"]["batch_size"] / num_gpus)
    helper_type = train_config["aligner"]["helper_type"]

    # Log Configuration
    print("\n==================================== Training Configuration ====================================")
    print(' ---> Automatic Mixed Precision:', args.use_amp)
    print(' ---> Number of used GPU:', num_gpus)
    print(' ---> Batch size per GPU:', batch_size)
    print(' ---> Batch size in total:', batch_size * num_gpus)
    print(' ---> Type of alignment helper:', helper_type)
    print("=================================================================================================")
    print("Prepare training ...")

    if num_gpus > 1:
        mp.spawn(train, nprocs=num_gpus, args=(
            args, configs, batch_size, num_gpus))
    else:
        train(0, args, configs, batch_size, num_gpus)


if __name__ == "__main__":
    main()
