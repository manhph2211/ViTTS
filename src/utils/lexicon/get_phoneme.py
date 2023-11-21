from src.utils.lexicon.g2p.g2p import G2P
from src.utils.utils import get_all_text
from src.utils.text import _clean_text, punctuations
import os
import glob


def make_line(text, g2p):
    phoneme = g2p(text.strip())
    return text + '\t' + phoneme.strip() + '\n'


def get_phoneme(config):
    g2p = G2P()
    csv_files = glob.glob(os.path.join(config['path']['corpus_path'],"*/*.csv"))
    with open(config['path']['lexicon_path'], 'w') as f:
        for csv_file in csv_files:
            texts = get_all_text(csv_file)
            for text in texts:
                text = _clean_text(text,config["preprocessing"]["text"]["text_cleaners"])
                for token in text.split(' ')[:-1]:
                    if token in punctuations:
                        continue
                    line = make_line(token,g2p)
                    f.write(line)

    print("Done!!")


def check_all_phonemes(file="data/preprocessed_data/val.txt"):
    phonemes = []
    with open(file,'r') as f:
        data = f.readlines()
        for line in data:
            line = line[:-1].split("|")[-2].replace("{","").replace("}","").split(" ")
            for phone in line:
                if phone not in phonemes:
                    phonemes.append(phone)
    with open(file.replace("val","train"),'r') as f:
        data = f.readlines()
        for line in data:
            line = line[:-1].split("|")[-2].replace("{","").replace("}","").split(" ")
            for phone in line:
                if phone not in phonemes:
                    phonemes.append(phone)
    
    print(phonemes)

def test(file_in, file_out=None):
    new_data = ''
    g2p = G2P()
    with open(file_in, 'r') as f:
        data = f.readlines()
        for word in data:
            line = make_line(word[:-1], g2p)
            new_data+=line
    with open(file_out, 'w') as f:
        f.write(new_data)


if __name__ == "__main__":
    # test('/home/max/coding/portaspeech/src/utils/lexicon/g2p/vietnamese_words.txt','/home/max/coding/portaspeech/src/utils/lexicon/g2p/out.txt')
    check_all_phonemes()
