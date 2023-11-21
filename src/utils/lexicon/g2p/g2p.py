from regex import F
from src.utils.lexicon.g2p.rules import *
import re


class G2P:
    def __init__(self):
        self.initial_consonants = self.sort_dict_by_key_len(initial_consonants)
        self.vowels = self.sort_dict_by_key_len(vowels)
        self.final_consonants = self.sort_dict_by_key_len(final_consonants)
        self.specials = self.sort_dict_by_key_len(specials)

    def sort_dict_by_key_len(self, d):
        new_d = {}
        for k in sorted(d, key=len, reverse=True):
            new_d[k] = d[k]
        return new_d

    def handle_initial(self):
        ph = ""
        for gra in self.initial_consonants:
            if self.word.startswith(gra):
                self.track = len(gra)
                ph = self.initial_consonants[gra]
                if gra == 'gi':
                    if (self.track >= len(self.word)) or (self.track < len(self.word) and self.word[self.track] in 'ê ế ể ệ ễ ề'.split()):
                        ph = 'zi'
                break 
        self.phonemes.append(ph)

    def handle_medial(self):
        if self.track < len(self.word)-1:
            if self.word[self.track] == 'u' and self.word[:self.track] not in ['b','m','ph'] and self.word[self.track+1] in "y ý ỷ ỳ ỹ ỵ e é è ẻ ẹ ẽ ê ế ề ể ễ ệ".split():
                ph = 'w'
                self.track+=1
                self.phonemes.append(ph)

            if self.word[self.track] == 'o' and self.word[self.track+1] in "a á ả ã à ạ ẵ ắ ằ ẳ ặ ă e é è ẻ ẹ ẽ ê ế ề ể ễ ệ".split():
                ph = 'w'
                self.track+=1
                self.phonemes.append(ph)

    def handle_specials(self):
        for spec in self.specials:
            if self.word[self.track:] == spec:
                ph = self.specials[spec]
                self.track += len(spec)
                self.phonemes+=ph.split(" ")
                # assert len(self.word) == self.track, f'Problems dealing with {self.word}'
                break

    def handle_vowels(self):
        ph = []
        while self.track < len(self.word) and self.word[self.track] in self.vowels:
            for vowel in self.vowels:
                if self.word[self.track:].startswith(vowel):
                    ph.append(self.vowels[vowel])
                    self.track+=len(vowel)
        ph = ' '.join(ph)
        self.phonemes.append(ph)

    def handle_final(self):
        for final in self.final_consonants:
            if self.word[self.track:].startswith(final):
                ph = self.final_consonants[final]
                self.track += len(final)
                self.phonemes.append(ph)
                break      
        # assert len(self.word) == self.track, f'Problems dealing with {self.word}'

    def handle_tone(self, phonemes):
        phonemes = " ".join(phonemes)
        tone_count = len(re.findall("_[0-9]",phonemes))
        O_count = len(re.findall("_0",phonemes))
        if tone_count == 1:
            return phonemes
        if O_count != tone_count:
            phonemes = re.sub("_0","",phonemes)
        elif O_count>=2:
            if O_count ==2 and phonemes[-1].isnumeric():
                phonemes = re.sub("0_","",phonemes[::-1],1)[::-1]
            elif O_count ==2 and not phonemes[-1].isnumeric():
                phonemes = re.sub("_0","",phonemes,1)
            if O_count==3:
                phonemes = re.sub("_0","",phonemes,1)

        return phonemes

    def g2p(self, word):
        self.word = word
        self.phonemes = []
        self.track = 0
        self.handle_initial()
        self.handle_medial()
        self.handle_specials()
        self.handle_vowels()
        self.handle_final()

    def __call__(self, word, all_tones = False):
        self.g2p(word)
        return self.phonemes if all_tones else self.handle_tone(self.phonemes) 


if __name__ == "__main__":
    text  = "nhỉ nhật ak buâng muốn ngoài quấn cuốn buông quắc mua tiên khuyu qua cua giao giết dết nghiêng hoa ngoan meo"
    g2p = G2P()
    for word in text.split():
        print(g2p(word),": ",  word)
