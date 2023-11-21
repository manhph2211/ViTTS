import re
import os
import json
import argparse
from string import punctuation
import torch
import numpy as np
from torch.utils.data import DataLoader
from src.utils.lexicon.g2p.g2p import G2P
from src.utils.models.model_utils import get_model, get_vocoder
from src.utils.utils import get_configs_of, to_device, synth_samples
from src.datasets import TextDataset
from src.utils.text import text_to_sequence


def read_lexicon(lex_path):
    lexicon = {}
    with open(lex_path) as f:
        for line in f:
            temp = re.split(r"\s+", line.strip("\n"))
            word = temp[0]
            phones = temp[1:]
            if word.lower() not in lexicon:
                lexicon[word.lower()] = phones
    return lexicon


def word_level_subdivision(phones_per_word, max_phoneme_num):
    res = []
    for l in phones_per_word:
        if l <= max_phoneme_num:
            res.append(l)
        else:
            s, r = l//max_phoneme_num, l % max_phoneme_num
            res += [max_phoneme_num]*s + ([r] if r else [])
    return res


def preprocess_vietnamese(text, preprocess_config):
    text = text.rstrip(punctuation)
    lexicon = read_lexicon(preprocess_config["path"]["lexicon_path"])
    phones = []
    word_boundaries = []
    g2p = G2P()
    # text = text.replace("."," . ")
    # text = text.replace(","," , ")
    words = re.split(" ", text)
    for w in words:
        if w.lower() in lexicon:
            phone_list = lexicon[w.lower()]
        elif w==',' or w=='.':
            phone_list = ['spn']
        else:
            phone_list = list(filter(lambda p: p != " ", g2p(w)))
        if phone_list:
            phones += phone_list
            word_boundaries.append(len(phone_list))
#    phones += ['spn']
#    word_boundaries.append(1)
    phones = "{" + "}{".join(phones) + "}"
    phones = re.sub(r"\{[^\w\s]?\}", "{spn}", phones)
    phones = phones.replace("}{", " ")
    if preprocess_config["preprocessing"]["text"]["sub_divide_word"]:
        word_boundaries = word_level_subdivision(
            word_boundaries, preprocess_config["preprocessing"]["text"]["max_phoneme_num"])
    print("Raw Text Sequence: {}".format(text))
    print("Phoneme Sequence: {}".format(phones))

    sequence = np.array(text_to_sequence(
        phones, preprocess_config["preprocessing"]["text"]["text_cleaners"]))
    return np.array(sequence), np.array(word_boundaries)


def synthesize(device, model, args, configs, vocoder, batchs, duration_control):
    preprocess_config, model_config, train_config = configs

    for batch in batchs:
        batch = to_device(batch, device)
        with torch.no_grad():
            # Forward
            output = model(
                *batch[2:],
                d_control=duration_control,
            )
            synth_samples(
                batch,
                output,
                vocoder,
                model_config,
                preprocess_config,
                train_config["path"]["result_path"],
                args,
            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--restore_step", type=int, required=True)
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "single"],
        required=False,
        default="single",
        help="Synthesize a whole dataset or a single sentence",
    )
    parser.add_argument("--model_type", type=str, default='base')
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="path to a source file with format like train.txt and val.txt, for batch mode only",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="raw text to synthesize, for single-sentence mode only",
    )
    parser.add_argument(
        "--speaker_id",
        type=str,
        default="0",
        help="speaker ID for multi-speaker synthesis, for single-sentence mode only",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="Article",
        help="name of dataset",
    )
    parser.add_argument(
        "--duration_control",
        type=float,
        default=1.0,
        help="control the speed of the whole utterance, larger value for slower speaking rate",
    )
    args = parser.parse_args()

    # Check source texts
    if args.mode == "batch":
        assert args.source is not None and args.text is None
    if args.mode == "single":
        assert args.source is None and args.text is not None

    # Read Config
    preprocess_config, model_config, train_config = get_configs_of(os.path.join(args.model_type,args.dataset))
    configs = (preprocess_config, model_config, train_config)
    os.makedirs(
        os.path.join(train_config["path"]["result_path"], str(args.restore_step)), exist_ok=True)

    # Set Device
    torch.manual_seed(train_config["seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed(train_config["seed"])
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')
    print("Device of PortaSpeech:", device)

    # Get model
    model = get_model(args, configs, device, train=False)

    # Load vocoder
    vocoder = get_vocoder(model_config, device)

    # Preprocess texts
    if args.mode == "batch":
        # Get dataset
        dataset = TextDataset(args.source, preprocess_config, model_config)
        batchs = DataLoader(
            dataset,
            batch_size=64,
            collate_fn=dataset.collate_fn,
        )
    if args.mode == "single":
        ids = raw_texts = [args.text[:100]]

        # Speaker Info
        load_spker_embed = model_config["multi_speaker"] \
            and preprocess_config["preprocessing"]["speaker_embedder"] != 'none'
        with open(os.path.join(preprocess_config["path"]["preprocessed_path"], "speakers.json")) as f:
            speaker_map = json.load(f)
        speakers = np.array([speaker_map[args.speaker_id]]) if model_config["multi_speaker"] else np.array(
            [0])  # single speaker is allocated 0
        spker_embed = np.load(os.path.join(
            preprocess_config["path"]["preprocessed_path"],
            "spker_embed",
            "{}-spker_embed.npy".format(args.speaker_id),
        )) if load_spker_embed else None

        if preprocess_config["preprocessing"]["text"]["language"] == "vi":
            texts, word_boundaries = preprocess_vietnamese(
                args.text, preprocess_config)
            texts, word_boundaries = np.array(
                [texts]), np.array([word_boundaries])
        else:
            raise NotImplementedError
        text_lens = np.array([len(texts[0])])
        text_w_lens = np.array([len(word_boundaries[0])])
        batchs = [(ids, raw_texts, speakers, texts,
                   text_lens, max(text_lens), word_boundaries, text_w_lens, max(text_w_lens), spker_embed)]
    synthesize(device, model, args, configs, vocoder,
               batchs, args.duration_control)
