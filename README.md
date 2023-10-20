---
title: 'DDMR: Deep Deformation Map Registration of CT/MRIs'
colorFrom: indigo
colorTo: indigo
sdk: docker
app_port: 7860
emoji: 🧠
pinned: false
license: mit
app_file: demo/app.py
---

<div align="center">
    <img src="https://user-images.githubusercontent.com/30429725/204778476-4d24c659-9287-48b8-b616-92016ffcf4f6.svg" alt="drawing" width="600">
</div>

<div align="center">

<h1 align="center">DDMR: Deep Deformation Map Registration</h1>
<h3 align="center">Learning deep abdominal CT registration through adaptive loss weighting and synthetic data generation</h3>
 
# ⚠️***WARNING: Under construction*** 

**DDMR** was developed by SINTEF Health Research. The corresponding manuscript describing the framework has been published in [PLOS ONE](https://journals.plos.org/plosone/) and the manuscript is openly available [here](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282110).


</div>

## 💻 Getting started

1. Setup virtual environment:
```
virtualenv -ppython3 venv --clear
source venv/bin/activate
```

2. Install requirements:
```
pip install /path/to/clone/.
```

## 🤖 How to use
Use the following CLI command to register images
```
ddmr --fixed path/to/fixed_image.nii.gz --moving path/to/moving_image.nii.gz --outputdir path/to/output/dir -a <anatomy> --model <model> --gpu <gpu-number> --original-resolution
```
where:
* anatomy: is the type of anatomy you want to register: B (brain) or L (liver)
* model: is the model you want to use:
    + BL-N (baseline with NCC)
    + BL-NS (baseline with NCC and SSIM)
    + SG-ND (segmentation guided with NCC and DSC)
    + SG-NSD (segmentation guided with NCC, SSIM, and DSC)
    + UW-NSD (uncertainty weighted with NCC, SSIM, and DSC)
    + UW-NSDH (uncertainty weighted with NCC, SSIM, DSC, and HD).
* gpu: is the GPU number you want to the model to run on, if you have multiple and want to use only one GPU
* original-resolution: (flag) whether to upsample the registered image to the fixed image resolution (disabled if the flag is not present)

Use ```ddmr --help``` to see additional options like using precomputed segmentations to crop the images to the desired ROI, or debugging.

## 🏋️‍♂️ Training

Use the "MultiTrain" scripts to launch the trainings, providing the neccesary parameters. Those in the COMET folder accepts a .ini configuration file (see COMET/train_config_files for example configurations).

For instance:
```
python TrainingScripts/Train_3d.py
```

## 🔍 Evaluate

Use Evaluate_network to test the trained models. On the Brain folder, use "Evaluate_network__test_fixed.py" instead.

For instance:
```
python EvaluationScripts/evaluation.py
```

## ✨ How to cite
Please, consider citing our paper, if you find the work useful:
<pre>
@article{perezdefrutos2022ddmr,
    title = {Learning deep abdominal CT registration through adaptive loss weighting and synthetic data generation},
    author = {Pérez de Frutos, Javier AND Pedersen, André AND Pelanis, Egidijus AND Bouget, David AND Survarachakan, Shanmugapriya AND Langø, Thomas AND Elle, Ole-Jakob AND Lindseth, Frank},
    journal = {PLOS ONE},
    publisher = {Public Library of Science},
    year = {2023},
    month = {02},
    volume = {18},
    doi = {10.1371/journal.pone.0282110},
    url = {https://doi.org/10.1371/journal.pone.0282110},
    pages = {1-14},
    number = {2}
}
</pre>

## ⭐ Acknowledgements
This project is based on [VoxelMorph](https://github.com/voxelmorph/voxelmorph) library, and its related publication:
<pre>
@article{balakrishnan2019voxelmorph,
    title={VoxelMorph: A Learning Framework for Deformable Medical Image Registration}, 
    author={Balakrishnan, Guha and Zhao, Amy and Sabuncu, Mert R. and Guttag, John and Dalca, Adrian V.},
    journal={IEEE Transactions on Medical Imaging}, 
    year={2019},
    volume={38},
    number={8},
    pages={1788-1800},
    doi={10.1109/TMI.2019.2897538}
}
</pre>
