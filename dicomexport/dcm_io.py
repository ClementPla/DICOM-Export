import math
import cv2
from pathlib import Path
from pydicom import dcmread
from pydicom.uid import JPEG2000Lossless
from pydicom.encaps import generate_pixel_data_frame
import numpy as np
import os
from typing import Optional


def unscramble_czm(frame: bytes) -> bytearray:
    """Return an unscrambled image frame.

    Parameters
    ----------
    frame : bytes
        The scrambled CZM JPEG 2000 data frame as found in the DICOM dataset.

    Returns
    -------
    bytearray
        The unscrambled JPEG 2000 data.
    """
    # Fix the 0x5A XORing
    frame = bytearray(frame)
    for ii in range(0, len(frame), 7):
        frame[ii] = frame[ii] ^ 0x5A

    # Offset to the start of the JP2 header - empirically determined
    jp2_offset = math.floor(len(frame) / 5 * 3)

    # Double check that our empirically determined jp2_offset is correct
    offset = frame.find(b"\x00\x00\x00\x0c")
    if offset == -1:
        raise ValueError("No JP2 header found in the scrambled pixel data")

    if jp2_offset != offset:
        print(
            f"JP2 header found at offset {offset} rather than the expected {jp2_offset}"
        )
        jp2_offset = offset

    d = bytearray()
    d.extend(frame[jp2_offset : jp2_offset + 253])
    d.extend(frame[993:1016])
    d.extend(frame[276:763])
    d.extend(frame[23:276])
    d.extend(frame[1016:jp2_offset])
    d.extend(frame[:23])
    d.extend(frame[763:993])
    d.extend(frame[jp2_offset + 253 :])

    assert len(d) == len(frame)

    return d


def read_dicom_file(
    file: Path,
    laterality: Optional[str],
    date: Optional[str],
    patientId: Optional[str],
    output_folder: Path,
):
    laterality = laterality if laterality else "UNKNOWN"
    date = date if date else "UNKNOWN"
    patientId = patientId if patientId else "UNKNOWN"

    ds = dcmread(file)
    try:
        laterality = ds.Laterality[:2]
    except Exception:
        pass
    try:
        date = ds.AcquisitionDate[:8]
    except Exception:
        pass
    try:
        patientId = ds.PatientID[:7]
    except Exception:
        pass

    if not ds.Manufacturer.startswith("Carl Zeiss Meditec"):
        raise ValueError("Only CZM DICOM datasets are supported")

    if "PixelData" not in ds:
        raise ValueError("No 'Pixel Data' found in the DICOM dataset")

    output_folder = (
        output_folder
        / Path(f"{patientId}/{date}/{laterality}/")
        / file.stem.replace(".", "_")
    )
    output_folder.mkdir(exist_ok=True, parents=True)
    meta = ds.file_meta
    if meta.TransferSyntaxUID != JPEG2000Lossless:
        raise ValueError(
            "Only DICOM datasets with a 'Transfer Syntax UID' of JPEG 2000 "
            "(Lossless) are supported"
        )

    # Iterate through the frames, unscramble and write to file
    if "NumberOfFrames" in ds:
        # Workaround horrible non-conformance in datasets :(
        if isinstance(ds.NumberOfFrames, str):
            nr_frames = ds.NumberOfFrames.split("\0")[0]
        else:
            nr_frames = ds.NumberOfFrames

        frames = generate_pixel_data_frame(ds.PixelData, int(nr_frames))
        for idx, frame in enumerate(frames):
            with open(output_folder / f"{idx:>03}.jp2", "wb") as f:
                f.write(unscramble_czm(frame))

            img = cv2.imread(
                str(output_folder / f"{idx:>03}.jp2"), cv2.IMREAD_UNCHANGED
            )
            img = np.transpose(img)
            os.remove(str(output_folder / f"{idx:>03}.jp2"))
            cv2.imwrite(str(output_folder / f"{idx:>03}.png"), img)

    else:
        # CZM is non-conformant for single frames :(
        output_path = str(output_folder)
        with open(output_path + ".jp2", "wb") as f:
            f.write(unscramble_czm(ds.PixelData))

        img = cv2.imread(str(output_path + ".jp2"), cv2.IMREAD_UNCHANGED)
        os.remove(str(output_path + ".jp2"))
        cv2.imwrite(str(output_path + ".png"), img)

    return laterality, date, patientId
