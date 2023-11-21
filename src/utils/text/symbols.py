'''
# English custom
from src.utils.text import cmudict, pinyin

_pad = "_"
_punctuation = "!'(),.:;? "
_special = "-"
_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_silences = ["@sp", "@spn", "@sil"]

# Prepend "@" to ARPAbet symbols to ensure uniqueness (some are the same as uppercase letters):
_arpabet = ["@" + s for s in cmudict.valid_symbols]
_pinyin = ["@" + s for s in pinyin.valid_symbols]

# Export all symbols:
symbols = (
    [_pad]
    + list(_special)
    + list(_punctuation)
    + list(_letters)
    + _arpabet
    + _pinyin
    + _silences
)
'''
from src.utils.lexicon.g2p.g2p import *
# Vietnamese Customs
initial_ph = list(initial_consonants.values())
final_ph = list(final_consonants.values())
vowel_ph = list(vowels.values())
ph = initial_ph + final_ph + vowel_ph + [x.replace("_0","") for x in vowel_ph]
for special in list(specials.values()):
    for p in special.split(" "):
        ph.append(p)
ph = ['z', '7_1', 'i', 'N', 'w', 'a_1', 'a_0', 'd', 'a_3', 'spn', 'u_4', 'p', 'J', 'i@_1', 'u', 'h', 'o_5', 'n', 'u@_0', 'a_2', 'm', 't_h', 'i@_2', 'u_2', 'O_0', 't', 'o_0', 'kp', 'k', 'N_+', 'M_1', 'O_4', 'f', 'u_5', 'o_1', 'a_4', 'v', 'u_1', 'Nm', 'b', 'O_2', 'a_X_5', 'E_4', 'i@_5', 'a_5', 'O', 'l', 'a_X_0', 'u_0', '7_X_5', 'ts\\', 'M@_1', '7_X_0', 'x', 'i_4', 'i_1', 'e_0', 'i_0', 'a_X_1', 'M_5', '7_X_4', 'G', 'a_X_4', 'u@_2', 'i@_0', 'o_4', '7_X_2', 'u_3', 'i@_4', 's', 'E_3', 'e_5', 'u@_4', 'e_4', 'i@_3', '7_0', 'E_0', 'M@_5', 'M_0', 'i_2', '7_X_1', 'o_2', 'e_2', 'M_3', 'u@_5', 'M@_0', '7_2', 'k_+', 'O_5', 'e_1', 'M@_2', 'O_1', 'i_5', 'M@_3', 'M_2', '7_4', '7_X_3', 'M@_4', 'O_X_4', 'M_4', 'a_X_2', 'o_3', '7_5', 'E_2', 'E_5', 'e_3', 'O_3', 'kp_5', 'kp_4', 'a_X_3', 'u@_1', 'E', '7_3', 'E_1', 'i_3', 'a', 'zi', 'u@_3', '7']
#ph = ["@"+s for s in ph]
punctuations  = ['.', '?', '"', '\'', ',', '-', '–', '!', ':', ';', '(', ')', '[', ']', '\n',' ']
_pad        = ['_']
_specials = ["-"]
_silences = ["@sp", "@spn", "@sil","@<silent>"]
_s = ["@<s>" , "@</s>"]

# Export all symbols:
symbols = set(_pad + _specials +  _silences + ph + _s)
symbols=('@zi','@kp_4','@kp_5','@o_1', '@e_3', '@u_5', '@i@_2', '@G', '@u@_3', '@e_2', '@o_0', '@M_2', '@x', '@m', '@7_0', '@t', '@Nm', '@p', '@o', '@e_1', '@k_+', '@a_1', '@O_X_4', '_', '@a_X_4', '@k', '@b', '@i_1', '@7_X_1', '@i_0', '@J', '@O_2', '@u@_4', '@a_X_3', '@u@_1', '@e_4', '@M@_4', '@7_X_3', '@h', '@u_4', '@i_5', '@M@_0', '@o_5', '@M_1', '@e', '@z', '@u@_2', '@7', '@e_0', '@i@_0', '@a_0', '@N', '@a_5', '@N_+', '@M_3', '@M_0', '@E_0', '@O_4', '-', '@o_4', '@7_1', '@i_2', '@M_5', '@M@_2', '@i@_5', '@7_5', '@o_3', '@a_4', '@u@_0', '@O_3', '@a_X', '@n', '@M_4', '@O_1', '@M@', '@kp', '@i@', '@u', '@E_1', '@o_2', '@e_5', '@7_X_2', '@7_X', '@a_X_2', '@i@_3', '@7_X_5', '@i@_1', '@E', '@i_4', '@E_5', '@v', '@u_0', '@i@_4', '@7_X_0', '@u_1', '@7_X_4', '@ts\\', '@a_X_0', '@7_3', '@i_3', '@M@_5', '@7_4', '@O_0', '@spn', '@O_5', '@E_4', '@O', '@u_3', '@E_2', '@a_3', '@sil', '@M@_3', '@a_2', '@sp', '@a', '@M', '@t_h', '@7_2', '@M@_1', '@u@', '@f', '@s', '@i', '@a_X_1', '@u_2', '@a_X_5', '@u@_5', '@d', '@E_3', '@l', '@w')
