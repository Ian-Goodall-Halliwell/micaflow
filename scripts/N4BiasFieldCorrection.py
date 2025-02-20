import ants
import argparse


def bias_field_correction(image, output, mask):
    img = ants.image_read(image)
    mask_img = ants.get_mask(img)
    corrected_img = ants.n4_bias_field_correction(img, mask_img)
    ants.image_write(corrected_img, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform N4 Bias Field Correction")
    parser.add_argument("--input", "-i", required=True, help="Input image file")
    parser.add_argument(
        "--output", "-o", required=True, help="Output corrected image file"
    )
    parser.add_argument("-m", "--mask", help="Save binary brain mask to path.")
    args = parser.parse_args()
    bias_field_correction(args.input, args.output, args.mask)
