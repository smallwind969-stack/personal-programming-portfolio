# A Human-in-the-Loop Cascaded Deep Learning and Local-Agent Framework for Pulmonary Nodule Detection, Malignancy Stratification, and Follow-up Support on Chest CT

## Manuscript Status

This is a pre-submission SCI-Q2-oriented draft based on the current project materials and codebase. Numeric performance claims marked with **[VERIFY]** must be re-computed from a locked test set before submission. No clinical claim should be submitted without ethics review, dataset documentation, and statistical validation.

## Target Journal Fit

Potential targets include *Computers in Biology and Medicine*, *Computer Methods and Programs in Biomedicine*, *Biomedical Signal Processing and Control*, and *Informatics in Medicine Unlocked*. The strongest positioning is a methods/research hybrid paper on a clinically oriented workflow system rather than a pure clinical validation paper.

## Terminology Ledger

- CT: computed tomography.
- LDCT: low-dose computed tomography.
- CAD: computer-aided diagnosis.
- LIDC-IDRI: Lung Image Database Consortium and Image Database Resource Initiative.
- LUNA16: LUng Nodule Analysis 2016 challenge.
- VNet: volumetric convolutional segmentation/detection network.
- CBAM: convolutional block attention module.
- Agent: local rule- and LLM-assisted module for case summarization, missing-information detection, and follow-up support.
- Human-in-the-loop: a workflow in which model outputs remain subject to physician review and correction.

## Abstract

### Background
Pulmonary nodule detection on chest CT is a high-volume task in lung cancer screening and routine thoracic imaging. Deep learning systems have improved nodule detection and classification, but many research prototypes remain weakly connected to the downstream clinical workflow in which physicians review candidate lesions, integrate patient context, and generate follow-up recommendations.

### Objective
We developed a human-in-the-loop pulmonary nodule assistance framework that links cascaded three-dimensional deep learning with physician review and a locally deployed medical Agent for structured follow-up support.

### Methods
The system accepts DICOM CT series and converts them into isotropic 1-mm volumes after Hounsfield-unit clipping and normalization. A three-stage pipeline was implemented: an AttentionVNet module generates high-recall candidate nodule probability maps; a 3D ResNet18-CBAM classifier filters false-positive candidates; and a dual-branch 3D ResNet integrates local nodule appearance and surrounding contextual tissue to estimate malignancy tendency. A Flask-based web workstation supports CT browsing, window adjustment, candidate visualization, manual physician correction, structured clinical context entry, and local Agent output. The Agent combines rule-based risk stratification, physician-confirmed findings, missing-information checks, and optional local Qwen 8B generation through Ollama.

### Results
In the current internal technical record, the cascaded system achieved a detection recall of **96.12% [VERIFY: dataset, split, and FROC operating point required]**, a detection precision of **78.5% [VERIFY]**, a malignancy classification accuracy of **92.3% [VERIFY]**, and an end-to-end single-case processing time of approximately **25 s [VERIFY: hardware and case definition required]**. The upgraded Agent produced structured outputs including case summary, risk level, nodule-level risk sections, missing clinical/imaging information, safety statements, and presentation-ready workflow highlights. These outputs were generated locally and were explicitly constrained not to replace physician judgment.

### Conclusions
The proposed framework demonstrates a practical route from pulmonary nodule detection models to a reviewable clinical decision-support workflow. Its main contribution is not only a cascaded detection and classification pipeline, but also the integration of physician correction, structured case context, local language-model assistance, and safety-bounded follow-up support. Before journal submission, the framework requires locked-dataset evaluation, baseline comparison, ablation analysis, external validation, and prospective usability testing.

### Keywords
Pulmonary nodule; chest CT; computer-aided diagnosis; deep learning; human-in-the-loop; medical Agent; local large language model; follow-up recommendation.

## 1. Introduction

Lung cancer screening and thoracic CT interpretation generate a large number of pulmonary nodule findings that require detection, characterization, and longitudinal management. The National Lung Screening Trial established the clinical importance of low-dose CT screening for reducing lung-cancer mortality in high-risk populations [1]. However, CT screening also increases the workload associated with reviewing volumetric images and managing incidental or screen-detected nodules. A single chest CT series may contain hundreds of slices, and small nodules, ground-glass nodules, juxta-vascular lesions, and pleural-adjacent lesions can be difficult to identify consistently.

