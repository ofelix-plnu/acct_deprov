import os
import sys
import logging
import json
import random
import math
import datetime
import time
import collections

def some_function(x, y):
    if x > y:   # Indentation Error: should be 4 spaces, not 2
      print("x is greater than y")
    elif x < y:
        print("y is greater than x")  # Correct indentation but inconsistent with above.
      return sqrt(x + y)  # Indentation issue here again.
    else:
        print("x and y are equal")

    # Line too long (more than 79 characters):
    print("This is a line that is way too long and should trigger a flake8 error because it exceeds the 79 characters limitation.")

def another_function(arg):
  return random.choice([arg, "default"])   # Trailing whitespace at the end

some_function(10, 5)

# Comment that is too long and would be flagged by flake8 for exceeding the line length limit, which should be 72 or 79 characters
# This comment is way too long for a normal style guide and should cause an error because it doesn't fit within the recommended length of the comment line.
print("This is an extra print statement that is not necessary and will cause an unused import warning. im going to make this longer to trigger a changa and also trigger a flake8 error hopfully this is enough text to trigger the line too long error. probably. ")

if __name__ == "__main__":
    another_function("test")
    sys.exit(0)  # sys.exit is unused here, so Flake8 will complain about it



def dummy_function_1():
    pass


def dummy_function_2():
    pass


def dummy_function_3():
    pass


def dummy_function_4():
    pass


def dummy_function_5():
    pass


def dummy_function_6():
    pass


def dummy_function_7():
    pass


def dummy_function_8():
    pass


def dummy_function_9():
    pass


def dummy_function_10():
    pass


def dummy_function_11():
    pass


def dummy_function_12():
    pass


def dummy_function_13():
    pass


def dummy_function_14():
    pass


def dummy_function_15():
    pass


def dummy_function_16():
    pass


def dummy_function_17():
    pass


def dummy_function_18():
    pass


def dummy_function_19():
    pass


def dummy_function_20():
    pass


def dummy_function_21():
    pass


def dummy_function_22():
    pass


def dummy_function_23():
    pass


def dummy_function_24():
    pass


def dummy_function_25():
    pass


def dummy_function_26():
    pass


def dummy_function_27():
    pass


def dummy_function_28():
    pass


def dummy_function_29():
    pass


def dummy_function_30():
    pass


def dummy_function_31():
    pass


def dummy_function_32():
    pass


def dummy_function_33():
    pass


def dummy_function_34():
    pass


def dummy_function_35():
    pass


def dummy_function_36():
    pass


def dummy_function_37():
    pass


def dummy_function_38():
    pass


def dummy_function_39():
    pass


def dummy_function_40():
    pass


def dummy_function_41():
    pass


def dummy_function_42():
    pass


def dummy_function_43():
    pass


def dummy_function_44():
    pass


def dummy_function_45():
    pass


def dummy_function_46():
    pass


def dummy_function_47():
    pass


def dummy_function_48():
    pass


def dummy_function_49():
    pass


def dummy_function_50():
    pass


def dummy_function_51():
    pass


def dummy_function_52():
    pass


def dummy_function_53():
    pass


def dummy_function_54():
    pass


def dummy_function_55():
    pass


def dummy_function_56():
    pass


def dummy_function_57():
    pass


def dummy_function_58():
    pass


def dummy_function_59():
    pass


def dummy_function_60():
    pass


def dummy_function_61():
    pass


def dummy_function_62():
    pass


def dummy_function_63():
    pass


def dummy_function_64():
    pass


def dummy_function_65():
    pass


def dummy_function_66():
    pass


def dummy_function_67():
    pass


def dummy_function_68():
    pass


def dummy_function_69():
    pass


def dummy_function_70():
    pass


def dummy_function_71():
    pass


def dummy_function_72():
    pass


def dummy_function_73():
    pass


def dummy_function_74():
    pass


def dummy_function_75():
    pass


def dummy_function_76():
    pass


def dummy_function_77():
    pass


def dummy_function_78():
    pass


def dummy_function_79():
    pass


def dummy_function_80():
    pass


def dummy_function_81():
    pass


def dummy_function_82():
    pass


def dummy_function_83():
    pass


