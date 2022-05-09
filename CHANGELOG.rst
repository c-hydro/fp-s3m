=========
Changelog
=========

Version 1.1.1 (20220509)
========================
- Added provision for shifting and scaling input data in the converter routine (e.g., convert Kelvin temperature to Celsius on the fly)

Version 1.1.0 (20211029)
========================
- Added s3m_merger to merge outputs from multiple domains into a reference grid (mostly useful for postprocessing and visualization)

Version 1.0.1 (20210614)
========================
- Modified s3m_runner.py and s3m_configuration_runner_example.json to start simulation w/o copying-pasting the s3m x file

Version 1.0.0 (20210607)
========================
- First beta release of the fp-s3m package with utilities to prepare input and updating netCDF datasets from multiple and diverse source files. 
- Remapping from multiple input grids included!
- This release includes a runner to automatically launch a simulation (including writing a namelist and sourcing to the relevant libraries via bash)

