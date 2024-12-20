import glob
import re
import getopt
import sys
import os


def help_out():
    print('update_lib_version.py -v <version in vX.X.X format>')
    sys.exit()


version = ''

opts, args = getopt.getopt(sys.argv[1:], "hv:", ["version="])

for opt, arg in opts:
    if opt == '-h':
        help_out()
    elif opt in ("-v", "--version"):
        version = arg

if not version:
    help_out()

for file in glob.glob("**/requirements.txt", recursive=True):
    fhi = open(file, mode="r")
    outfilename = f"{file}.new"
    fho = open(outfilename, "w")

    for line in fhi.readlines():
        if "acct_decom_utils" in line:
            line = re.sub("\.git\@.*?$", f".git@{version}", line)
        fho.write(line)

    fhi.close()
    fho.close()

    os.replace(outfilename, file)
