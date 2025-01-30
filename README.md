# Convenient Zeiss DICOM Exporter

A simple tool to export Zeiss OCT scans from zip files to organized DICOM files.

## Usage

Go to the [notebook](export.ipynb) and change the cell containing:

```python
root = Path("samples/")  # Folder that contains all the zip files
```

Set this path to your folder containing all the exported volumes from the Zeiss machine as .zip files (i.e., all patients). It can be relative to the DICOM-Export folder or absolute. Make sure to indicate the path with / and not \ (even on Windows system)

Then execute the next cell. Note that exporting may take some time. 
By nature, there might be inaccuracies in the date and laterality associated with each volume as we extrapolate them from the first time we find them on each subfolder within the zip.

## Installation

```bash
git clone https://github.com/clement-q/DICOM-Export.git
```

```bash
cd DICOM-Export
pip install .
```