Clinical management of pulmonary nodules extends beyond binary detection. Nodule size, attenuation pattern, morphology, location, interval change, and patient-level risk factors influence follow-up decisions. The Fleischner Society guidelines emphasize that follow-up intervals should account for nodule type, size, number, and clinical risk context [2]. Therefore, a clinically useful CAD system should not merely draw boxes on CT slices. It should provide traceable candidate findings, allow physician correction, preserve structured measurements, and support guideline-aware communication without replacing physician judgment.

Deep learning has become the dominant technical route for pulmonary nodule detection and classification. Public resources such as LIDC-IDRI and the LUNA16 challenge have enabled standardized development and evaluation of detection algorithms [3,4]. Encoder-decoder networks and three-dimensional convolutional models are well suited to volumetric CT because nodules are spatial structures rather than isolated two-dimensional appearances [5,6]. Yet two gaps remain important for deployable student- and laboratory-scale systems. First, high recall and low false-positive burden are difficult to optimize in a single model. Second, many systems stop at algorithmic inference and do not provide a physician-reviewable workflow for structured follow-up reasoning.

Here we present a human-in-the-loop pulmonary nodule assistance framework that combines cascaded 3D deep learning with an interactive review workstation and a local medical Agent. The technical design follows a staged principle: detect broadly to reduce missed nodules, filter candidates to reduce physician burden, classify malignancy tendency using both local and contextual information, and then route the structured outputs into a safety-bounded Agent. The paper reports the system architecture, implementation, internal technical performance record, and a realistic roadmap required to elevate the current prototype into a publishable clinical AI study.

## 2. Related Work

### 2.1 Public pulmonary nodule datasets and challenge protocols
LIDC-IDRI is a foundational public database for lung nodule CAD research. It contains 1018 thoracic CT cases with XML annotations from a two-phase process involving four experienced thoracic radiologists [3]. LUNA16 built an objective detection evaluation framework on LIDC-IDRI and emphasized free-response evaluation for automatic pulmonary nodule detection [4]. These resources support reproducible algorithm development, but they do not by themselves solve workflow integration, physician correction, or follow-up recommendation.

### 2.2 Volumetric deep learning for nodule detection
U-Net and related encoder-decoder networks established an influential pattern for biomedical segmentation by combining contextual encoding with localization-preserving decoding [5]. In volumetric imaging, 3D convolutional networks can capture lesion continuity across slices and reduce the information loss inherent in slice-level analysis [6]. For pulmonary nodules, candidate-generation networks are often paired with false-positive reduction classifiers because permissive thresholds improve sensitivity but increase the number of candidate lesions requiring review.

### 2.3 Malignancy classification and attention mechanisms
Pulmonary nodule malignancy classification requires features beyond candidate localization. Texture, margins, internal density, surrounding tissue, and contextual anatomy may all contribute to risk estimation. Residual learning and attention modules such as CBAM have been used to improve feature selection in medical image classification tasks [7]. The present system adopts a 3D ResNet-CBAM module for false-positive reduction and a dual-branch 3D ResNet to combine local nodule features with wider contextual information.

### 2.4 AI workflow integration in radiology
Recent work on radiology AI emphasizes that model performance alone is insufficient for adoption. AI tools must integrate with review workflows, preserve user control, communicate uncertainty, and support auditability [8]. This is particularly relevant when language models are used in medical settings. In the proposed framework, the Agent is not a diagnostic authority. It transforms structured model and physician-review outputs into a safer, reviewable summary: risk sections, missing information, follow-up support, and explicit safety boundaries.

## 3. Materials and Methods

### 3.1 Study design and system objective
This work describes the design and implementation of a pulmonary nodule assistance system. The system objective is to support a workflow from CT upload to candidate detection, false-positive reduction, malignancy tendency estimation, physician review, and structured follow-up support. The current version should be regarded as a technical prototype. Clinical deployment and claims of diagnostic benefit require further institutional review and external validation.

