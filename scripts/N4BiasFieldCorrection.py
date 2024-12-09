import ants
import argparse


def bias_field_correction(image, output):
    img = ants.image_read(image)
    corrected_img = ants.n4_bias_field_correction(img)
    ants.image_write(corrected_img, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform N4 Bias Field Correction")
    parser.add_argument("--input", "-i", required=True, help="Input image file")
    parser.add_argument(
        "--output", "-o", required=True, help="Output corrected image file"
    )
    args = parser.parse_args()
    bias_field_correction(args.input, args.output)
