"""Download the two public datasets into raw/ (git-ignored).

Twitter data needs a Kaggle token in ~/.kaggle. Bitext is a plain download from Hugging Face.
Usage: python scripts/download_data.py
"""
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"
KAGGLE = str(Path(sys.executable).parent / "kaggle")
BITEXT_URL = (
    "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset"
    "/resolve/main/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
)


def twitter():
    out = RAW / "twcs"
    if (out / "twcs.csv").exists():
        return
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([KAGGLE, "datasets", "download", "thoughtvector/customer-support-on-twitter",
                    "-f", "twcs/twcs.csv", "-p", str(out), "--unzip"], check=True)


def bitext():
    out = RAW / "bitext" / "bitext.csv"
    if out.exists():
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(BITEXT_URL, out)


if __name__ == "__main__":
    bitext()
    twitter()
    print("raw data ready in", RAW)