### 3.2 Data input and preprocessing
The system supports DICOM series and MetaImage inputs. DICOM series are loaded using SimpleITK. Volumes are resampled to isotropic 1-mm spacing to standardize physical voxel dimensions across studies. CT intensity values are clipped to the lung-window range from -1200 HU to 600 HU and normalized to [0, 1]. For web display, the normalized CT volume is converted into sequential PNG slices, enabling browser-based review while model inference remains based on volumetric data.

### 3.3 Cascaded diagnostic pipeline
The diagnostic engine uses a three-stage cascade.

First, an AttentionVNet module performs candidate generation on 3D CT volumes. The model uses residual convolutional blocks, squeeze-and-excitation operations, and attention gates in skip connections. The inference engine applies sliding-window volumetric inference with 64 x 64 x 64 patches and a stride of 32 voxels. Candidate regions are extracted from the averaged probability map after thresholding.

Second, a 3D ResNet18-CBAM model filters false-positive candidates. Candidate-centered 32 x 32 x 32 volumetric patches are extracted and classified. The purpose of this stage is to retain likely nodules while reducing candidates caused by vessels, airway walls, inflammatory shadows, or other anatomic structures.

Third, a dual-branch 3D ResNet estimates malignancy tendency. The local branch receives a 32-voxel patch centered on the candidate, whereas the global branch receives a 64-voxel contextual crop resized to the same tensor size. The concatenated feature vector is passed through fully connected layers to predict benign versus malignant tendency. The dual-branch design reflects the clinical intuition that malignancy assessment depends both on nodule-level appearance and surrounding anatomical context.

### 3.4 Physician review workstation
The web interface is implemented using Flask, HTML, CSS, JavaScript, and Canvas. It supports patient selection, CT slice navigation, window width/window level adjustment, zooming, candidate overlay, candidate cards, and physician editing. Physicians or reviewers can confirm model candidates, dismiss false positives, manually add missed nodules by drawing boxes, edit slice ranges and coordinates, and enter structured clinical context including age, sex, smoking history, prior CT comparison, tumor history, symptoms, and free-text notes.

### 3.5 Local Agent for follow-up support
The Agent receives model findings, physician-reviewed findings, and clinical context. It produces a structured output with the following fields: patient identifier, case summary, overall risk level, nodule statistics, high/medium/low-risk sections, nodule-level recommendations, missing-information list, optional LLM summary, presentation highlight, and safety note. The rule layer prioritizes physician-confirmed and physician-added nodules over raw model outputs. If fine-grained imaging signs such as spiculation, lobulation, pleural indentation, calcification, or nodule type are absent, the Agent lists them as missing rather than inventing them.

The optional language-model component is deployed locally through Ollama using Qwen 8B. This design avoids sending sensitive case data to external cloud APIs during prototype operation. The LLM is used only for wording and summary assistance; risk assignment and safety constraints remain rule governed.

### 3.6 Implementation environment
The backend is implemented in Python with Flask, PyTorch, NumPy, SciPy, scikit-image, SimpleITK, and Pillow. The frontend is a lightweight browser-based CT review workstation. The current project contains model weights for the AttentionVNet detector, the ResNet-CBAM false-positive reduction model, and the dual-branch malignancy classifier. Runtime hardware for the current prototype includes a local workstation with NVIDIA GPU support **[VERIFY: exact GPU, CUDA version, CPU, RAM, OS, and PyTorch version before submission]**.

## 4. Experiments and Results

### 4.1 Evaluation protocol
The current system materials report internal performance metrics, but the dataset split, case counts, lesion counts, and exact operating points must be reconstructed before journal submission. A publishable evaluation should include:

1. A locked training/validation/test split or cross-validation protocol.
2. Case-level and nodule-level counts.
3. Sensitivity at fixed false-positive rates per scan.
4. Precision, recall, F1-score, and confusion matrices for false-positive reduction and malignancy classification.
5. Calibration analysis for malignancy probability.
6. Ablation studies for the cascade, CBAM, dual-branch design, physician review, and Agent module.
7. External validation on an independent dataset or institutional cohort.

