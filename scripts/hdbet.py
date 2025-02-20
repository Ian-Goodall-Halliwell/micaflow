import subprocess
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform N4 Bias Field Correction")
    parser.add_argument("--input", "-i", required=True, help="Input image file")
    parser.add_argument(
        "--output", "-o", required=True, help="Output corrected image file"
    )
    parser.add_argument("-m", "--mask", help="Save binary brain mask to path.")
    args = parser.parse_args()
    subprocess.run(
        "hd-bet -i " + args.input + " -o " + args.output + " -device cpu",
        shell=True,
    )
