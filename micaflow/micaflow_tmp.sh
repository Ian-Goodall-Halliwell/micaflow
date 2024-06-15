#!/bin/bash

help() {
  echo -e "\n $(basename $0)
  \t--subject [SUBJECT ID INCLUDE sub-]
  \t--session []
  \t--out_dir []
  \t--fs_license []
  \t--threads []\n"
}

echo "
           _            __ _
 _ __ ___ (_) ___ __ _ / _| | _____      __
| '_ \` _ \| |/ __/ _/| |_| |/ _ \ \ /\ / /
| | | | | | | (_| (_| |  _| | (_) \ V  V /
|_| |_| |_|_|\___\__,_|_| |_|\___/ \_/\_/
"

args=("$@")

# Parse command line options
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --subject)
      subject="$2"
      echo "Input --subject : ${subject}"
      shift
      ;;
    --session)
      session="$2"
      echo "Input --session : ${session}"
      shift
      ;;
    --bids)
      bids="$2"
      echo "Input --bids : ${bids}"
      shift
      ;;
    --out_dir)
      out_dir="$2"
      echo "Input --out_dir : ${out_dir}"
      shift
      ;;
    --fs_license)
      fs_license="$2"
      echo "Input --fs_license : ${fs_license}"
      shift
      ;;
    --threads)
      threads="$2"
      if [ -z "${threads}" ]; then
        threads=6
      fi
      echo "Input --threads : ${threads}"
      shift
      ;;
    -h|--h|-help|--help)
      help
      exit 0
      ;;
    -*)
      Error "Unknown option ${1}"
      exit 1
  ;;
  esac
  shift
done

# Scripts directory
micaflow_dir=$(dirname $(realpath "${0}"))

# ------------------------------------------------- Unit test -------------------------------------------------- #
if [ -z "$fs_license" ]; then
  echo "Error: --fs_license is required."
  exit 1
fi

if [ -z "$subject" ] || [ -z "$session" ] || [ -z "$bids" ]; then
  echo "Error: --subject, --session, and --bids directories are required."
  exit 1
fi

# Check if the subject/session directory exists
if [ ! -d "${bids}/${subject}/${session}" ]; then
  echo "Error: Directory ${bids}/${subject}/${session} does not exist."
  exit 1
fi

# Check for existing output directory and handle accordingly
if [ -d "${out_dir}/${subject}/${session}" ]; then
  echo "Warning: Output directory already exists. Contents may be overwritten."
fi

# ------------------------------------------------- Initiate timer -------------------------------------------------- #
SECONDS=0

# ------------------------------------------- Define the scrcipt variables ------------------------------------------ #
BIDS_ID=${subject}_${session}
out=${out_dir}/${subject}/${session}
T1w=${bids}/${subject}/${session}/anat/${BIDS_ID}_run-1_T1w.nii.gz
flair=${bids}/${subject}/${session}/anat/${BIDS_ID}_FLAIR.nii.gz

# If the out directory does not exist, create it
if [ ! -d ${out} ]; then mkdir -p ${out}/{anat,xfm}; fi

# Cretate a temporary directory that will be erased at the end of the processing
tmp_dir=./tmp_${RANDOM}
mkdir ${tmp_dir}

# N4 multi-thread requires this on the ENV
export ITK_GET_GLOBAL_DEFAULT_NUMBER_OF_THREADS=${threads}

# Output of the segmentation, this and the nifti must be inside the repository!
atlas_dir=${micaflow_dir}/atlas

# MNI152 compresed NIFTI
atlas_mni152=${atlas_dir}/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz
atlas_mni152_seg=${atlas_dir}/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz


# ------------------------------------------------ Define micaflow ------------------------------------------------ #

function micaflow(){
# Describe your function:
  local image=${1}
  local type=${2}

# ------------------------------------------------
  #  Step 1. Brain segmentation
  echo -e "\n------------------------------------------------\nStep 1: Brain segmentation: ${type}\n"
  # Take into account including or not the option --cpu (optional) Enforce running with CPU rather than GPU.
  mri_synthseg --i ${image} \
               --o ${out}/anat/${BIDS_ID}_desc-synthseg_${type}.nii.gz \
               --robust --vol ${out}/anat/${BIDS_ID}_desc-volumes_${type}.csv \
               --qc ${out}/anat/${BIDS_ID}_desc-qc_${type}.csv --threads ${threads} --cpu --parc

  #  Step 3. Registration of T1w to MNI space
  echo -e "\n------------------------------------------------\nStep 3. Registration of ${type} to MNI space\n"
  # Registration from T1w to MNI
  mri_easyreg --ref ${atlas_mni152} \
              --ref_seg ${atlas_mni152_seg} \
              --flo ${image} \
              --flo_seg ${out}/anat/${BIDS_ID}_desc-synthseg_${type}.nii.gz \
              --fwd_field ${out}/xfm/${BIDS_ID}_from-${type}_to-MNI151_desc-easyreg_fwdfield.nii.gz \
              --bak_field ${out}/xfm/${BIDS_ID}_from-${type}_to-MNI151_desc-easyreg_bakfield.nii.gz \
              --threads ${threads}

  # ------------------------------------------------
  #  Step 2. Bias field correction
  echo -e "\n------------------------------------------------\nStep 2. Bias field correction\n"
  N4BiasFieldCorrection  -d 3 -i "$image" -r -o "${tmp_dir}/${BIDS_ID}_desc-N4_${type}.nii.gz"

  # ------------------------------------------------
  #  Step 4. Apply the warpfield to the MNI
  echo -e "\n------------------------------------------------\nStep 4. Apply spatial normalization warpfield\n"
  mri_easywarp --i ${tmp_dir}/${BIDS_ID}_desc-N4_${type}.nii.gz \
               --o ${out}/anat/${BIDS_ID}_space-MNI152_${type}.nii.gz \
               --field ${out}/xfm/${BIDS_ID}_from-${type}_to-MNI151_desc-easyreg_fwdfield.nii.gz \
               --threads ${threads}

micaflow ${T1w} "T1w"
micaflow ${flair} "FLAIR"

# ----------------------------------- Step 5. Calculate Registration Quality Metrics -------------------------------- #
mkdir -p ${out}/scores
# Compute Dice score and Jaccard Index of T1 registration.
python "${micaflow_dir}"/calculate_metrics.py "${out}/anat/${BIDS_ID}_space-MNI152_T1w.nii.gz" "${atlas_mni152_seg}" "{out}/scores/${BIDS_ID}_T1w.csv"

# Compute Dice score and Jaccard Index of T2 registration.
python "${micaflow_dir}"/calculate_metrics.py "${out}/anat/${BIDS_ID}_space-MNI152_FLAIR.nii.gz" "${atlas_mni152_seg}" "{out}/scores/${BIDS_ID}_FLAIR.csv"

# ----------------------------------- Step 6. Normalize images? -------------------------------- #
# remove tmp directory
rm -rfv "${tmp_dir}"

# ------------------------------------------------ Total running time ----------------------------------------------- #
elapsed=$(printf "%.2f" "$(bc <<< "scale=2; $SECONDS/60")")
echo -e "Total elapsed time for ${BIDS_ID}: \033[38;5;220m ${elapsed} \033[0m minutes"