### 4.2 Internal technical performance record
The project technical record reports a detection recall of 96.12%, detection precision of 78.5%, malignancy classification accuracy of 92.3%, and single-case processing time of approximately 25 s. These values are promising for a student-built technical system, but they must be treated as preliminary until the evaluation protocol is frozen. In the final manuscript, these numbers should be reported only with exact dataset, split, confidence intervals, and baseline comparison.

### 4.3 Workflow-level functionality
The upgraded system successfully links model inference with physician review and Agent output. The workstation can display CT slices, overlay candidate regions, maintain a reviewed nodule list, save physician-reviewed findings, and generate Agent summaries. The Agent returns case-level statistics, risk sections, missing-information prompts, and safety-bounded follow-up support. This workflow demonstrates that the system has moved beyond a single inference endpoint toward a reviewable clinical AI pipeline.

### 4.4 Safety behavior of the Agent
A key design requirement is that the Agent must not fabricate missing imaging signs or clinical facts. In the current implementation, absent information is explicitly returned as missing data. Examples include prior CT comparison, nodule type, maximum diameter, spiculation, lobulation, pleural indentation, and physician review conclusion. This behavior is important because language-model outputs in medical workflows must remain subordinate to structured evidence and physician oversight.

### 4.5 Required figures and tables for submission
The following figures and tables should be prepared before submission:

- Figure 1: Overall workflow from CT upload to Agent output.
- Figure 2: Cascaded model architecture: AttentionVNet, ResNet-CBAM, and dual-branch ResNet.
- Figure 3: Web workstation screenshots with candidate overlays and physician review.
- Figure 4: Agent output schema and safety-control logic.
- Table 1: Dataset characteristics.
- Table 2: Detection performance at multiple false-positive rates per scan.
- Table 3: False-positive reduction and malignancy classification metrics.
- Table 4: Ablation study.
- Table 5: Runtime and resource consumption.

## 5. Discussion

This work presents a pulmonary nodule assistance framework that connects volumetric deep learning to a physician-reviewable workflow. The central contribution is the integration of a cascaded CT inference pipeline with a structured local Agent, rather than any single model block in isolation. The design is aligned with a practical clinical sequence: broad candidate detection, false-positive reduction, malignancy tendency estimation, manual review, clinical-context enrichment, and follow-up support.

The cascaded architecture addresses a common trade-off in pulmonary nodule CAD. A candidate generator optimized for high recall may produce too many false positives for routine use. A stricter detector may reduce false positives but miss subtle lesions. Separating candidate generation from false-positive reduction allows each module to optimize a more specific task. The dual-branch classifier further reflects the need to combine lesion-centered features with surrounding anatomical context.

The Agent module adds a second layer of value. Rather than asking a language model to make medical decisions, the system passes structured findings and physician corrections into a constrained summarization and missing-information workflow. This is a safer design than free-form report generation because it makes the absence of evidence visible. The Agent can state that prior CT comparison or nodule type is missing, but it cannot fill those fields without evidence.

The study has important limitations. First, the current performance numbers require independent re-analysis. Second, the system has not yet been externally validated. Third, the current model does not directly extract fine-grained imaging signs such as spiculation, lobulation, pleural retraction, cavitation, or calcification. Fourth, the Agent currently provides follow-up support based on structured rules and local language generation, but it has not yet been evaluated against guideline-grounded expert annotations. Fifth, usability and workload reduction have not been quantified in a reader study.

These limitations define the path toward a stronger SCI-Q2 submission. The next version should add a locked evaluation dataset, FROC analysis, calibration, reader agreement, guideline-consistency scoring, and an external validation cohort. A small radiologist-in-the-loop study measuring review time, correction rate, and perceived usefulness would substantially strengthen the manuscript.

## 6. Conclusion

We developed a human-in-the-loop pulmonary nodule assistance framework that integrates cascaded 3D deep learning, an interactive physician review workstation, and a local safety-bounded Agent for structured follow-up support. The prototype demonstrates a feasible technical pathway from CT-based nodule detection to reviewable case-level decision support. With rigorous dataset validation, ablation studies, and expert-guideline evaluation, the framework could be developed into a competitive SCI-Q2 manuscript in biomedical informatics or medical imaging AI.

## Data Availability Statement

