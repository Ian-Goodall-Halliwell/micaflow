#!/usr/bin/env nextflow

params.subject = ''
params.session = ''
params.out_dir = ''
params.threads = ''
params.data_directory = ''
params.run_dwi = true // Toggle for running DWI processing, set via `--run_dwi false` to skip.


// ------------------------------------------------------------------
// 1. Denoise
// ------------------------------------------------------------------
process DwiDenoise {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/dwi", mode: 'copy'

    input:
    tuple val(type), path(moving_path)
    path bval
    path bvec

    output:
    tuple val(type), path("denoised_moving.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_denoise.py \
        --moving ${moving_path} \
        --bval ${bval} \
        --bvec ${bvec}
    """
}

// ------------------------------------------------------------------
// 2. Motion Correction
// ------------------------------------------------------------------
process DwiMotionCorrection {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/dwi", mode: 'copy'

    input:
    tuple val(type), path(denoised_output)
    path dwi_bval
    path dwi_bvec

    output:
    tuple val(type), path("moving_motion_corrected.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_motioncorrection.py \
        --denoised ${denoised_output} \
        --bval ${dwi_bval} \
        --bvec ${dwi_bvec}
    """
}

// ------------------------------------------------------------------
// 3. Compute Topup (Warp Field + Mask)
// ------------------------------------------------------------------
process DwiTopup {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(type), path(moving_path)
    path b0_path
    path b0_bval
    path b0_bvec

    output:
    tuple val(type), path("warp.nii.gz"), path("mask.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_topup.py \
        --moving ${moving_path} \
        --b0 ${b0_path} \
        --b0_bval ${b0_bval} \
        --b0_bvec ${b0_bvec} \
        --warp_out warp.nii.gz \
        --mask_out mask.nii.gz
    """
}

// ------------------------------------------------------------------
// 4. Apply Topup
// ------------------------------------------------------------------
process DwiApplyTopup {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(type), path(motion_corrected)
    path warp_field
    path input_affine // e.g. original DWI path, if needed

    output:
    tuple val(type), path("topup_corrected.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_applytopup.py \
        --motion_corr ${motion_corrected} \
        --warp ${warp_field} \
        --affine ${input_affine}
    """
}

// ------------------------------------------------------------------
// 5. Bias Field Correction
// ------------------------------------------------------------------
process DwiBiasCorrection {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/dwi", mode: 'copy'

    input:
    tuple val(type), path(denoised_output)
    path mask_path

    output:
    tuple val(type), path("denoised_moving_corrected.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_biascorrection.py \
        --image ${denoised_output} \
        --mask ${mask_path}
    """
}
process DwiRegistration {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(movingType), path(movingImage)
    tuple val(fixedType), path(fixedImage)
    

    output:
        path "*_fwdfield.nii.gz"
        path "*_fwdaffine.mat"


    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_reg.py \
        --fixed ${fixedImage} \
        --moving ${movingImage} \
        --affine ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_fwdaffine.mat \
        --rev_affine ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_bakaffine.mat \
        --warpfield ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_fwdfield.nii.gz \
        --rev_warpfield ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_bakfield.nii.gz
    """
}

// ------------------------------------------------------------------
// 6. Linear Registration
// ------------------------------------------------------------------
process DwiLinearReg {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(type), path(bias_corrected)
    path dwi_bval
    path dwi_bvec
    path atlas

    output:
    tuple val(type), path("registered.nii.gz"), path("reg_affine.txt")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_linearreg.py \
        --bias_corr ${bias_corrected} \
        --bval ${dwi_bval} \
        --bvec ${dwi_bvec} \
        --atlas ${atlas} \
        --affine reg_affine.txt
    """
}

// ------------------------------------------------------------------
// 7. Nonlinear Registration
// ------------------------------------------------------------------
process DwiNonlinearReg {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(type), path(linear_reg_output)
    path atlas

    output:
    tuple val(type), path("backward_MNI_warp.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_nonlinearreg.py \
        --atlas ${atlas} \
        --fixed ${linear_reg_output} \
        --warp backward_MNI_warp.nii.gz
    """
}

// ------------------------------------------------------------------
// 8. Compute FA and MD
// ------------------------------------------------------------------
process DwiComputeFaMd {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/metrics", mode: 'copy'

    input:
    tuple val(type), path(bias_corrected)
    path mask_path
    path dwi_bval
    path dwi_bvec

    output:
    tuple val(type),
          path("fa_map.nii.gz"),
          path("md_map.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_compute_fa_md.py \
        --bias_corr ${bias_corrected} \
        --mask ${mask_path} \
        --bval ${dwi_bval} \
        --bvec ${dwi_bvec}
    """
}

// ------------------------------------------------------------------
// 9. FA/MD Registration into MNI Space
// ------------------------------------------------------------------
process DwiFaMdRegistration {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(type), path(fa_map_file), path(md_map_file)
    path atlas
    path affine_matrix_file
    path nonlinear_forward_warp

    output:
    tuple val(type), path("fa_registered.nii.gz"), path("md_registered.nii.gz")

    script:
    """
    python3 ${workflow.projectDir}/scripts/dwi_fa_md_registration.py \
        --fa ${fa_map_file} \
        --md ${md_map_file} \
        --atlas ${atlas} \
        --reg_affine ${affine_matrix_file} \
        --mapping ${nonlinear_forward_warp} \
        --out_fa fa_registered.nii.gz \
        --out_md md_registered.nii.gz
    """
}


process BiasFieldCorrection {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(image)
    path mask
    
    output:
    tuple val(type), path("*_desc-N4_*.nii.gz")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/N4BiasFieldCorrection.py \
        -i ${image} \
        -o ${params.subject}_${params.session}_desc-N4_${type}.nii.gz \
        -m ${mask} 
    """
}

process Registration_T1w {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'

    input:
    tuple val(fixedType), path(fixedImage)
    tuple val(movingType), path(movingImage)

    output:
    tuple val(movingType), path("*_space-${fixedType}.nii.gz"),
          path("*_fwdfield.nii.gz"),
          path("*_bakfield.nii.gz"),
          path("*_fwdaffine.mat"),
          path("*_bakaffine.mat")

    script:
    """
    python3 ${workflow.projectDir}/scripts/coregister.py \
        --fixed-file ${fixedImage} \
        --moving-file ${movingImage} \
        --out-file ${params.subject}_${params.session}_${movingType}_space-${fixedType}.nii.gz \
        --warp-file ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_fwdfield.nii.gz \
        --affine-file ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_fwdaffine.mat \
        --rev-warp-file ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_bakfield.nii.gz \
        --rev-affine-file ${params.subject}_${params.session}_from-${movingType}_to-${fixedType}_bakaffine.mat
    """
}

process Registration_MNI152 {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/xfm", mode: 'copy'
    
    input:
    tuple val(type), path(image)
    path fixed

    output:
    tuple val(type), path("*_space-MNI152.nii.gz"),
          path("*_fwdfield.nii.gz"), 
          path("*_bakfield.nii.gz"),
          path("*_fwdaffine.mat"), 
          path("*_bakaffine.mat")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/coregister.py \
        --fixed-file ${fixed} \
        --moving-file ${image} \
        --out-file ${params.subject}_${params.session}_${type}_space-MNI152.nii.gz \
        --warp-file ${params.subject}_${params.session}_from-${type}_to-MNI152_fwdfield.nii.gz \
        --affine-file ${params.subject}_${params.session}_from-${type}_to-MNI152_fwdaffine.mat \
        --rev-warp-file ${params.subject}_${params.session}_from-${type}_to-MNI152_bakfield.nii.gz \
        --rev-affine-file ${params.subject}_${params.session}_from-${type}_to-MNI152_bakaffine.mat 
    """
}

process ApplyWarp {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(n4_image), path(warp_field), path(affine), path(reference), val(reference_type)
    
    output:
    tuple val(type), path("*_space-${reference_type}_*.nii.gz")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/use_warp.py \
        --moving ${n4_image} \
        --reference ${reference} \
        --affine ${affine} \
        --warp ${warp_field} \
        --out ${params.subject}_${params.session}_space-${reference_type}_${type}.nii.gz
    """
}

process ApplyWarpFLAIRtoT1w {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(n4_image), path(warp_field), path(affine), path(reference), val(reference_type)
    
    output:
    tuple val(type), path("*_space-${reference_type}_*.nii.gz")
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/use_warp.py \
        --moving ${n4_image} \
        --reference ${reference} \
        --affine ${affine} \
        --warp ${warp_field} \
        --out ${params.subject}_${params.session}_space-${reference_type}_${type}.nii.gz
    """
}

process SkullStrip {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/anat", mode: 'copy'
    
    input:
    tuple val(type), path(image)
    
    output:
    tuple val(type), path("${type}_hdbet.nii.gz") 
    path "${type}_hdbet_bet.nii.gz"
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/hdbet.py \
        --input ${image} \
        --output ${type}_hdbet.nii.gz 
    """
}

process CalculateMetrics {
    conda "envs/micaflow.yml" 
    publishDir "${params.out_dir}/${params.subject}/${params.session}/metrics", mode: 'copy'
    
    input:
    tuple val(type), path(warped_image)
    path atlas
    
    output:
    path "${type}_${params.subject}_${params.session}_jaccard.csv"
    
    script:
    """
    python3 ${workflow.projectDir}/scripts/calculate_metrics.py \
        ${warped_image} \
        ${atlas} \
        "${type}_${params.subject}_${params.session}_jaccard.csv"
    """
}

process RunTexture {
    conda "envs/micaflow.yml"
    publishDir "${params.out_dir}/${params.subject}/${params.session}/textures", mode: 'copy'
    
    input:
    tuple val(type), path(image)
    path mask 
    
    output:
    tuple val(type),
        path("*_gradient_magnitude.nii"), 
        path("*_relative_intensity.nii")

    script:
    """
    python3 ${workflow.projectDir}/scripts/runtexture.py \
        --input ${image} \
        --mask ${mask} \
        --output ${params.subject}_${params.session}_${type}_textures_output
    """
}

workflow {
    // Construct expected file paths for the anatomical images
    def t1wPath = "${params.data_directory}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_run-1_T1w.nii.gz"
    def flairPath = "${params.data_directory}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_FLAIR.nii.gz"

    // Check if the files exist
    if( !new File(t1wPath).exists() || !new File(flairPath).exists() ) {
        exit 1, "Missing input image(s):\n  T1w: ${t1wPath}\n  FLAIR: ${flairPath}"
    }
    // Validate required parameters
    if (!params.subject || !params.session || !params.out_dir || !params.threads || !params.data_directory) {
        exit 1, """
        Required parameters missing. Please provide:
        --subject            Subject ID
        --session           Session ID
        --out_dir           Output directory
        --threads           Number of threads
        --data_directory    BIDS-compatible data directory
        --run_dwi          Run DWI processing (default: true)
        """
    }

    // Define atlas paths
    ATLAS_DIR = "${workflow.projectDir}/atlas"

    // Input channels for the anatomical pipeline
    atlas = file("${ATLAS_DIR}/mni_icbm152_t1_tal_nlin_sym_09a.nii")
    atlas_mask = file("${ATLAS_DIR}/mni_icbm152_t1_tal_nlin_sym_09a_mask.nii")

    // -----------------------------------------------------------
    // Anatomical pipeline
    // -----------------------------------------------------------

    // Create channel for input images
    input_images = Channel.fromList([
        ['T1w', file("${params.data_directory}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_run-1_T1w.nii.gz")],
        ['FLAIR', file("${params.data_directory}/${params.subject}/${params.session}/anat/${params.subject}_${params.session}_FLAIR.nii.gz")]
    ])



    // Execute SkullStrip process
    (skullstrip_out, skull_mask) = SkullStrip(input_images)

    // Perform bias field correction
    n4_out = BiasFieldCorrection(skullstrip_out, skull_mask)


    // Separate T1w and FLAIR images
    input_t1w = input_images.filter { it[0] == 'T1w' }
    input_flair = input_images.filter { it[0] == 'FLAIR' }

    // Run registrations
    reg_out = Registration_T1w(input_t1w, input_flair)
    mni_reg_out = Registration_MNI152(input_t1w, atlas)

    // Ensure separate N4 channels are ready
    n4_skullstrip_t1w = n4_out.filter { it[0] == 'T1w' }.map { tuple -> file(tuple[1]) }
    n4_skullstrip_flair = n4_out.filter { it[0] == 'FLAIR' }.map { tuple -> file(tuple[1]) }

    // Now create a channel for ApplyWarpFLAIRtoT1w and make sure it waits for all processes
    flair_to_t1w_channel = n4_skullstrip_flair
        .combine(reg_out)               // Produces tuple: [flair, reg]
        .combine(n4_skullstrip_t1w)     // Produces tuple: [[flair, reg], t1w]
        .map { combined ->  
            def flair = combined[0]
            def movingType   = combined[1]
            def registeredImage = combined[2]
            def fwdfield     = combined[3]
            def bakfield     = combined[4]
            def fwdaffine    = combined[5]
            def bakaffine    = combined[6]
            def t1w = combined[7]

            // Return a properly structured tuple
            tuple('FLAIR', flair, fwdfield, fwdaffine, t1w, 'T1w')
        }

    // Now invoke ApplyWarpFLAIRtoT1w and ensure it waits for all the processes
    warped_flair_t1w = ApplyWarpFLAIRtoT1w(flair_to_t1w_channel)


    // Build a channel for T1w → MNI152 using combine
    t1w_to_mni_channel = n4_skullstrip_t1w
        .combine(mni_reg_out)
        .map { combined ->
            // reg: [ type, registeredImage, fwdfield, bakfield, fwdaffine, bakaffine ]
            tuple('T1w', combined[0], combined[3], combined[5], atlas, 'MNI152')
        }

    // Build a channel for FLAIR → MNI152 using combine
    flair_to_mni_channel = warped_flair_t1w
        .combine(mni_reg_out)
        .map { combined ->
            tuple('FLAIR', combined[1], combined[4], combined[6], atlas, 'MNI152')
        }

    combined_apply_warp = t1w_to_mni_channel.mix(flair_to_mni_channel)

    // Now ApplyWarp can use the single channel of 6-element tuples
    warped_images = ApplyWarp(combined_apply_warp)

    warped_flair = warped_images.filter { it[0] == 'FLAIR' }

    warped_t1w = warped_images.filter { it[0] == 'T1w' }


    texture_in = warped_flair.mix(warped_t1w)

    // Call RunTexture (from your earlier definition) using texture_in.
    texture_out = RunTexture(texture_in, atlas_mask)

    warped_flair_metrics = warped_images.filter { it[0] == 'FLAIR' }
    warped_t1w_metrics = warped_images.filter { it[0] == 'T1w' }


    metrics_in_in = warped_flair_metrics.mix(warped_t1w_metrics)

    // Execute CalculateMetrics using the warped FLAIR (for example) and the atlas
    calculate_metrics_out = CalculateMetrics(
        metrics_in_in,
        atlas
    )

    // -----------------------------------------------------------
    // DWI pipeline (only run if params.run_dwi == true)
    // -----------------------------------------------------------
    if (params.run_dwi) {
        // Input channels for DWI
        Channel.fromPath("${params.data_directory}/${params.subject}/${params.session}/dwi/*.nii.gz")
            .filter { it.name.contains("b700") }
            .map { path -> tuple("b700", file(path)) }
            .set { input_dwi }
        Channel.fromPath("${params.data_directory}/${params.subject}/${params.session}/dwi/*.bvec")
            .filter { it.name.contains("b700") }
            .map { path -> file(path) }
            .set { input_bvec }
        Channel.fromPath("${params.data_directory}/${params.subject}/${params.session}/dwi/*.bval")
            .filter { it.name.contains("b700") }
            .map { path -> file(path) }
            .set { input_bval }

        Channel.fromPath("${params.data_directory}/${params.subject}/${params.session}/dwi/*.nii.gz")
            .filter { it.name.contains("PA") }
            .map { path -> file(path) }
            .set { b0_img }
        Channel.fromPath("${params.data_directory}/${params.subject}/${params.session}/dwi/*.bvec")
            .filter { it.name.contains("PA") }
            .map { path -> file(path) }
            .set { b0_bvecs }
        Channel.fromPath("${params.data_directory}/${params.subject}/${params.session}/dwi/*.bval")
            .filter { it.name.contains("PA") }
            .map { path -> file(path) }
            .set { b0_bvals }

        input_dwi.view { "input_dwi: $it" }
        b0_img.view { "b0_img: $it" }
        b0_bvecs.view { "b0_bvecs: $it" }
        b0_bvals.view { "b0_bvals: $it" }

        // 3) Topup
        topup_out = DwiTopup(
            input_dwi, // or mc_out if desired
            b0_img,
            b0_bvals,
            b0_bvecs
        )



        // 1) Denoise
        denoised_out = DwiDenoise(
            input_dwi,
            input_bval,
            input_bvec
        )

        // 2) Motion Correction
        mc_out = DwiMotionCorrection(
            denoised_out,
            input_bval,
            input_bvec
        )

        // 4) Apply Topup
        topup_applied = DwiApplyTopup(
            mc_out,
            topup_out.map{ it[1] },  // warp field
            input_dwi.map{ it[1] },  // optional affine
        )

        // 5) Bias Correction
        bias_corr = DwiBiasCorrection(
            topup_applied,
            topup_out.map{ it[2] } // mask
        )

        (lin_reg, nonlin_reg) = DwiRegistration(
            topup_applied,
            n4_out.filter { it[0] == 'T1w' }
        )


        // 8) Compute FA/MD
        fa_md = DwiComputeFaMd(
            bias_corr,
            topup_out.map{ it[2] }, // mask
            input_bval,
            input_bvec
        )

        // 9) FA/MD Registration
        fa_md_registered = DwiFaMdRegistration(
            fa_md,
            n4_out.filter { it[0] == 'T1w' }.map { it[1] },
            lin_reg,     
            nonlin_reg   
        )

        fa_md_registered.view()
    } else {
        println "DWI pipeline disabled via --run_dwi false"
    }
            
}