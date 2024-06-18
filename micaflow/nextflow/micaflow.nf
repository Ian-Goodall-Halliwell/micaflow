#!/usr/bin/env nextflow
if (!params.subject || !params.session || !params.out_dir || !params.threads) {
    exit 1, "Error: Missing required parameters. Make sure to specify subject, session, bids, out_dir, threads."
}

process BrainSegmentation {
    tag "${params.subject}_${params.session}_${type}_brain_segmentation"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'

    input:
    tuple path(image), val(type)

    output:
    path "${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz", emit: synthseg
    path "${params.subject}_${params.session}_desc-volumes_${type}.csv"
    path "${params.subject}_${params.session}_desc-qc_${type}.csv"

    script:
    """
    export FS_LICENSE=/path/to/license.txt
    mkdir -p ${params.out_dir}/${params.subject}/${params.session}/anat
    mri_synthseg --i ${image} \
                 --o ${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz \
                 --robust --vol ${params.subject}_${params.session}_desc-volumes_${type}.csv \
                 --qc ${params.subject}_${params.session}_desc-qc_${type}.csv --threads ${params.threads} --cpu --parc
    """
}

process BiasFieldCorrection {
    tag "${params.subject}_${params.session}_${type}_bias_field_correction"

    input:
    tuple path(image), val(type)

    output:
    path "${params.subject}_${params.session}_desc-N4_${type}.nii.gz"

    script:
    """
    N4BiasFieldCorrection -d 3 -i ${image} -r -o ${params.subject}_${params.session}_desc-N4_${type}.nii.gz
    """
}

process Registration {
    tag "${params.subject}_${params.session}_${type}_registration"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple path(image), val(type)
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
    tuple path(image), val(type)
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

process CalculateMetrics {
    tag "${params.subject}_${params.session}_calculate_metrics"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/metrics", mode: 'copy'

    input:
    tuple path(image), val(type)
    path warped
    path atlas_mni152
    
    output:
    path "${params.subject}_${params.session}_jaccard.csv"

    script:
    """
    python3 calculate_metrics.py ${warped} ${atlas_mni152} ${params.subject}_${params.session}_jaccard.csv
    """
}

workflow {

    // Define atlas paths as parameters or variables
    atlas_mni152 = Channel.fromPath('/opt/micaflow/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz')
    atlas_mni152_seg = Channel.fromPath('/opt/micaflow/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz')

    // Define image types and paths
    image_types = Channel.of(
        ["/data/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_run-1_T1w.nii.gz", 'T1w'],
        ["/data/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_FLAIR.nii.gz", 'FLAIR']
    )

    // Brain Segmentation
    BrainSegmentation(image_types)
    BrainSegmentation.out.synthseg
        .set { seg_ch }

    // Bias Field Correction
    BiasFieldCorrection(image_types)
    BiasFieldCorrection.out
        .set { corrected_ch }

    // Registration to MNI space
    Registration(image_types, seg_ch, atlas_mni152, atlas_mni152_seg)
    Registration.out.fwd_field
        .set { registration_ch }

    // Apply Warp uses outputs from BiasFieldCorrection and Registration
    ApplyWarp(image_types, corrected_ch, registration_ch)
    ApplyWarp.out
        .set { warped_ch }

    // Calculate metrics
    CalculateMetrics(image_types, warped_ch, atlas_mni152)

}
