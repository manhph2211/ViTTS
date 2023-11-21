from src.utils.lexicon.g2p.g2p import G2P
from src.utils.text.cleaners import basic_cleaners


def prepare_test_set(in_file='src/evaluation/MOSNet/data/OutDomainTestData.txt'):
    new_lines=''
    with open(in_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            text = basic_cleaners(line.split('|')[-1][-1])
            pass
