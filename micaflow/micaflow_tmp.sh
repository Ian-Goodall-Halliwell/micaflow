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


# ------------------------------------------------- Initiate timer -------------------------------------------------- #
SECONDS=0

# ------------------------------------------- Define the scrcipt variables ------------------------------------------ #
BIDS_ID=${subject}_${session}
out=${out_dir}/${subject}/${session}
T1w=/data_/mica3/BIDS_MICs/rawdata/${subject}/${session}/anat/${BIDS_ID}_run-1_T1w.nii.gz
flair=/data_/mica3/BIDS_MICs/rawdata/${subject}/${session}/anat/${BIDS_ID}_FLAIR.nii.gz

# If the out directory does not exist, create it
if [ ! -d ${out} ]; then mkdir -p ${out}/{anat,xfm}; fi

# Cretate a temporary directory that will be erased at the end of the processing
tmp_dir=./tmp_${RANDOM}
mkdir ${tmp_dir}

# -------------------------------------------- Step 1. Brain segmentation ------------------------------------------- #
echo -e "\nStep 1: Brain segmentation\n"

# Segmentation of the T1w image
# Take into account including or not the option --cpu (optional) Enforce running with CPU rather than GPU.
mri_synthseg --i ${T1w} \
             --o ${out}/anat/${BIDS_ID}_desc-synthseg_T1w.nii.gz \
             --robust --vol ${out}/anat/${BIDS_ID}_desc-volumes_T1w.csv \
             --qc ${out}/anat/${BIDS_ID}_desc-qc_T1w.csv --threads ${threads} --cpu --parc

# Segmentation of the FLAIR image
mri_synthseg --i ${flair} \
            --o ${out}/anat/${BIDS_ID}_desc-synthseg_FLAIR.nii.gz \
            --robust --vol ${out}/anat/${BIDS_ID}_desc-volumes_FLAIR.csv \
            --qc ${out}/anat/${BIDS_ID}_desc-qc_FLAIR.csv --threads ${threads} --cpu --parc

# ------------------------------------------- Step 2. Bias field correction ----------------------------------------- #
echo -e "\nStep 2. Bias field correction\n"
# N4 multi-thread requires this on the ENV
export ITK_GET_GLOBAL_DEFAULT_NUMBER_OF_THREADS=${threads}

# Bias field correction (ANTS) for T1w
N4BiasFieldCorrection  -d 3 -i "$T1w" -r -o "${tmp_dir}/${BIDS_ID}_desc-N4_T1w.nii.gz" -v

# Bias field correction for FLAIR
N4BiasFieldCorrection  -d 3 -i "$flair" -r -o "${tmp_dir}/${BIDS_ID}_desc-N4_FLAIR.nii.gz" -v

# -------------------------------------- Step 3. Registration of T1w to MNI space ----------------------------------- #
echo -e "\nStep 3. Registration of T1w to MNI space\n"

# Output of the segmentation, this and the nifti must be inside the repository!
atlas_dir=/host/yeatman/local_raid/cerys/Downloads/mni_icbm152_nlin_sym_09a

# MNI152 compresed NIFTI
atlas_mni152=${atlas_dir}/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz
atlas_mni152_seg=${atlas_dir}/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz

# Registration from T1w to MNI
mri_easyreg --ref ${atlas_mni152} \
            --ref_seg ${atlas_mni152_seg} \
            --flo ${T1w} \
            --flo_seg ${out}/anat/${BIDS_ID}_desc-synthseg_T1w.nii.gz \
            --fwd_field ${out}/xfm/${BIDS_ID}_from-T1w_to-MNI151_1mm_desc-easyreg_fwdfield.nii.gz \
            --bak_field ${out}/xfm/${BIDS_ID}_from-T1w_to-MNI151_1mm_desc-easyreg_bakfield.nii.gz \
            --threads ${threads}

# --------------------------------------------- Step 4. Apply the warpfield ----------------------------------------- #
echo -e "\nStep 4. Apply spatial normalization warpfield\n"

# Apply the warpfield
mri_easywarp --i ${tmp_dir}/${BIDS_ID}_desc-N4_T1w.nii.gz \
             --o ${out}/anat/${BIDS_ID}_space-MNI152_1m_T1w.nii.gz \
             --field ${out}/xfm/${BIDS_ID}_from-T1w_to-MNI151_1mm_desc-easyreg_fwdfield.nii.gz \
             --threads ${threads} --nearest

# ------------------------------------------- Step 5. Align T2/FLAIR to T1w ----------------------------------------- #
echo -e "\nStep 5. Align T2/FLAIR to T1w\n"

# Register FLAIR to T1w
mri_easyreg --ref ${tmp_dir}/${BIDS_ID}_desc-N4_T1w.nii.gz \
            --ref_seg ${out}/anat/${BIDS_ID}_desc-synthseg_T1w.nii.gz \
            --flo ${flair} \
            --flo_seg ${out}/anat/${BIDS_ID}_desc-synthseg_FLAIR.nii.gz \
            --fwd_field ${out}/xfm/${BIDS_ID}_from-FLAIR_to-T1w_desc-easyreg_fwdfield.nii.gz \
            --bak_field ${out}/xfm/${BIDS_ID}_from-FLAIR_to-T1w_desc-easyreg_bakfield.nii.gz \
            --threads ${threads}

# --------------------------------------- Step 6. Apply warpfied of T1w to FLAIR ------------------------------------- #
echo -e "\nStep 6. Apply forward transformation to FLAIR\n"

# Apply forward transformation of flair to T1w space
mri_easywarp --i ${tmp_dir}/${BIDS_ID}_desc-N4_FLAIR.nii.gz \
             --o ${out}/anat/${BIDS_ID}_space-T1w_FLAIR.nii.gz \
             --field ${out}/xfm/${BIDS_ID}_from-FLAIR_to-T1w_desc-easyreg_fwdfield.nii.gz \
             --threads ${threads} --nearest

# Apply forward transformation of flair in the T1w space to MNI space
mri_easywarp --i ${out}/anat/${BIDS_ID}_space-T1w_FLAIR.nii.gz  \
             --o ${out}/anat/${BIDS_ID}_space-MNI152_1mm_FLAIR.nii.gz \
             --field ${out}/xfm/${BIDS_ID}_from-T1w_to-MNI151_1mm_desc-easyreg_fwdfield.nii.gz \
             --threads ${threads} --nearest

# ------------------------------------------------ Total running time ----------------------------------------------- #
elapsed=$(printf "%.2f" "$(bc <<< "scale=2; $SECONDS/60")")
echo "Total elapsed time for ${BIDS_ID}: \033[38;5;220m${elapsed} minutes"
