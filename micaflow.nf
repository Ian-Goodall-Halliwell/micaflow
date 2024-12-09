#!/usr/bin/env nextflow

params.subject = ''
params.session = ''
params.out_dir = ''
params.threads = ''
params.data_directory = ''

// Validate required parameters
if (!params.subject || !params.session || !params.out_dir || !params.threads || !params.data_directory) {
    exit 1, """
    Required parameters missing. Please provide:
      --subject            Subject ID
      --session           Session ID
      --out_dir           Output directory
      --threads           Number of threads
      --data_directory    BIDS-compatible data directory
    """
}

// Define atlas paths
ATLAS_DIR = "${workflow.projectDir}/atlas"

process BrainSegmentation {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(image)
    
    output:
    tuple val(type), path("*_desc-synthseg_*.nii.gz"), emit: synthseg
    path "*_desc-volumes_*.csv"
    path "*_desc-qc_*.csv"
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/mri_synthseg.py \
        --i ${image} \
        --o ${params.subject}_${params.session}_desc-synthseg_${type}.nii.gz \
        --robust \
        --vol ${params.subject}_${params.session}_desc-volumes_${type}.csv \
        --qc ${params.subject}_${params.session}_desc-qc_${type}.csv \
        --threads ${params.threads} \
        --cpu \
        --parc
    """
}

process BiasFieldCorrection {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(image)
    
    output:
    tuple val(type), path("*_desc-N4_*.nii.gz")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/N4BiasFieldCorrection.py \
        -i ${image} \
        -o ${params.subject}_${params.session}_desc-N4_${type}.nii.gz
    """
}

process Registration {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'
    
    input:
    tuple val(type), path(image), path(segmentation)
    path atlas
    path atlas_seg
    
    output:
    tuple val(type), 
          path("*_desc-easyreg_fwdfield.nii.gz"), 
          path("*_desc-easyreg_bakfield.nii.gz")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/mri_easyreg.py \
        --ref ${atlas} \
        --ref_seg ${atlas_seg} \
        --flo ${image} \
        --flo_seg ${segmentation} \
        --fwd_field ${params.subject}_${params.session}_from-${type}_to-MNI152_desc-easyreg_fwdfield.nii.gz \
        --bak_field ${params.subject}_${params.session}_from-${type}_to-MNI152_desc-easyreg_bakfield.nii.gz \
        --threads ${params.threads}
    """
}

process ApplyWarp {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(n4_image), path(warp_field)
    
    output:
    tuple val(type), path("*_space-MNI152_*.nii.gz")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/mri_easywarp.py \
        --i ${n4_image} \
        --o ${params.subject}_${params.session}_space-MNI152_${type}.nii.gz \
        --field ${warp_field} \
        --threads ${params.threads}
    """
}

process CalculateMetrics {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/metrics", mode: 'copy'
    
    input:
    tuple val(type), path(warped_image)
    path atlas
    
    output:
    path "*_jaccard.csv"
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/calculate_metrics.py \
        ${warped_image} \
        ${atlas} \
        ${params.subject}_${params.session}_jaccard.csv
    """
}

workflow {
    // Input channels
    atlas = Channel.fromPath("${ATLAS_DIR}/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz")
    atlas_seg = Channel.fromPath("${ATLAS_DIR}/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz")
    
    // Create channel for input images
    input_images = Channel.fromList([
        ['T1w', "${params.data_directory}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_run-1_T1w.nii.gz"],
        ['FLAIR', "${params.data_directory}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_FLAIR.nii.gz"]
    ]).map { type, path -> tuple(type, file(path)) }
    
    // Execute pipeline
    brain_seg_out = BrainSegmentation(input_images)
    n4_out = BiasFieldCorrection(input_images)
    
    // Combine segmentation with original images for registration
    reg_input = input_images.join(brain_seg_out.synthseg)
    reg_out = Registration(reg_input, atlas, atlas_seg)
    
    // Prepare input for warp application
    warp_input = n4_out.join(reg_out.map { type, fwd, bak -> tuple(type, fwd) })
    warped_out = ApplyWarp(warp_input)
    
    // Calculate metrics
    CalculateMetrics(warped_out, atlas)
}