#!/usr/bin/env nextflow

params.subject = ''
params.session = ''
params.bids = ''
params.out_dir = ''
params.fs_license = ''
params.threads = 6

process BrainSegmentation {
    tag "${params.subject}_${params.session}_${type}_brain_segmentation"

    input:
    tuple val(type), path(image) from image_types

    output:
    path "${params.out_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz" into brain_segmentation_ch

    script:
    """
    mkdir -p ${params.out_dir}/${params.subject}/${params.session}/anat
    mri_synthseg --i ${image} \
                 --o ${params.out_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz \
                 --robust --vol ${params.out_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_desc-volumes_${type}.csv \
                 --qc ${params.out_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_desc-qc_${type}.csv --threads ${params.threads} --cpu --parc
    """
}

process BiasFieldCorrection {
    tag "${params.subject}_${params.session}_${type}_bias_field_correction"

    input:
    tuple val(type), path(image) from image_types

    output:
    path ${tmp_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_desc-N4_${type}.nii.gz into bias_field_correction_ch

    script:
    """
    tmp_dir=./tmp_${RANDOM}
    mkdir ${tmp_dir}
    N4BiasFieldCorrection -d 3 -i ${image} -r -o ${tmp_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_desc-N4_${type}.nii.gz
    """
}

process Registration {
    tag "${params.subject}_${params.session}_${type}_registration"
    
    input:
    tuple val(type), path(image) from image_types
    path segmentation from brain_segmentation_ch
    path atlas_mni152
    path atlas_mni152_seg

    output:
    path "${params.out_dir}/${params.subject}/${params.session}/xfm/${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_fwdfield.nii.gz" into forward_field_ch
    path "${params.out_dir}/${params.subject}/${params.session}/xfm/${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_bakfield.nii.gz" into backward_field_ch

    script:
    """
    mkdir -p ${params.out_dir}/${params.subject}/${params.session}/xfm
    mri_easyreg --ref ${atlas_mni152} \
                --ref_seg ${atlas_mni152_seg} \
                --flo ${image} \
                --flo_seg ${segmentation} \
                --fwd_field ${params.out_dir}/${params.subject}/${params.session}/xfm/${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_fwdfield.nii.gz \
                --bak_field ${params.out_dir}/${params.subject}/${params.session}/xfm/${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_bakfield.nii.gz \
                --threads ${params.threads}
    """
}

process ApplyWarp {
    input:
    tuple val(type), path(image) from image_types
    path N4 from bias_field_correction_ch
    path warp_field from forward_field_ch

    output:
    path "${out_dir}/${subject}/${session}/anat/${subject}_${session}_space-MNI152_${type}.nii.gz" into warped_images_ch

    script:
    """
    mri_easywarp --i ${N4} \
                 --o ${params.out_dir}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_space-MNI152_${type}.nii.gz \
                 --field ${warp_field} \
                 --threads ${params.threads}
    """
}

workflow {

    // Define atlas paths as parameters or variables
    micaflow_dir = '$(dirname $(realpath "${0}"))'
    atlas_mni152 = '${micaflow_dir}/atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz'
    atlas_mni152_seg = '${micaflow_dir}/atlas/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz'

    image_data = Channel.from([
    ['T1w', "${params.bids}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_run-1_T1w.nii.gz"],
    ['FLAIR', "${params.bids}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_FLAIR.nii.gz"]
    ])

    // Brain Segmentation
    BrainSegmentation(image_data)
    BrainSegmentation.out
        .set { seg_ch }

    // Bias Field Correction
    BiasFieldCorrection(image_data)
    BiasFieldCorrection.out
        .set { corrected_ch }

    // Registration to MNI space
    Registration(seg_ch.combine(image_data, Channel.value(atlas_mni152), Channel.value(atlas_mni152_seg)))
    Registration.out
        .set { registration_ch }

    // Apply Warp uses outputs from BiasFieldCorrection and Registration
    ApplyWarp(corrected_ch, registration_ch)

}