The current manuscript draft is based on a local project prototype and publicly described dataset references. No patient-level research dataset is redistributed with this draft. For submission, the authors should specify whether training and testing used LIDC-IDRI, LUNA16-derived splits, institutional data, or mixed data, and should provide access instructions or controlled-access statements consistent with dataset licenses and ethics approval.

## Ethics Statement

This technical draft does not report a finalized human-subjects study. If institutional CT data are used for training, validation, or testing, institutional review board approval or exemption must be obtained before submission. All patient identifiers must be removed or protected according to applicable regulations.

## Author Contributions

Use CRediT taxonomy before submission. Suggested draft: Conceptualization: [names]; Methodology: [names]; Software: [names]; Data curation: [names]; Validation: [names]; Writing - original draft: [names]; Writing - review and editing: [names]; Supervision: [names].

## Funding

[Insert grant, innovation project, undergraduate research program, or "The authors received no specific funding for this work."]

## Conflict of Interest

The authors declare no competing interests. **[VERIFY before submission]**

## AI Tool Disclosure

AI tools were used to assist manuscript planning, language drafting, and code/document organization. All scientific claims, experimental results, citations, clinical interpretations, and final wording must be verified and approved by the authors before submission. The AI system did not replace author responsibility for data integrity or clinical validity.

## References

1. National Lung Screening Trial Research Team. Reduced lung-cancer mortality with low-dose computed tomographic screening. *New England Journal of Medicine*. 2011;365(5):395-409. doi:10.1056/NEJMoa1102873.
2. MacMahon H, Naidich DP, Goo JM, et al. Guidelines for management of incidental pulmonary nodules detected on CT images: From the Fleischner Society 2017. *Radiology*. 2017;284(1):228-243. doi:10.1148/radiol.2017161659.
3. Armato SG III, McLennan G, Bidaut L, et al. The Lung Image Database Consortium (LIDC) and Image Database Resource Initiative (IDRI): A completed reference database of lung nodules on CT scans. *Medical Physics*. 2011;38(2):915-931. doi:10.1118/1.3528204.
4. Setio AAA, Traverso A, de Bel T, et al. Validation, comparison, and combination of algorithms for automatic detection of pulmonary nodules in computed tomography images: The LUNA16 challenge. *Medical Image Analysis*. 2017;42:1-13. doi:10.1016/j.media.2017.06.015.
5. Ronneberger O, Fischer P, Brox T. U-Net: Convolutional networks for biomedical image segmentation. In: *Medical Image Computing and Computer-Assisted Intervention - MICCAI 2015*. Lecture Notes in Computer Science. 2015;9351:234-241. doi:10.1007/978-3-319-24574-4_28.
6. Dou Q, Yu L, Chen H, et al. 3D deeply supervised network for automated segmentation of volumetric medical images. *Medical Image Analysis*. 2017;41:40-54. doi:10.1016/j.media.2017.05.001.
7. Zhang Y, Feng W, Wu Z, et al. Deep-learning model of ResNet combined with CBAM for malignant-benign pulmonary nodules classification on computed tomography images. *Diagnostics*. 2023;13(11):1949. doi:10.3390/diagnostics13111949.
8. Lakhani P, Sundaram B, Recht MP, et al. Integrating and adopting AI in the radiology workflow: A primer for standards and Integrating the Healthcare Enterprise (IHE) profiles. *Radiology*. 2024;310(3):e232653. doi:10.1148/radiol.232653.
9. Venkadesh KV, Setio AAA, Schreuder A, et al. Deep learning for the detection of benign and malignant pulmonary nodules in non-screening chest CT scans. *Communications Medicine*. 2023;3:161. doi:10.1038/s43856-023-00388-5.

## Pre-submission Action Checklist

- Recompute all metrics from a frozen dataset.
- Add FROC curves at standard false-positive rates per scan.
- Add baseline comparison against a single-stage 3D CNN and/or published LUNA16 baselines.
- Add ablation: without CBAM, without dual-branch context, without physician review, without Agent safety rules.
- Add external validation if possible.
- Add expert review of Agent outputs against Fleischner-style follow-up rules.
- Prepare figures and tables listed in Section 4.5.
- Confirm ethics, data availability, author contributions, and AI disclosure.
