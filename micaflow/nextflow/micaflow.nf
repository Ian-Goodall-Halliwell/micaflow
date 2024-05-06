#!/usr/bin/env nextflow

params.subject = 'sub-HC062'
params.session = 'ses-03'
params.bids = '/Users/cerys/Documents/MICA/test_data/rawdata'
params.out_dir = '/Users/cerys/Documents/MICA/test_data/test_outputs'
params.fs_license = '/Users/cerys/Documents/MICA/license.txt'
params.threads = 8

process BrainSegmentation {
    tag "${params.subject}_${params.session}_${type}_brain_segmentation"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'

    input:
    path image
    val type

    output:
    path "${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz", emit: synthseg
    path "${params.subject}_${params.session}_desc-volumes_${type}.csv"
    path "${params.subject}_${params.session}_desc-qc_${type}.csv"

    script:
    """
    mkdir -p ${params.out_dir}/${params.subject}/${params.session}/anat
    mri_synthseg --i ${image} \
                 --o ${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz \
                 --robust --vol ${params.subject}_${params.session}_desc-volumes_${type}.csv \
                 --qc ${params.subject}_${params.session}_desc-qc_${type}.csv --threads ${params.threads} --cpu --parc
    """
}

process BiasFieldCorrection {
    tag "${params.subject}_${params.session}_${type}_bias_field_correction"
    publishDir "${tmp_dir}/${params.subject}/${params.session}", mode: 'copy'

    input:
    path image
    val type

    output:
    path "${params.subject}_${params.session}_desc-N4_${type}.nii.gz"

    script:
    """
    tmp_dir = '/Users/cerys/Documents/MICA/test_data/tmp'
    mkdir -p ${tmp_dir}/${params.subject}/${params.session}
    N4BiasFieldCorrection -d 3 -i ${image} -r -o ${params.subject}_${params.session}_desc-N4_${type}.nii.gz
    """
}

process Registration {
    tag "${params.subject}_${params.session}_${type}_registration"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'
    
    input:
    path image
    val type
    path segmentation
    path atlas_mni152
    path atlas_mni152_seg

    output:
    path "${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_fwdfield.nii.gz", emit: fwd_field
    path "${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_bakfield.nii.gz", emit: bak_field

    script:
    """
    mkdir -p ${params.out_dir}/${params.subject}/${params.session}/xfm
    mri_easyreg --ref ${atlas_mni152} \
                --ref_seg ${atlas_mni152_seg} \
                --flo ${image} \
                --flo_seg ${segmentation} \
                --fwd_field ${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_fwdfield.nii.gz \
                --bak_field ${params.subject}_${params.session}_from-${type}_to-MNI151_desc-easyreg_bakfield.nii.gz \
                --threads ${params.threads}
    """
}

process ApplyWarp {
    tag "${params.subject}_${params.session}_${type}_apply_warp"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    val type
    path N4
    path warp_field

    output:
    path "${params.subject}_${params.session}_space-MNI152_${type}.nii.gz"

    script:
    """
    mri_easywarp --i ${N4} \
                 --o ${params.subject}_${params.session}_space-MNI152_${type}.nii.gz \
                 --field ${warp_field} \
                 --threads ${params.threads}
    """
}

workflow {

    // Define atlas paths as parameters or variables
    atlas_mni152 = Channel.fromPath('/atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz')
    atlas_mni152_seg = Channel.fromPath('/atlas/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz')

    images = Channel.fromPath("${params.bids}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_run-1_T1w.nii.gz", "${params.bids}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_FLAIR.nii.gz")
    types = Channel.of('T1w', 'FLAIR')

    // Brain Segmentation
    BrainSegmentation(images, types)
    BrainSegmentation.out.synthseg
        .set { seg_ch }

    // Bias Field Correction
    BiasFieldCorrection(images, types)
    BiasFieldCorrection.out
        .set { corrected_ch }

    // Registration to MNI space
    Registration(images, types, seg_ch, atlas_mni152, atlas_mni152_seg)
    Registration.out.fwd_field
        .set { registration_ch }

    // Apply Warp uses outputs from BiasFieldCorrection and Registration
    ApplyWarp(types, corrected_ch, registration_ch)

}