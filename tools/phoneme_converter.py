import argparse
from src.utils.utils import get_configs_of
from src.utils.lexicon.get_phoneme import get_phoneme


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=str,
        # required=True,
        default='Article',
        help="name of dataset",
    )
    args = parser.parse_args()
    config, *_ = get_configs_of(args.dataset)
    get_phoneme(config)
