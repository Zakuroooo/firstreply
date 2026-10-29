"""Download the two public datasets into raw/ (git-ignored).

Twitter data: Kaggle (needs a token in ~/.kaggle) if the kaggle CLI is set up, otherwise a public
Hugging Face mirror of the same twcs.csv file. scripts/verify_data.py checks the copy is complete.
Bitext: plain download from Hugging Face.
Usage: python scripts/download_data.py
"""
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"
KAGGLE = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle")
BITEXT_URL = (
    "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset"
    "/resolve/main/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
)
# Public re-upload of Kaggle's thoughtvector/customer-support-on-twitter twcs.csv (same 516 MB file).
TWCS_MIRROR = "https://huggingface.co/datasets/SunidhiSriram/twcs/resolve/main/twcs.csv"


def _fetch(url, out):
    tmp = out.with_suffix(".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(out)


def twitter():
    out = RAW / "twcs"
    if (out / "twcs.csv").exists():
        return
    out.mkdir(parents=True, exist_ok=True)
    if Path(KAGGLE).exists() and (Path.home() / ".kaggle" / "kaggle.json").exists():
        subprocess.run([KAGGLE, "datasets", "download", "thoughtvector/customer-support-on-twitter",
                        "-f", "twcs/twcs.csv", "-p", str(out), "--unzip"], check=True)
    else:
        print("no Kaggle token: using the Hugging Face mirror of twcs.csv")
        _fetch(TWCS_MIRROR, out / "twcs.csv")


def bitext():
    out = RAW / "bitext" / "bitext.csv"
    if out.exists():
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    _fetch(BITEXT_URL, out)


if __name__ == "__main__":
    bitext()
    if "--bitext-only" not in sys.argv:
        twitter()
    print("raw data ready in", RAW)
