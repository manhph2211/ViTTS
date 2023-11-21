import argparse
from src.utils.utils import get_configs_of
from src.utils.preprocessor.preprocessor import Preprocessor


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=str,
        # required=True,
        default= "Article",
        help="name of dataset",
    )
    args = parser.parse_args()

    preprocess_config, model_config, train_config = get_configs_of(
        args.dataset)
    preprocessor = Preprocessor(preprocess_config, model_config, train_config)
    preprocessor.build_from_path()
