from texturepipeline import noelTexturesPy
import argparse


def run_texture_pipeline(input, mask, output_dir):
    pipeline = noelTexturesPy(
        id='textures',
        output_dir=output_dir,
        input=input,
        mask=mask,
    )
    pipeline.file_processor()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform N4 Bias Field Correction")
    parser.add_argument("--input", "-i", required=True, help="Input image file")
    parser.add_argument("--mask", "-m", required=True, help="Input mask file")
    parser.add_argument(
        "--output", "-o", required=True, help="Output corrected image file"
    )
    args = parser.parse_args()
    run_texture_pipeline(args.input, args.mask, args.output)