def dummy_function_84():
    pass


def dummy_function_85():
    pass


def dummy_function_86():
    pass


def dummy_function_87():
    pass


def dummy_function_88():
    pass


def dummy_function_89():
    pass


def dummy_function_90():
    pass


def dummy_function_91():
    pass


def dummy_function_92():
    pass


def dummy_function_93():
    pass


def dummy_function_94():
    pass


def dummy_function_95():
    pass


def dummy_function_96():
    pass


def dummy_function_97():
    pass


def dummy_function_98():
    pass


def dummy_function_99():
    pass


def dummy_function_100():
    pass


def dummy_function_101():
    pass


def dummy_function_102():
    pass


def dummy_function_103():
    pass


def dummy_function_104():
    pass


def dummy_function_105():
    pass


def dummy_function_106():
    pass


def dummy_function_107():
    pass


def dummy_function_108():
    pass


def dummy_function_109():
    pass


def dummy_function_110():
    pass


def dummy_function_111():
    pass


def dummy_function_112():
    pass


def dummy_function_113():
    pass


def dummy_function_114():
    pass


def dummy_function_115():
    pass


def dummy_function_116():
    pass


def dummy_function_117():
    pass


def dummy_function_118():
    pass


def dummy_function_119():
    pass


def dummy_function_120():
    pass


def dummy_function_121():
    pass


def dummy_function_122():
    pass


def dummy_function_123():
    pass


def dummy_function_124():
    pass


def dummy_function_125():
    pass


def dummy_function_126():
    pass


def dummy_function_127():
    pass


def dummy_function_128():
    pass


def dummy_function_129():
    pass


def dummy_function_130():
    pass


def dummy_function_131():
    pass


def dummy_function_132():
    pass


def dummy_function_133():
    pass


def dummy_function_134():
    pass


def dummy_function_135():
    pass


def dummy_function_136():
    pass


def dummy_function_137():
    pass


def dummy_function_138():
    pass


def dummy_function_139():
    pass


def dummy_function_140():
    pass


def dummy_function_141():
    pass


def dummy_function_142():
    pass


def dummy_function_143():
    pass


def dummy_function_144():
    pass


def dummy_function_145():
    pass


def dummy_function_146():
    pass


def dummy_function_147():
    pass


def dummy_function_148():
    pass


def dummy_function_149():
    pass


def dummy_function_150():
    pass


def dummy_function_151():
    pass


def dummy_function_152():
    pass


def dummy_function_153():
    pass


def dummy_function_154():
    pass


def dummy_function_155():
    pass


def dummy_function_156():
    pass


def dummy_function_157():
    pass


def dummy_function_158():
    pass


def dummy_function_159():
    pass


def dummy_function_160():
    pass


def dummy_function_161():
    pass


def dummy_function_162():
    pass


def dummy_function_163():
    pass


def dummy_function_164():
    pass


def dummy_function_165():
    pass


def dummy_function_166():
    pass


def dummy_function_167():
    pass


def dummy_function_168():
    pass


def dummy_function_169():
    pass


def dummy_function_170():
    pass


def dummy_function_171():
    pass


def dummy_function_172():
    pass


def dummy_function_173():
    pass


def dummy_function_174():
    pass


def dummy_function_175():
    pass


def dummy_function_176():
    pass


def dummy_function_177():
    pass


def dummy_function_178():
    pass


def dummy_function_179():
    pass


def dummy_function_180():
    pass


def dummy_function_181():
    pass


def dummy_function_182():
    pass


def dummy_function_183():
    pass


def dummy_function_184():
    pass


def dummy_function_185():
    pass


def dummy_function_186():
    pass


def dummy_function_187():
    pass


def dummy_function_188():
    pass


def dummy_function_189():
    pass


def dummy_function_190():
    pass


def dummy_function_191():
    pass


def dummy_function_192():
    pass


def dummy_function_193():
    pass


def dummy_function_194():
    pass


def dummy_function_195():
    pass


def dummy_function_196():
    pass


def dummy_function_197():
    pass


def dummy_function_198():
    pass


def dummy_function_199():
    pass


def dummy_function_200():
    print('hello')
    print('am i restricted??')
    pass
